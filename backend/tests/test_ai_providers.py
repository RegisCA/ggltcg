"""Unit tests for AI provider configuration, selection, and planner mode resolution."""

from game_engine.ai.llm_player import LLMPlayer
from game_engine.ai.providers import OpenAICompatibleProvider, build_provider, resolve_provider_config
from game_engine.ai.turn_planner import get_planner_mode, ai_version_to_planner_mode


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