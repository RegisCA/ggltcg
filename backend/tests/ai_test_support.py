"""Shared helpers for provider-aware AI tests."""

from __future__ import annotations

from game_engine.ai.providers import build_provider
from game_engine.ai.turn_planner import TurnPlanner, ai_version_to_planner_mode


def has_valid_ai_api_key() -> bool:
    """Return True when the configured provider has a plausible API key."""
    try:
        _, config = build_provider()
    except ValueError:
        return False

    return bool(config.api_key and not config.api_key.startswith("dummy") and len(config.api_key) > 20)


def build_turn_planner(
    ai_version: int | None = None,
    planner_mode: str | None = None,
) -> TurnPlanner:
    """Create a provider-aware TurnPlanner for live LLM tests.

    Args:
        ai_version: Legacy version int (3 or 4). Converted to planner_mode.
        planner_mode: 'single' or 'dual'. Takes precedence over ai_version.
    """
    provider_client, config = build_provider()

    # Convert legacy ai_version to planner_mode if planner_mode not given.
    effective_mode = planner_mode
    if effective_mode is None and ai_version is not None:
        effective_mode = ai_version_to_planner_mode(ai_version)

    return TurnPlanner(
        client=getattr(provider_client, "client", None),
        provider_client=provider_client,
        provider=config.provider,
        model_name=config.model,
        fallback_model=config.fallback_model,
        planner_mode=effective_mode,
    )