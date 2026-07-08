"""Gemini provider for the AI player's model backend."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

# NOTE: simulation.rate_limiter (BudgetExhaustedError, NoopLimiter) is
# imported lazily inside the functions/methods below rather than at module
# scope, to avoid a circular import: simulation/__init__.py imports
# runner.py, which imports llm_player.py, which imports this module — so a
# module-level import here would try to import the still-initializing
# `simulation` package.

DEFAULT_MODEL = "gemini-flash-lite-latest"  # Stable alias for latest Flash Lite; no geographic restriction
DEFAULT_FALLBACK_MODEL = "gemini-2.5-flash-lite"


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

    def __init__(self, config: AIProviderConfig, client: Any | None = None, rate_limiter: Any | None = None):
        self.config = config
        if client is None:
            from google import genai

            client = genai.Client(api_key=config.api_key)
        self.client = client
        if rate_limiter is None:
            from simulation.rate_limiter import NoopLimiter

            rate_limiter = NoopLimiter()
        self.rate_limiter = rate_limiter

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
        from simulation.rate_limiter import BudgetExhaustedError

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
        from simulation.rate_limiter import BudgetExhaustedError

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
