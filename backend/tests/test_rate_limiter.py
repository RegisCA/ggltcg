"""
Tests for game_engine.ai.rate_limiter: RateBudgetLimiter, NoopLimiter,
BudgetExhaustedError.

Uses an injectable fake clock/sleep so no test actually sleeps, and an
in-memory SQLite session factory (shared across limiter instances within a
test) to exercise persistence/rollover without touching the real app DB.
"""

import sys
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.db_models import Base, ApiUsageModel  # noqa: E402
from game_engine.ai.rate_limiter import (  # noqa: E402
    RateBudgetLimiter,
    NoopLimiter,
    BudgetExhaustedError,
)

TZ = "America/Los_Angeles"


@pytest.fixture
def session_factory():
    """A fresh in-memory SQLite DB with the schema created, shared by name
    within this fixture instance (StaticPool keeps the same in-memory DB
    alive across connections)."""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[ApiUsageModel.__table__])
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


class FakeClock:
    """Deterministic monotonic clock + no-op sleep that advances the clock
    by the requested duration instead of actually sleeping."""

    def __init__(self, start: float = 0.0):
        self.now = start
        self.sleep_calls = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self.now += seconds


class FakeNow:
    """Controllable now_fn for the daily-budget day computation."""

    def __init__(self, start: datetime):
        self.current = start

    def __call__(self) -> datetime:
        return self.current

    def advance_days(self, n: int) -> None:
        self.current = self.current + timedelta(days=n)


def _make_now(day: date, hour: int = 12) -> datetime:
    return datetime(day.year, day.month, day.day, hour, tzinfo=ZoneInfo(TZ))


# ---------------------------------------------------------------------
# Token bucket (RPM) timing
# ---------------------------------------------------------------------

class TestTokenBucket:
    def test_rpm_none_never_sleeps(self, session_factory):
        fake = FakeClock()
        limiter = RateBudgetLimiter(
            rpm=None,
            daily_budget=None,
            session_factory=session_factory,
            clock=fake.clock,
            sleep=fake.sleep,
            now_fn=lambda: _make_now(date(2026, 7, 8)),
        )
        for _ in range(50):
            limiter.acquire()
        assert fake.sleep_calls == []

    def test_rpm_bucket_starts_full_no_sleep_for_burst(self, session_factory):
        # capacity == rpm, so the first `rpm` acquires should not need to sleep.
        fake = FakeClock()
        limiter = RateBudgetLimiter(
            rpm=5,
            daily_budget=None,
            session_factory=session_factory,
            clock=fake.clock,
            sleep=fake.sleep,
            now_fn=lambda: _make_now(date(2026, 7, 8)),
        )
        for _ in range(5):
            limiter.acquire()
        assert fake.sleep_calls == []

    def test_rpm_bucket_blocks_once_exhausted(self, session_factory):
        fake = FakeClock()
        rpm = 3
        limiter = RateBudgetLimiter(
            rpm=rpm,
            daily_budget=None,
            session_factory=session_factory,
            clock=fake.clock,
            sleep=fake.sleep,
            now_fn=lambda: _make_now(date(2026, 7, 8)),
        )
        for _ in range(rpm):
            limiter.acquire()
        assert fake.sleep_calls == []

        # The 4th acquire within the same instant must wait for a refill.
        limiter.acquire()
        assert len(fake.sleep_calls) == 1
        expected_wait = 60.0 / rpm
        assert fake.sleep_calls[0] == pytest.approx(expected_wait)

    def test_rpm_bucket_refills_over_time(self, session_factory):
        fake = FakeClock()
        rpm = 60  # 1 token/sec
        limiter = RateBudgetLimiter(
            rpm=rpm,
            daily_budget=None,
            session_factory=session_factory,
            clock=fake.clock,
            sleep=fake.sleep,
            now_fn=lambda: _make_now(date(2026, 7, 8)),
        )
        # Drain the bucket.
        for _ in range(rpm):
            limiter.acquire()
        assert fake.sleep_calls == []

        # Advance the fake clock by 5 seconds worth of refill "for free"
        # (simulating time passing between calls, not via sleep).
        fake.now += 5.0
        for _ in range(5):
            limiter.acquire()
        # Those 5 acquires should be covered by the 5 refilled tokens.
        assert fake.sleep_calls == []

        # One more should need to wait ~1 second for the next token.
        limiter.acquire()
        assert len(fake.sleep_calls) == 1
        assert fake.sleep_calls[0] == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------
# Daily budget persistence + rollover
# ---------------------------------------------------------------------

