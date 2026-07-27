"""Gemini provider for the AI player's model backend."""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

from game_engine.ai.rate_limiter import BudgetExhaustedError, NoopLimiter

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-flash-lite-latest"  # Stable alias for latest Flash Lite; no geographic restriction
DEFAULT_FALLBACK_MODEL = "gemini-2.5-flash-lite"

# USD per million tokens, as published 2026-07-26. Indicative only: this exists so
# a run can report roughly what it cost instead of relying on a hand estimate, not
# as a billing source of truth. Unlisted models fall back to the 2.5 Flash-Lite
# rate, which is the cheapest tier, so an unknown model under-reports rather than
# silently inventing a number.
MODEL_PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-flash-lite-latest": (0.10, 0.40),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-3.5-flash-lite": (0.30, 2.50),
}
_FALLBACK_PRICING = (0.10, 0.40)


@dataclass(frozen=True)
class AIProviderConfig:
    """Resolved Gemini provider configuration."""

    api_key: str
    model: str
    fallback_model: str


def resolve_provider_config(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    fallback_model: Optional[str] = None,
) -> AIProviderConfig:
    """Resolve Gemini provider configuration from arguments and environment."""
    resolved_api_key = api_key or os.getenv("GOOGLE_API_KEY")
    if not resolved_api_key:
        raise ValueError("API key required for Gemini. Set GOOGLE_API_KEY.")

    resolved_model = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
    resolved_fallback = fallback_model or os.getenv("GEMINI_FALLBACK_MODEL") or resolved_model

    return AIProviderConfig(
        api_key=resolved_api_key,
        model=resolved_model,
        fallback_model=resolved_fallback,
    )


