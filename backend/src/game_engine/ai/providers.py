"""Provider abstraction for AI model backends."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


SUPPORTED_PROVIDERS = ("gemini", "groq", "openrouter")

_DEFAULT_MODELS = {
    "gemini": "gemini-3.1-flash-lite-preview",
    "groq": "llama-3.1-8b-instant",
    "openrouter": "openai/gpt-oss-20b",
}

_API_KEY_ENV_VARS = {
    "gemini": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


@dataclass(frozen=True)
class AIProviderConfig:
    """Resolved provider configuration."""

    provider: str
    api_key: str
    model: str
    fallback_model: str
    base_url: Optional[str] = None


def get_default_provider_name() -> str:
    """Get the default provider from environment."""
    provider_name = os.getenv("AI_PROVIDER", "gemini").strip().lower()
    if provider_name not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported AI provider '{provider_name}'. Supported providers: {SUPPORTED_PROVIDERS}"
        )
    return provider_name


def get_api_key_env_var(provider_name: str) -> str:
    """Get the API key environment variable for a provider."""
    normalized = provider_name.strip().lower()
    if normalized not in _API_KEY_ENV_VARS:
        raise ValueError(f"Unsupported AI provider '{provider_name}'")
    return _API_KEY_ENV_VARS[normalized]


def get_default_model(provider_name: str) -> str:
    """Get the default model for a provider."""
    normalized = provider_name.strip().lower()
    if normalized not in _DEFAULT_MODELS:
        raise ValueError(f"Unsupported AI provider '{provider_name}'")
    return _DEFAULT_MODELS[normalized]


def resolve_provider_config(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    fallback_model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> AIProviderConfig:
    """Resolve provider configuration from arguments and environment."""
    resolved_provider = (provider_name or get_default_provider_name()).strip().lower()
    if resolved_provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported AI provider '{resolved_provider}'. Supported providers: {SUPPORTED_PROVIDERS}"
        )

    provider_key_var = get_api_key_env_var(resolved_provider)
    resolved_api_key = api_key or os.getenv("AI_API_KEY") or os.getenv(provider_key_var)

    if not resolved_api_key:
        raise ValueError(
            f"API key required for provider '{resolved_provider}'. "
            f"Set {provider_key_var} or AI_API_KEY."
        )

    if resolved_provider == "gemini":
        resolved_model = model or os.getenv("AI_MODEL") or os.getenv("GEMINI_MODEL") or get_default_model("gemini")
        resolved_fallback = (
            fallback_model
            or os.getenv("AI_FALLBACK_MODEL")
            or os.getenv("GEMINI_FALLBACK_MODEL")
            or resolved_model
        )
        resolved_base_url = None
    else:
        resolved_model = model or os.getenv("AI_MODEL") or get_default_model(resolved_provider)
        resolved_fallback = fallback_model or os.getenv("AI_FALLBACK_MODEL") or resolved_model
        resolved_base_url = base_url or os.getenv("AI_BASE_URL") or _BASE_URLS[resolved_provider]

    return AIProviderConfig(
        provider=resolved_provider,
        api_key=resolved_api_key,
        model=resolved_model,
        fallback_model=resolved_fallback,
        base_url=resolved_base_url,
    )


class BaseLLMProvider:
    """Base class for model providers."""

    def __init__(self, config: AIProviderConfig):
        self.config = config

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
        raise NotImplementedError

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
        raise NotImplementedError

    def get_display_name(self, model_name: str) -> str:
        return f"{self.config.provider.title()} ({model_name})"


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider using the google-genai SDK."""

    def __init__(self, config: AIProviderConfig, client: Any | None = None):
        super().__init__(config)
        if client is None:
            from google import genai

            client = genai.Client(api_key=config.api_key)
        self.client = client

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
        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        last_exception: Exception | None = None

        for attempt in range(retry_count):
            try:
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=full_prompt)],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        response_mime_type="application/json",
                        response_json_schema=schema,
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
            except Exception as exc:
                last_exception = exc
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
                        "Gemini model %s exhausted, falling back to %s.",
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
        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        last_exception: Exception | None = None

        for attempt in range(retry_count):
            try:
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=full_prompt)],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
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
            except Exception as exc:
                last_exception = exc
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
                        "Gemini model %s exhausted, falling back to %s.",
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


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider for OpenAI-compatible chat completions APIs."""

    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        self.client = httpx.Client(
            base_url=config.base_url.rstrip("/"),
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

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
        json_prompt = self._build_json_prompt(prompt, schema)
        json_system_instruction = self._build_json_system_instruction(system_instruction)
        payload = {
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
        return self._generate_response(
            json_prompt,
            payload=payload,
            retry_count=retry_count,
            allow_fallback=allow_fallback,
            model=model,
            fallback_model=fallback_model,
            system_instruction=json_system_instruction,
        )

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
        payload = {
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
        return self._generate_response(
            prompt,
            payload=payload,
            retry_count=retry_count,
            allow_fallback=allow_fallback,
            model=model,
            fallback_model=fallback_model,
            system_instruction=system_instruction,
        )

    def get_display_name(self, model_name: str) -> str:
        return f"{self.config.provider.title()} ({model_name})"

    def _generate_response(
        self,
        prompt: str,
        *,
        payload: dict[str, Any],
        retry_count: int,
        allow_fallback: bool,
        model: Optional[str],
        fallback_model: Optional[str],
        system_instruction: Optional[str],
    ) -> str:
        current_model = model or self.config.model
        resolved_fallback = fallback_model or self.config.fallback_model
        last_exception: Exception | None = None

        for attempt in range(retry_count):
            try:
                request_payload = {
                    "model": current_model,
                    "messages": self._build_messages(prompt, system_instruction),
                    **payload,
                }
                response = self.client.post(
                    "/chat/completions",
                    headers=self._build_headers(),
                    json=request_payload,
                )
                response.raise_for_status()
                body = response.json()
                return self._extract_content(body)
            except httpx.HTTPStatusError as exc:
                last_exception = exc
                status_code = exc.response.status_code
                if status_code in {429, 500, 502, 503, 504} and attempt < retry_count - 1:
                    wait_time = self._get_retry_wait_seconds(exc.response, attempt)
                    logger.warning(
                        "%s API issue (%s). Retry %s/%s after %.2fs.",
                        self.config.provider,
                        status_code,
                        attempt + 1,
                        retry_count,
                        wait_time,
                    )
                    time.sleep(wait_time)
                    continue

                if allow_fallback and current_model != resolved_fallback:
                    logger.warning(
                        "%s model %s failed, falling back to %s.",
                        self.config.provider,
                        current_model,
                        resolved_fallback,
                    )
                    return self._generate_response(
                        prompt,
                        payload=payload,
                        retry_count=1,
                        allow_fallback=False,
                        model=resolved_fallback,
                        fallback_model=resolved_fallback,
                        system_instruction=system_instruction,
                    )

                raise
            except Exception as exc:
                last_exception = exc
                if allow_fallback and current_model != resolved_fallback:
                    logger.warning(
                        "%s model %s failed, falling back to %s.",
                        self.config.provider,
                        current_model,
                        resolved_fallback,
                    )
                    return self._generate_response(
                        prompt,
                        payload=payload,
                        retry_count=1,
                        allow_fallback=False,
                        model=resolved_fallback,
                        fallback_model=resolved_fallback,
                        system_instruction=system_instruction,
                    )
                raise

        if last_exception is not None:
            raise last_exception
        raise RuntimeError(f"{self.config.provider} request failed without an exception")

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.provider == "openrouter":
            headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL", "https://github.com/RegisCA/ggltcg")
            headers["X-Title"] = os.getenv("OPENROUTER_APP_NAME", "ggltcg")
        return headers

    @staticmethod
    def _get_retry_wait_seconds(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return max(float(retry_after), 0.5)
            except ValueError:
                pass

        reset_tokens = response.headers.get("x-ratelimit-reset-tokens")
        if reset_tokens:
            parsed = OpenAICompatibleProvider._parse_duration_seconds(reset_tokens)
            if parsed is not None:
                return max(parsed, 0.5)

        return float(2 ** attempt)

    @staticmethod
    def _parse_duration_seconds(value: str) -> float | None:
        total = 0.0
        matches = re.findall(r"(\d+(?:\.\d+)?)([hms])", value.strip().lower())
        if not matches:
            try:
                return float(value)
            except ValueError:
                return None

        for amount, unit in matches:
            numeric_amount = float(amount)
            if unit == "h":
                total += numeric_amount * 3600
            elif unit == "m":
                total += numeric_amount * 60
            else:
                total += numeric_amount

        return total

    @staticmethod
    def _build_json_prompt(prompt: str, schema: dict[str, Any]) -> str:
        schema_text = json.dumps(
            OpenAICompatibleProvider._trim_schema_for_prompt(schema),
            separators=(",", ":"),
        ) if schema else "{}"
        return (
            f"{prompt}\n\n"
            "Return a valid JSON object only. Do not use markdown fences.\n"
            f"JSON schema reference: {schema_text}"
        )

    @staticmethod
    def _trim_schema_for_prompt(value: Any) -> Any:
        if isinstance(value, dict):
            trimmed: dict[str, Any] = {}
            for key, child in value.items():
                if key in {"default", "description", "examples", "propertyOrdering", "title"}:
                    continue
                trimmed[key] = OpenAICompatibleProvider._trim_schema_for_prompt(child)
            return trimmed
        if isinstance(value, list):
            return [OpenAICompatibleProvider._trim_schema_for_prompt(item) for item in value]
        return value

    @staticmethod
    def _build_json_system_instruction(system_instruction: Optional[str]) -> str:
        json_instruction = "You must respond with valid JSON only."
        if system_instruction:
            return f"{system_instruction}\n\n{json_instruction}"
        return json_instruction

    @staticmethod
    def _build_messages(prompt: str, system_instruction: Optional[str]) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def _extract_content(body: dict[str, Any]) -> str:
        choices = body.get("choices") or []
        if not choices:
            raise ValueError("Provider returned no choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            if text_parts:
                return "".join(text_parts).strip()
        raise ValueError(f"Unexpected content format from provider: {json.dumps(message)}")


def build_provider(
    provider_name: Optional[str] = None,
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    fallback_model: Optional[str] = None,
    base_url: Optional[str] = None,
    client: Any | None = None,
) -> tuple[BaseLLMProvider, AIProviderConfig]:
    """Build a provider instance and return it with its resolved config."""
    config = resolve_provider_config(
        provider_name=provider_name,
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        base_url=base_url,
    )

    if config.provider == "gemini":
        return GeminiProvider(config, client=client), config

    return OpenAICompatibleProvider(config), config