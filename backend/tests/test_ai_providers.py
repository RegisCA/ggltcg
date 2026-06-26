"""Unit tests for AI provider configuration, selection, and planner mode resolution."""

from types import SimpleNamespace

from game_engine.ai.llm_player import LLMPlayer
from game_engine.ai.providers import (
    AIProviderConfig,
    GeminiProvider,
    OpenAICompatibleProvider,
    build_provider,
    resolve_provider_config,
)
from game_engine.ai.turn_planner import get_planner_mode, ai_version_to_planner_mode


class _FakeGeminiModels:
    """Records generate_content calls and returns a minimal well-formed response."""

    def __init__(self):
        self.calls: list[dict] = []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        part = SimpleNamespace(text='{"ok": true}')
        content = SimpleNamespace(parts=[part])
        candidate = SimpleNamespace(content=content, finish_reason="STOP")
        return SimpleNamespace(candidates=[candidate], text='{"ok": true}')


class _FakeGeminiClient:
    def __init__(self):
        self.models = _FakeGeminiModels()


def _build_fake_gemini_provider() -> tuple[GeminiProvider, _FakeGeminiClient]:
    config = AIProviderConfig(
        provider="gemini", api_key="x" * 32, model="gemini-test", fallback_model="gemini-test"
    )
    client = _FakeGeminiClient()
    return GeminiProvider(config, client=client), client


def test_gemini_generate_json_passes_system_instruction_via_config() -> None:
    """system_instruction must reach GenerateContentConfig, not be concatenated into the prompt."""
    provider, client = _build_fake_gemini_provider()

    provider.generate_json(
        "USER PROMPT TEXT",
        {"type": "object"},
        temperature=0.4,
        max_output_tokens=200,
        system_instruction="SYSTEM TEXT",
    )

    call = client.models.calls[0]
    assert call["config"].system_instruction == "SYSTEM TEXT"
    sent_text = call["contents"][0].parts[0].text
    assert sent_text == "USER PROMPT TEXT"
    assert "SYSTEM TEXT" not in sent_text


def test_gemini_generate_text_passes_system_instruction_via_config() -> None:
    provider, client = _build_fake_gemini_provider()

    provider.generate_text(
        "USER PROMPT TEXT",
        temperature=0.4,
        max_output_tokens=200,
        system_instruction="SYSTEM TEXT",
    )

    call = client.models.calls[0]
    assert call["config"].system_instruction == "SYSTEM TEXT"
    sent_text = call["contents"][0].parts[0].text
    assert sent_text == "USER PROMPT TEXT"


def test_gemini_generate_json_without_system_instruction() -> None:
    """No system_instruction passed should leave the prompt and config field untouched."""
    provider, client = _build_fake_gemini_provider()

    provider.generate_json(
        "USER PROMPT TEXT",
        {"type": "object"},
        temperature=0.4,
        max_output_tokens=200,
    )

    call = client.models.calls[0]
    assert call["config"].system_instruction is None
    assert call["contents"][0].parts[0].text == "USER PROMPT TEXT"


def test_resolve_provider_config_uses_gemini_legacy_env(monkeypatch) -> None:
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("AI_FALLBACK_MODEL", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "g" * 32)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")

    config = resolve_provider_config()

    assert config.provider == "gemini"
    assert config.model == "gemini-3.1-flash-lite-preview"
    assert config.fallback_model == "gemini-2.5-flash-lite"


def test_build_provider_returns_openai_compatible_for_groq(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "g" * 32)
    monkeypatch.setenv("AI_MODEL", "llama-3.1-8b-instant")

    provider, config = build_provider()

    assert config.provider == "groq"
    assert config.model == "llama-3.1-8b-instant"
    assert isinstance(provider, OpenAICompatibleProvider)


def test_llm_player_accepts_groq_provider(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "g" * 32)

    player = LLMPlayer(provider="groq", model="llama-3.1-8b-instant")

    assert player.provider == "groq"
    assert player.model_name == "llama-3.1-8b-instant"
    assert player.get_endpoint_name() == "Groq (llama-3.1-8b-instant)"


def test_parse_duration_seconds_handles_groq_header_format() -> None:
    assert OpenAICompatibleProvider._parse_duration_seconds("7.66s") == 7.66
    assert OpenAICompatibleProvider._parse_duration_seconds("2m59.56s") == 179.56


def test_get_planner_mode_defaults_to_single(monkeypatch) -> None:
    monkeypatch.delenv("AI_PLANNER_MODE", raising=False)
    monkeypatch.delenv("AI_VERSION", raising=False)

    assert get_planner_mode() == "single"


def test_get_planner_mode_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("AI_PLANNER_MODE", "dual")

    assert get_planner_mode() == "dual"


def test_get_planner_mode_falls_back_to_ai_version_4(monkeypatch) -> None:
    monkeypatch.delenv("AI_PLANNER_MODE", raising=False)
    monkeypatch.setenv("AI_VERSION", "4")

    assert get_planner_mode() == "dual"


def test_ai_version_to_planner_mode_mapping() -> None:
    assert ai_version_to_planner_mode(3) == "single"
    assert ai_version_to_planner_mode(4) == "dual"
    assert ai_version_to_planner_mode(2) == "single"