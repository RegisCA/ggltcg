"""
The turn planner trusts enumerated sequences at their real, engine-derived cost.

Enumerated sequences are engine-legal by construction. These tests pin that the
planner takes such sequences at face value rather than re-deriving costs from
hand-written assumptions (e.g. "tussles always cost 2") that would be wrong for
cards like Raggy (0-cost tussles) or Jumpscare (return-to-hand, not break). The
planner plans normally — with exactly ONE LLM call (the strategic-selection
request).

Uses a stubbed selector, so it costs no API credits.
"""

import json

from conftest import create_game_with_cards
from game_engine.ai.turn_planner import TurnPlanner


class _StubSelector:
    """Stands in for the Request-2 strategic selector (the only LLM call in enum)."""

    def __init__(self):
        self.calls = 0

    def generate_json(self, prompt, schema, **kwargs):
        self.calls += 1
        return json.dumps({"selected_index": 0, "reasoning": "stub selection"})

    def get_display_name(self, model):  # pragma: no cover - cosmetic
        return "stub"


def _enum_planner(stub):
    # Passing provider_client explicitly skips build_provider() — no API key needed.
    return TurnPlanner(
        client=None, model_name="m", fallback_model="f",
        provider_client=stub,
    )


def test_enum_keeps_engine_derived_costs_and_makes_one_call():
    """Raggy's 0-cost attacks must survive at their real cost, not a hand-written one."""
    setup, _ = create_game_with_cards(
        player1_in_play=["Raggy"],
        player2_in_play=["Gibbers"],
        player2_hand=["Ka"],
        player1_charge=2,
        player2_charge=0,
        active_player="player1",
        turn_number=4,
    )
    stub = _StubSelector()
    plan = _enum_planner(stub).create_plan(setup.game_state, "player1", setup.engine)

    assert plan is not None, "planner must not give up on validator false-positives"
    assert stub.calls == 1, "planner should make exactly ONE LLM call (selection only)"
    assert any(a.action_type != "end_turn" for a in plan.action_sequence), \
        "plan should take a real action, not just end the turn"

    # Raggy's tussles cost 0. With only 2 Charge, canonical-cost grounding (2/attack)
    # would drop these as "unaffordable". The enum plan must keep them at their
    # real engine cost (0) — pins that enum trusts engine-derived costs and skips
    # _reground_charge_chain (Copilot review, turn_planner.py).
    attacks = [a for a in plan.action_sequence if a.action_type in ("tussle", "direct_attack")]
    assert attacks, "discounted Raggy attacks must survive plan grounding, not be dropped"
    assert all(a.charge_cost == 0 for a in attacks), \
        f"Raggy attacks should carry real cost 0, got {[a.charge_cost for a in attacks]}"


def test_enum_handles_jumpscare_toy_return_without_fallback():
    """Jumpscare's return-to-hand is a real engine effect; enum must keep the line."""
    setup, _ = create_game_with_cards(
        player1_hand=["Jumpscare"],
        player1_in_play=["Knight"],
        player2_in_play=["Gibbers"],
        player2_hand=["Ka"],
        player1_charge=5,
        player2_charge=0,
        active_player="player1",
        turn_number=4,
    )
    stub = _StubSelector()
    plan = _enum_planner(stub).create_plan(setup.game_state, "player1", setup.engine)

    assert plan is not None
    assert stub.calls == 1
