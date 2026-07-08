"""
Rate limiter + persisted daily request budget for external API calls (Gemini).

Two independent controls, both optional:

- RPM (requests per minute): a simple token-bucket. `acquire()` blocks
  (via an injectable `sleep`) until a token is available. Disabled entirely
  when `rpm` is None.
- Daily budget: a running per-provider, per-day request counter persisted to
  the `api_usage_daily` table (see `api.db_models.ApiUsageModel`). When the
  counter reaches the budget, `acquire()` raises `BudgetExhaustedError`
  instead of blocking. Disabled entirely when `daily_budget` is None.

Callers construct a `RateBudgetLimiter` (or a
`NoopLimiter` when no limiting is configured) and call `acquire()` before
each external request, then `flush()` when done (e.g. at process shutdown)
to ensure the last few requests are persisted.

Thread-safety: a single `threading.Lock` serializes `acquire()` and
`flush()`. This is deliberate — a shared daily budget across the whole
process must be counted exactly once per request even if multiple threads
call `acquire()` concurrently.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from api.database import SessionLocal
from api.db_models import ApiUsageModel

# Flush the persisted counter to the DB every N acquires, in addition to
# whenever the caller explicitly calls flush() or a day rolls over.
_FLUSH_EVERY = 10


class BudgetExhaustedError(Exception):
    """Raised by `RateBudgetLimiter.acquire()` once the daily budget is used up."""

    def __init__(self, resets_at: datetime, message: Optional[str] = None):
        self.resets_at = resets_at
        super().__init__(
            message or f"Daily API request budget exhausted; resets at {resets_at.isoformat()}"
        )


class RateBudgetLimiter:
    """
    Thread-safe RPM limiter + persisted daily request budget for one provider.

    Args:
        rpm: max requests per minute (token bucket capacity + refill rate).
            None disables RPM limiting entirely.
        daily_budget: max requests per calendar day (in `tz`). None disables
            the daily budget entirely.
        session_factory: SQLAlchemy sessionmaker used to read/write the
            `api_usage_daily` row. Defaults to the app's `SessionLocal`.
            Tests should inject their own in-memory-SQLite-backed factory.
        provider: identifies the row in `api_usage_daily` (e.g. "gemini").
        tz: IANA timezone name used to determine "today" for the daily
            budget and to compute `resets_at`.
        clock: monotonic clock used for RPM token-bucket timing. Injectable
            for deterministic tests.
        sleep: sleep function used to block until an RPM token is available.
            Injectable for deterministic tests (avoid real sleeping).
        now_fn: returns the current timezone-aware datetime, used to derive
            "today" for the daily budget. Defaults to
            `datetime.now(ZoneInfo(tz))`. Injectable for deterministic tests.
    """

    def __init__(
        self,
        rpm: Optional[int],
        daily_budget: Optional[int],
        session_factory=None,
        provider: str = "gemini",
        tz: str = "America/Los_Angeles",
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        now_fn: Optional[Callable[[], datetime]] = None,
    ):
        self.rpm = rpm
        self.daily_budget = daily_budget
        self.session_factory = session_factory if session_factory is not None else SessionLocal
        self.provider = provider
        self.tz = ZoneInfo(tz)
        self._clock = clock
        self._sleep = sleep
        self._now_fn = now_fn or (lambda: datetime.now(self.tz))

        self._lock = threading.Lock()

        # Token bucket state (only meaningful when rpm is not None).
        self._tokens: float = float(rpm) if rpm is not None else 0.0
        self._refill_rate: float = (rpm / 60.0) if rpm is not None else 0.0
        self._last_refill: float = self._clock()

        # Daily budget state.
        self._day: date = self._today()
        self._count: int = self._load_count_locked(self._day)
        self._acquires_since_flush: int = 0

    # -- public API ---------------------------------------------------

    def acquire(self) -> None:
        """
        Block (if needed) for RPM pacing, then account for one request
        against the daily budget.

        Raises:
            BudgetExhaustedError: if the daily budget (if configured) has
                already been reached for today.
        """
        with self._lock:
            self._check_rollover_locked()

            if self.daily_budget is not None and self._count >= self.daily_budget:
                raise BudgetExhaustedError(resets_at=self._next_midnight_locked())

            self._consume_rpm_token_locked()

            self._count += 1
            self._acquires_since_flush += 1
            if self._acquires_since_flush >= _FLUSH_EVERY:
                self._flush_locked()

    def remaining(self) -> dict:
        """Return current limiter status."""
        with self._lock:
            self._check_rollover_locked()
            used_today = self._count
            resets_at = self._next_midnight_locked() if self.daily_budget is not None else None
            return {
                "rpm": self.rpm,
                "daily_budget": self.daily_budget,
                "used_today": used_today,
                "resets_at": resets_at,
            }

    def flush(self) -> None:
        """Persist the current day's counter to the database."""
        with self._lock:
            self._flush_locked()

    # -- internals (must be called while holding self._lock) ----------

    def _today(self) -> date:
        return self._now_fn().date()

    def _next_midnight_locked(self) -> datetime:
        next_day = self._day + timedelta(days=1)
        return datetime(next_day.year, next_day.month, next_day.day, tzinfo=self.tz)

    def _check_rollover_locked(self) -> None:
        today = self._today()
        if today != self._day:
            # Persist the outgoing day's final count before rolling over.
            self._flush_locked()
            self._day = today
            self._count = self._load_count_locked(today)
            self._acquires_since_flush = 0

    def _consume_rpm_token_locked(self) -> None:
        if self.rpm is None:
            return

        now = self._clock()
        elapsed = now - self._last_refill
        self._tokens = min(float(self.rpm), self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

        if self._tokens < 1.0:
            wait = (1.0 - self._tokens) / self._refill_rate
            self._sleep(wait)
            self._tokens = 0.0
            self._last_refill = self._clock()
        else:
            self._tokens -= 1.0

    def _load_count_locked(self, day: date) -> int:
        """Read (or implicitly initialize to 0) today's persisted count."""
        session = self.session_factory()
        try:
            row = session.get(ApiUsageModel, (self.provider, day))
            return row.request_count if row is not None else 0
        finally:
            session.close()

    def _flush_locked(self) -> None:
        """Upsert the current (provider, day) row with self._count."""
        session = self.session_factory()
        try:
            row = session.get(ApiUsageModel, (self.provider, self._day))
            if row is None:
                row = ApiUsageModel(
                    provider=self.provider,
                    day=self._day,
                    request_count=self._count,
                )
                session.add(row)
            else:
                row.request_count = self._count
            session.commit()
            self._acquires_since_flush = 0
        finally:
            session.close()


class NoopLimiter:
    """
    Drop-in replacement for `RateBudgetLimiter` that never limits or
    persists anything. Lets callers always hold a limiter instance without
    needing an `if limiter:` branch.
    """

    def acquire(self) -> None:
        pass

    def remaining(self) -> dict:
        return {
            "rpm": None,
            "daily_budget": None,
            "used_today": 0,
            "resets_at": None,
        }

    def flush(self) -> None:
        pass
