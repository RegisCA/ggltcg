"""
Phase 4.1 (WP-4): deterministic sequence enumerator.

Gates pinned here:

1. **Standard opening** — the Turn-1 Surge+Knight hand MUST yield the
   Surge → Knight → direct_attack line (the canonical optimal opener).
2. **Validator agreement on common cards** — for these scenarios every
   enumerated sequence passes the live ``TurnPlanValidator`` (zero rejections).
   Note this is NOT a universal invariant: ``TurnPlanValidator`` is a weaker
   heuristic with incomplete hardcoded card knowledge and *will* false-reject
   some engine-legal lines (e.g. Raggy's 0-cost tussles, Jumpscare's
   return-to-hand), which is why it is advisory — not a filter — in enum mode
   (see test_enum_planner_integration.py). These scenarios use cards it models
   correctly, so agreement here is a useful regression on the enumerator output.
3. **Engine-derived legality** — "tussle the last toy away → direct_attack
   becomes legal" falls out of real transitions, not hand-written rules.
4. **Bounded time** — enumeration on a rich state stays in the low-ms range.
"""

import time

import pytest

from conftest import create_game_with_cards
from game_engine.ai.enumerator import enumerate_sequences
from game_engine.ai.validators.turn_plan_validator import TurnPlanValidator
from game_engine.ai.prompts.schemas import PlannedAction, TurnPlan


def _seq_to_plan(seq: dict, starting_cc: int) -> TurnPlan:
    """Build a TurnPlan from an enumerated sequence for validator cross-checking.

    Mirrors TurnPlanner._sequence_to_temp_plan (the path V4 uses to validate
    LLM sequences) so the cross-check exercises the real validators.
    """
    actions = []
    cc = starting_cc
    for action in seq.get("actions", []):
        cc_cost = action.get("cc_cost", 0)
        card_name = action.get("card_name") or ""
        cc_gain = 0
        if action.get("action_type") == "play_card":
            cc_gain = {"Surge": 1, "Rush": 2}.get(card_name, 0)
        cc_after = cc - cc_cost + cc_gain
        actions.append(PlannedAction(
            action_type=action.get("action_type", "end_turn"),
            card_id=action.get("card_id"),
            card_name=card_name,
            target_ids=action.get("target_ids"),
            target_names=action.get("target_names"),
            cc_cost=cc_cost,
            cc_after=max(0, cc_after),
            reasoning="",
        ))
        cc = cc_after
    return TurnPlan(
        threat_assessment="", resources_summary="", sequences_considered=[],
        selected_strategy="", action_sequence=actions, cc_start=starting_cc,
        cc_after_plan=max(0, cc), expected_cards_slept=seq.get("cards_slept", 0),
        plan_reasoning="",
    )


def _assert_all_sequences_valid(setup, player_id: str, sequences: list):
    """No enumerated sequence may be rejected by the live validator."""
    validator = TurnPlanValidator(setup.engine)
    starting_cc = setup.game_state.players[player_id].cc
    for i, seq in enumerate(sequences):
        plan = _seq_to_plan(seq, starting_cc)
        errors = validator.validate(plan, setup.game_state, player_id, starting_cc)
        assert not errors, (
            f"Sequence {i} ({seq['raw_string']}) rejected by validator: "
            f"{[e.message for e in errors]}"
        )


def _action_signature(seq: dict) -> list:
    """(action_type, card_name) tuples, dropping the trailing end_turn."""
    return [
        (a["action_type"], a.get("card_name"))
        for a in seq["actions"]
        if a["action_type"] != "end_turn"
    ]


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def _turn1_surge_knight():
    """Standard Turn-1 opener (mirrors test_ai_standard_scenario)."""
    return create_game_with_cards(
        player1_hand=["Surge", "Knight", "Umbruh", "Wake"],
        player1_in_play=[],
        player2_hand=["Knight", "Ka", "Archer", "Wizard", "Drop", "Surge"],
        player2_in_play=[],
        player1_cc=2,
        player2_cc=0,
        active_player="player1",
        turn_number=1,
    )


def _tussle_then_direct():
    """P1 Knight in play vs a single opponent toy it can defeat, plus CC to attack."""
    return create_game_with_cards(
        player1_hand=[],
        player1_in_play=["Knight"],
        player2_hand=["Ka", "Wizard"],
        player2_in_play=["Paper Plane"],
        player1_cc=5,
        player2_cc=0,
        active_player="player1",
        turn_number=3,
    )