class GeminiProvider:
    """Google Gemini provider using the google-genai SDK."""

    # Class-level token accounting, shared across instances (simulations build a
    # provider per game, so per-instance counters would be discarded every game).
    #
    # Nothing previously recorded response.usage_metadata, which is why every cost
    # figure for this project has been an estimate inferred from prompt structure.
    # Capturing it makes a run self-measuring: requests per game, tokens per
    # request and approximate spend all become facts rather than assumptions.
    _usage = {
        "requests": 0,
        "prompt_tokens": 0,
        "output_tokens": 0,
        "thinking_tokens": 0,
        "cached_tokens": 0,
        "by_model": {},
    }
    # Simulations fan out over a ThreadPoolExecutor, so accumulation is shared
    # mutable state. `counter += n` on a dict value is a read-modify-write and is
    # not atomic under the GIL; without this the totals would quietly run low
    # exactly when parallelism is highest.
    _usage_lock = threading.Lock()

    @classmethod
    def reset_usage(cls) -> None:
        cls._usage = {
            "requests": 0,
            "prompt_tokens": 0,
            "output_tokens": 0,
            "thinking_tokens": 0,
            "cached_tokens": 0,
            "by_model": {},
        }

    @classmethod
    def get_usage(cls) -> dict[str, Any]:
        """Token totals plus an approximate cost, per model and overall."""
        with cls._usage_lock:
            snapshot = {k: (dict(v) if isinstance(v, dict) else v)
                        for k, v in cls._usage.items()}
            snapshot["by_model"] = {m: dict(c) for m, c in cls._usage["by_model"].items()}
        usage = {k: v for k, v in snapshot.items() if k != "by_model"}
        by_model = {}
        total_cost = 0.0
        for model, counts in snapshot["by_model"].items():
            price_in, price_out = MODEL_PRICING_PER_MTOK.get(model, _FALLBACK_PRICING)
            # Thinking tokens bill as output on models that emit them.
            billable_out = counts["output_tokens"] + counts["thinking_tokens"]
            cost = (counts["prompt_tokens"] * price_in
                    + billable_out * price_out) / 1_000_000
            by_model[model] = {**counts, "est_cost_usd": round(cost, 6)}
            total_cost += cost
        usage["by_model"] = by_model
        usage["est_cost_usd"] = round(total_cost, 6)
        usage["priced_from"] = "MODEL_PRICING_PER_MTOK (indicative, 2026-07-26)"
        return usage

    @classmethod
    def _record_usage(cls, response: Any, model: str) -> None:
        """Accumulate one response's token counts. Never raises.

        Usage accounting must not be able to break a game: the SDK's field names
        have changed before and some are absent on some models, so every read is
        defensive and a failure here is swallowed.
        """
        try:
            meta = getattr(response, "usage_metadata", None)
            if meta is None:
                return

            def count(*names: str) -> int:
                for name in names:
                    value = getattr(meta, name, None)
                    if isinstance(value, int):
                        return value
                return 0

            fields = {
                "prompt_tokens": count("prompt_token_count"),
                "output_tokens": count("candidates_token_count"),
                "thinking_tokens": count("thoughts_token_count", "thinking_token_count"),
                "cached_tokens": count("cached_content_token_count"),
            }
            with cls._usage_lock:
                entry = cls._usage["by_model"].setdefault(model, {
                    "requests": 0, "prompt_tokens": 0,
                    "output_tokens": 0, "thinking_tokens": 0, "cached_tokens": 0,
                })
                cls._usage["requests"] += 1
                entry["requests"] += 1
                for key, value in fields.items():
                    cls._usage[key] += value
                    entry[key] += value
        except Exception:  # pragma: no cover - accounting must never break a game
            logger.debug("failed to record token usage", exc_info=True)

    def __init__(self, config: AIProviderConfig, client: Any | None = None, rate_limiter: Any | None = None):
        self.config = config
        if client is None:
            from google import genai

            client = genai.Client(api_key=config.api_key)
        self.client = client
        self.rate_limiter = rate_limiter if rate_limiter is not None else NoopLimiter()

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        temperature: float,
        max_output_tokens: int,
        retry_count: int = 3,
        allow_fallback: bool = True,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        from google.genai import types

        current_model = model or self.config.model
        resolved_fallback = fallback_model or self.config.fallback_model
        last_exception: Exception | None = None

        for attempt in range(retry_count):
            try:
                self.rate_limiter.acquire()
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=prompt)],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        response_mime_type="application/json",
                        response_json_schema=schema,
                        system_instruction=system_instruction,
                    ),
                )

                # Recorded before validating: a truncated or empty response still
                # consumed input tokens and still bills. Those calls are exactly
                # the ones a cost report needs to show -- on models with thinking
                # enabled they are the expensive failure mode.
                self._record_usage(response, current_model)

                if not response.candidates or not response.candidates[0].content.parts:
                    finish_reason = (
                        response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
                    )
                    raise ValueError(
                        f"Gemini returned empty response (finish_reason: {finish_reason})"
                    )

                return response.text.strip()
            except BudgetExhaustedError:
                raise
            except Exception as exc:
                last_exception = exc
                if self._is_location_precondition(exc):
                    logger.error(
                        "Gemini location precondition failed for model %s (fallback %s). "
                        "This is typically a key/project policy or hosting egress geolocation issue; "
                        "model fallback will not resolve it.",
                        current_model,
                        resolved_fallback,
                    )
                    raise

                if self._is_retryable(exc) and attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "Gemini capacity issue. Retry %s/%s after %ss.",
                        attempt + 1,
                        retry_count,
                        wait_time,
                    )
                    time.sleep(wait_time)
                    continue

                if allow_fallback and current_model != resolved_fallback:
                    logger.warning(
                        "Gemini model %s failed, falling back to %s.",
                        current_model,
                        resolved_fallback,
                    )
                    return self.generate_json(
                        prompt,
                        schema,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        retry_count=1,
                        allow_fallback=False,
                        model=resolved_fallback,
                        fallback_model=resolved_fallback,
                        system_instruction=system_instruction,
                    )

                raise

        if last_exception is not None:
            raise last_exception
        raise RuntimeError("Gemini request failed without an exception")

    def generate_text(
        self,
        prompt: str,
        *,
        temperature: float,
        max_output_tokens: int,
        retry_count: int = 3,
        allow_fallback: bool = True,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        from google.genai import types

        current_model = model or self.config.model
        resolved_fallback = fallback_model or self.config.fallback_model
        last_exception: Exception | None = None

        for attempt in range(retry_count):
            try:
                self.rate_limiter.acquire()
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=prompt)],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        system_instruction=system_instruction,
                    ),
                )

                # Recorded before validating: a truncated or empty response still
                # consumed input tokens and still bills. Those calls are exactly
                # the ones a cost report needs to show -- on models with thinking
                # enabled they are the expensive failure mode.
                self._record_usage(response, current_model)

                if not response.candidates or not response.candidates[0].content.parts:
                    finish_reason = (
                        response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
                    )
                    raise ValueError(
                        f"Gemini returned empty response (finish_reason: {finish_reason})"
                    )

                return response.text.strip()
            except BudgetExhaustedError:
                raise
            except Exception as exc:
                last_exception = exc
                if self._is_location_precondition(exc):
                    logger.error(
                        "Gemini location precondition failed for model %s (fallback %s). "
                        "This is typically a key/project policy or hosting egress geolocation issue; "
                        "model fallback will not resolve it.",
                        current_model,
                        resolved_fallback,
                    )
                    raise

                if self._is_retryable(exc) and attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "Gemini capacity issue. Retry %s/%s after %ss.",
                        attempt + 1,
                        retry_count,
                        wait_time,
                    )
                    time.sleep(wait_time)
                    continue

                if allow_fallback and current_model != resolved_fallback:
                    logger.warning(
                        "Gemini model %s failed, falling back to %s.",
                        current_model,
                        resolved_fallback,
                    )
                    return self.generate_text(
                        prompt,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        retry_count=1,
                        allow_fallback=False,
                        model=resolved_fallback,
                        fallback_model=resolved_fallback,
                        system_instruction=system_instruction,
                    )

                raise

        if last_exception is not None:
            raise last_exception
        raise RuntimeError("Gemini request failed without an exception")

    def get_display_name(self, model_name: str) -> str:
        model_map = {
            "gemini-flash-lite-latest": "Gemini Flash Lite (Latest)",
            "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
            "gemini-2.0-flash": "Gemini 2.0 Flash",
            "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
            "gemini-3-flash-preview": "Gemini 3 Flash (Preview)",
            "gemini-3.1-flash-lite-preview": "Gemini 3.1 Flash Lite (Preview)",
            "gemini-1.5-flash": "Gemini 1.5 Flash",
            "gemini-1.5-pro": "Gemini 1.5 Pro",
        }
        return model_map.get(model_name, f"Gemini ({model_name})")

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        error_text = str(exc)
        return (
            "429" in error_text
            or "ResourceExhausted" in error_text
            or "Resource exhausted" in error_text
        )

    @staticmethod
    def _is_location_precondition(exc: Exception) -> bool:
        error_text = str(exc)
        return (
            "FAILED_PRECONDITION" in error_text
            and "location is not supported" in error_text.lower()
        )


def build_provider(
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    fallback_model: Optional[str] = None,
    client: Any | None = None,
    rate_limiter: Any | None = None,
) -> tuple[GeminiProvider, AIProviderConfig]:
    """Build a Gemini provider instance and return it with its resolved config."""
    config = resolve_provider_config(api_key=api_key, model=model, fallback_model=fallback_model)
    return GeminiProvider(config, client=client, rate_limiter=rate_limiter), config
