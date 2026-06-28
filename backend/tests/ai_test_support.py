"""Shared helpers for provider-aware AI tests."""

from __future__ import annotations

from game_engine.ai.providers import build_provider
from game_engine.ai.turn_planner import TurnPlanner


def has_valid_ai_api_key() -> bool:
    """Return True when Gemini has a plausible API key configured."""
    try:
        _, config = build_provider()
    except ValueError:
        return False

    return bool(config.api_key and not config.api_key.startswith("dummy") and len(config.api_key) > 20)


def build_turn_planner() -> TurnPlanner:
    """Create a provider-aware TurnPlanner for live LLM tests."""
    provider_client, config = build_provider()

    return TurnPlanner(
        client=getattr(provider_client, "client", None),
        provider_client=provider_client,
        model_name=config.model,
        fallback_model=config.fallback_model,
    )