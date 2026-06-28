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


def validate_charge_math(plan) -> list[str]:
    """
    Validate that a TurnPlan's Charge math is internally consistent.

    charge_cost/charge_after are engine-derived: TurnPlanner builds each
    candidate sequence by actually applying the action through GameEngine
    and reading the resulting Charge back off the game state (see
    enumerator.py's _action_charge_cost and turn_planner.py's
    convert_sequence_to_turn_plan with trust_action_costs=True). The LLM
    only picks which pre-built sequence to use by index — it never
    generates a Charge number itself. So a mismatch here is a real bug in
    plan construction, not LLM noise, and is worth a hard assertion.

    Uses TurnPlanner._CHARGE_GAIN_ON_PLAY (mirrored and pinned by
    tests/test_charge_gain_tables.py) instead of a separately maintained
    cost table, to avoid the two drifting apart.

    Returns a list of human-readable errors; empty list if the plan is
    internally consistent.
    """
    running_charge = plan.charge_start
    errors: list[str] = []

    for i, action in enumerate(plan.action_sequence, 1):
        if action.action_type == "end_turn":
            continue

        charge_gain = (
            TurnPlanner._CHARGE_GAIN_ON_PLAY.get(action.card_name, 0)
            if action.action_type == "play_card"
            else 0
        )
        expected_charge = running_charge - action.charge_cost + charge_gain

        if expected_charge < 0:
            errors.append(
                f"Action {i} ({action.card_name}): {running_charge} - "
                f"{action.charge_cost} + {charge_gain} = {expected_charge} (negative!)"
            )
        elif action.charge_after != expected_charge:
            errors.append(
                f"Action {i} ({action.card_name}): charge_after mismatch - "
                f"reported {action.charge_after}, expected {expected_charge} "
                f"({running_charge} - {action.charge_cost} + {charge_gain})"
            )

        running_charge = max(0, expected_charge)

    return errors