class TestDailyBudget:
    def test_daily_count_persists_across_instances(self, session_factory):
        fake_now = FakeNow(_make_now(date(2026, 7, 8)))
        fake_clock = FakeClock()

        limiter1 = RateBudgetLimiter(
            rpm=None,
            daily_budget=100,
            session_factory=session_factory,
            clock=fake_clock.clock,
            sleep=fake_clock.sleep,
            now_fn=fake_now,
        )
        for _ in range(10):
            limiter1.acquire()
        limiter1.flush()

        limiter2 = RateBudgetLimiter(
            rpm=None,
            daily_budget=100,
            session_factory=session_factory,
            clock=fake_clock.clock,
            sleep=fake_clock.sleep,
            now_fn=fake_now,
        )
        status = limiter2.remaining()
        assert status["used_today"] == 10

        for _ in range(5):
            limiter2.acquire()
        limiter2.flush()

        limiter3 = RateBudgetLimiter(
            rpm=None,
            daily_budget=100,
            session_factory=session_factory,
            clock=fake_clock.clock,
            sleep=fake_clock.sleep,
            now_fn=fake_now,
        )
        assert limiter3.remaining()["used_today"] == 15

    def test_auto_flush_every_ten_acquires(self, session_factory):
        fake_now = FakeNow(_make_now(date(2026, 7, 8)))
        fake_clock = FakeClock()

        limiter1 = RateBudgetLimiter(
            rpm=None,
            daily_budget=None,
            session_factory=session_factory,
            clock=fake_clock.clock,
            sleep=fake_clock.sleep,
            now_fn=fake_now,
        )
        # Exactly 10 acquires should trigger the periodic auto-flush,
        # without an explicit flush() call.
        for _ in range(10):
            limiter1.acquire()

        limiter2 = RateBudgetLimiter(
            rpm=None,
            daily_budget=None,
            session_factory=session_factory,
            clock=fake_clock.clock,
            sleep=fake_clock.sleep,
            now_fn=fake_now,
        )
        assert limiter2.remaining()["used_today"] == 10

    def test_budget_exhausted_raised_exactly_at_budget(self, session_factory):
        fake_now = FakeNow(_make_now(date(2026, 7, 8)))
        fake_clock = FakeClock()
        limiter = RateBudgetLimiter(
            rpm=None,
            daily_budget=3,
            session_factory=session_factory,
            clock=fake_clock.clock,
            sleep=fake_clock.sleep,
            now_fn=fake_now,
        )
        for _ in range(3):
            limiter.acquire()

        with pytest.raises(BudgetExhaustedError) as exc_info:
            limiter.acquire()

        expected_resets_at = datetime(2026, 7, 9, tzinfo=ZoneInfo(TZ))
        assert exc_info.value.resets_at == expected_resets_at

        # Still exhausted on subsequent calls (no double-counting).
        with pytest.raises(BudgetExhaustedError):
            limiter.acquire()

        assert limiter.remaining()["used_today"] == 3

    def test_day_rollover_resets_counter(self, session_factory):
        fake_now = FakeNow(_make_now(date(2026, 7, 8)))
        fake_clock = FakeClock()
        limiter = RateBudgetLimiter(
            rpm=None,
            daily_budget=5,
            session_factory=session_factory,
            clock=fake_clock.clock,
            sleep=fake_clock.sleep,
            now_fn=fake_now,
        )
        for _ in range(5):
            limiter.acquire()
        with pytest.raises(BudgetExhaustedError):
            limiter.acquire()

        # Roll over to the next day.
        fake_now.advance_days(1)

        # Budget should be reset; this should succeed without raising.
        limiter.acquire()
        status = limiter.remaining()
        assert status["used_today"] == 1
        limiter.flush()

        # The previous day's final count (5) should have been persisted
        # under the old date, separately from the new day's row.
        session = session_factory()
        try:
            old_row = session.get(ApiUsageModel, ("gemini", date(2026, 7, 8)))
            new_row = session.get(ApiUsageModel, ("gemini", date(2026, 7, 9)))
        finally:
            session.close()
        assert old_row.request_count == 5
        assert new_row.request_count == 1


# ---------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------

class TestThreadSafety:
    def test_concurrent_acquires_count_exactly(self, session_factory):
        fake_now = FakeNow(_make_now(date(2026, 7, 8)))
        # rpm=None to avoid any sleeping/refill timing races in this test.
        limiter = RateBudgetLimiter(
            rpm=None,
            daily_budget=None,
            session_factory=session_factory,
            now_fn=fake_now,
        )

        def worker():
            for _ in range(5):
                limiter.acquire()

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        limiter.flush()
        assert limiter.remaining()["used_today"] == 100


# ---------------------------------------------------------------------
# NoopLimiter
# ---------------------------------------------------------------------

class TestNoopLimiter:
    def test_noop_limiter_never_raises_or_blocks(self):
        limiter = NoopLimiter()
        for _ in range(1000):
            limiter.acquire()
        limiter.flush()
        status = limiter.remaining()
        assert status == {
            "rpm": None,
            "daily_budget": None,
            "used_today": 0,
            "resets_at": None,
        }