def _archer_scenario():
    """P1 Archer in play with CC, opponent toys to whittle down."""
    return create_game_with_cards(
        player1_hand=["Surge"],
        player1_in_play=["Archer", "Knight"],
        player2_hand=["Ka"],
        player2_in_play=["Paper Plane", "Wizard"],
        player1_cc=6,
        player2_cc=0,
        active_player="player1",
        turn_number=4,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_turn1_includes_surge_knight_direct_attack():
    setup, _ = _turn1_surge_knight()
    sequences = enumerate_sequences(setup.game_state, "player1")

    signatures = [_action_signature(s) for s in sequences]
    target = [("play_card", "Surge"), ("play_card", "Knight"), ("direct_attack", "Knight")]
    assert target in signatures, (
        "Enumerator must include Surge → Knight → direct_attack.\n"
        f"Got: {signatures}"
    )


def test_turn1_top_ranked_is_aggressive_opener():
    """The lethal/aggressive line should rank at or near the top (most sleeps, 0 waste)."""
    setup, _ = _turn1_surge_knight()
    sequences = enumerate_sequences(setup.game_state, "player1")
    # Best sequence should sleep a card and spend its CC efficiently.
    best = sequences[0]
    assert best["cards_slept"] >= 1
    assert best["cc_available"] - best["total_cc_spent"] <= 1  # ≤1 CC wasted


def test_tussle_unlocks_direct_attack():
    setup, _ = _tussle_then_direct()
    sequences = enumerate_sequences(setup.game_state, "player1")

    signatures = [_action_signature(s) for s in sequences]
    has_tussle_then_direct = any(
        [at for at, _ in sig] == ["tussle", "direct_attack"]
        for sig in signatures
    )
    assert has_tussle_then_direct, (
        "After tussling away the only opponent toy, direct_attack must become "
        f"legal in the same line.\nGot: {signatures}"
    )


@pytest.mark.parametrize("scenario", [
    _turn1_surge_knight,
    _tussle_then_direct,
    _archer_scenario,
])
def test_all_enumerated_sequences_pass_validator(scenario):
    setup, _ = scenario()
    sequences = enumerate_sequences(setup.game_state, "player1")
    assert sequences, "Enumerator should produce at least one sequence"
    _assert_all_sequences_valid(setup, "player1", sequences)


def test_enumeration_is_bounded_and_fast():
    setup, _ = _archer_scenario()  # richest scenario (2 toys + abilities + CC)
    start = time.perf_counter()
    sequences = enumerate_sequences(setup.game_state, "player1")
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"\nenumeration: {len(sequences)} seqs in {elapsed_ms:.1f} ms")
    assert len(sequences) <= 12  # capped
    assert elapsed_ms < 750, f"enumeration too slow: {elapsed_ms:.1f} ms"


def test_pass_line_is_always_offered():
    """Even with actions available, the explicit pass (end_turn only) is recorded."""
    setup, _ = _turn1_surge_knight()
    sequences = enumerate_sequences(setup.game_state, "player1")
    signatures = [_action_signature(s) for s in sequences]
    assert [] in signatures, (
        "The pure pass line (do nothing, then end_turn) must be among the options.\n"
        f"Got: {signatures}"
    )


def test_pointless_self_drop_ranks_below_pass():
    """A self-Drop with no payoff must rank below the pass line.

    With no opponent cards in play, Drop can only target the AI's own toy.
    Sleeping it gains nothing, so the perverse "spending CC lowers waste" pull
    must not float the self-Drop above doing nothing.
    """
    setup, _ = create_game_with_cards(
        player1_hand=["Drop"],
        player1_in_play=["Knight"],
        player2_hand=[],
        player2_in_play=[],
        player1_cc=2,
        player2_cc=0,
        active_player="player1",
        turn_number=3,
    )
    sequences = enumerate_sequences(setup.game_state, "player1")
    signatures = [_action_signature(s) for s in sequences]

    pass_idx = signatures.index([])
    drop_idx = signatures.index([("play_card", "Drop")])
    assert pass_idx < drop_idx, (
        "Pointless self-Drop should rank below the pass line.\n"
        f"Got order: {signatures}"
    )


def test_wake_drop_combo_not_penalized():
    """Drop own card then Wake it back is a real combo and must not be penalized.

    The card is recovered to hand, so net own-cards-slept is 0 — the combo line
    should rank at or above a bare self-Drop that leaves the card asleep.
    """
    setup, _ = create_game_with_cards(
        player1_hand=["Drop", "Wake"],
        player1_in_play=["Knight"],
        player2_hand=[],
        player2_in_play=[],
        player1_cc=3,
        player2_cc=0,
        active_player="player1",
        turn_number=3,
    )
    sequences = enumerate_sequences(setup.game_state, "player1")
    signatures = [_action_signature(s) for s in sequences]

    combo = [("play_card", "Drop"), ("play_card", "Wake")]
    bare_drop = [("play_card", "Drop")]
    assert combo in signatures, (
        f"Drop→Wake recovery combo should be enumerated.\nGot: {signatures}"
    )
    if bare_drop in signatures:
        assert signatures.index(combo) <= signatures.index(bare_drop), (
            "Recovery combo should rank at or above a bare self-Drop.\n"
            f"Got order: {signatures}"
        )


def test_no_actions_returns_end_turn_line():
    """A state with nothing to do still yields a usable pass line."""
    setup, _ = create_game_with_cards(
        player1_hand=[], player1_in_play=[], player1_cc=0,
        active_player="player1", turn_number=2,
    )
    sequences = enumerate_sequences(setup.game_state, "player1")
    assert len(sequences) == 1
    assert sequences[0]["actions"][0]["action_type"] == "end_turn"
