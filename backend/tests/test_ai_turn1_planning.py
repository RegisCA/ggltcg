"""
Live-LLM strategic-quality regression tests for the turn planner.

Unlike most live-LLM AI tests, the assertions here don't rely on
ActionValidator already filtering the wrong choice out of the enumerator's
candidate sequences (that case is tautological — see the 2026-06 AI test
audit in KNOWN_ISSUES.md) or on engine-derived Charge math (also
tautological by construction). Each test here gates on a scenario where the
"wrong" answer is still a legal, enumerable sequence, so a real strategic
mistake by the strategic-selection LLM call can actually be caught:

- ``TestWinningTussle``: passing (end_turn) is always legally available, so
  the AI choosing not to take a lethal tussle is a real failure mode.
- ``TestKnightEfficiency``: wasting an Archer shot on a target Knight will
  auto-break anyway is a legal sequence the AI must avoid by judgment, not
  by engine restriction.
- ``TestCombatMath::test_attacker_wins_clean``: requires the AI to choose to
  tussle at all (not guaranteed); the resulting Charge/break count is
  engine-derived once a tussle is chosen, but choosing it is not.

Run with: pytest tests/test_ai_turn1_planning.py -v -s
"""

import pytest
from pathlib import Path

# Add backend/src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards
from ai_test_support import has_valid_ai_api_key, build_turn_planner


# Skip all tests if no valid API key
def _has_valid_api_key():
    return has_valid_ai_api_key()


pytestmark = pytest.mark.skipif(
    not _has_valid_api_key(),
    reason="No valid AI provider API key found - skipping live LLM tests"
)


@pytest.fixture
def turn_planner():
    """Create a TurnPlanner instance for testing."""
    return build_turn_planner()


def log_plan(plan, title: str):
    """Log plan details for debugging."""
    print("\n" + "=" * 70)
    print(f"📋 {title}")
    print("=" * 70)
    print(f"Threat Assessment: {plan.threat_assessment[:100]}...")
    print(f"Resources: {plan.resources_summary[:100]}...")
    print(f"Selected Strategy: {plan.selected_strategy}")
    print(f"\nSequences Considered:")
    for seq in plan.sequences_considered:
        print(f"  • {seq}")
    print(f"\nAction Sequence (Charge: {plan.charge_start} → {plan.charge_after_plan}):")
    for i, action in enumerate(plan.action_sequence, 1):
        target = f" → {action.target_names}" if action.target_names else ""
        print(f"  {i}. {action.action_type}: {action.card_name or 'N/A'}{target} "
              f"(cost: {action.charge_cost}, charge_after: {action.charge_after})")
    print(f"\nExpected Cards Slept: {plan.expected_cards_broken}")
    print(f"Plan Reasoning: {plan.plan_reasoning}")
    if plan.residual_charge_justification:
        print(f"Residual Charge Justification: {plan.residual_charge_justification}")
    print("=" * 70)


class TestWinningTussle:
    """
    Tests for endgame scenarios where the AI should tussle to win.

    Issue: AI hallucinated "opponent has no toys" when opponent clearly had Umbruh.
    This led to invalid direct_attack when tussle was the winning move.

    Key insight: Trading toys (mutual destruction) is WINNING if it breaks
    the opponent's last card!
    """

    def test_must_tussle_to_win_not_direct_attack(self, turn_planner):
        """
        Test that AI recognizes tussle is required when opponent has toys.

        Scenario: Turn 8, both players have 5/6 cards broken.
        - AI has Umbruh (4/4/4) in play, empty hand
        - Opponent has Umbruh (4/4/4) in play, empty hand

        CORRECT: Tussle Umbruh→Umbruh (trade, both die) = OPPONENT LOSES (6 cards broken)!
        WRONG: Pass without tussling, leaving a free win on the table.

        Note: direct_attack while the opponent has a toy in play isn't a
        legal action at all (ActionValidator never offers it), so that
        failure mode can't occur here regardless of AI quality. The only
        real risk this test catches is the AI passing instead of taking the
        lethal tussle, since passing (end_turn) is always legally available.
        """
        # This is the exact scenario from the user's bug report
        setup, cards = create_game_with_cards(
            player1_hand=[],  # Empty hand
            player1_in_play=["Umbruh"],
            player1_break=["Archer", "Surge", "Paper Plane", "Wake", "Knight"],  # 5 broken
            player2_hand=[],  # Empty hand
            player2_in_play=["Umbruh"],
            player2_break=["Surge", "Wake", "Knight", "Paper Plane", "Archer"],  # 5 broken
            player1_charge=4,  # Plenty of Charge
            player2_charge=1,
            active_player="player1",
            turn_number=8,
        )

        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )

        assert plan is not None
        log_plan(plan, "WINNING TUSSLE: Must Tussle When Opponent Has Toys")

        has_tussle = any(
            action.action_type == "tussle"
            for action in plan.action_sequence
        )

        # The winning play is to tussle
        assert has_tussle, \
            "AI should have used tussle to attack opponent's Umbruh! " \
            "With 5/6 cards broken, one tussle (even a trade) wins the game."

        print("\n✓ AI correctly chose tussle over passing")
        print("  This scenario breaks opponent's 6th card = VICTORY!")


class TestKnightEfficiency:
    def test_no_wasted_archer_before_knight(self, turn_planner):
        """Verify AI doesn't waste Archer shots before Knight tussle."""
        setup, cards = create_game_with_cards(
            player1_hand=[],
            player1_in_play=["Knight", "Archer"],
            player2_hand=[],
            player2_in_play=["Umbruh"],
            player1_charge=4,
            player2_charge=0,
            active_player="player1",
            turn_number=2,
        )

        plan = turn_planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None
        log_plan(plan, "KNIGHT EFFICIENCY: No Wasted Archer Shots")

        archer_use = next((a for a in plan.action_sequence if a.action_type == "activate_ability" and "Umbruh" in a.target_names), None)
        knight_tussle = next((a for a in plan.action_sequence if a.action_type == "tussle" and a.card_name == "Knight"), None)

        if knight_tussle and archer_use:
             pytest.fail("AI wasted Archer ability on a target that Knight was going to auto-break!")


class TestCombatMath:
    def test_attacker_wins_clean(self, turn_planner):
        """Verify the AI chooses to tussle in an attacker-advantage trade.

        The resulting break count is engine-derived (the enumerator already
        simulated the outcome for real), not AI-predicted — what this test
        actually verifies is that the AI chooses to tussle at all rather
        than passing on a clearly favorable trade.
        """
        setup, cards = create_game_with_cards(
            player1_hand=[],
            player1_in_play=["Umbruh"], # 4/4/4
            player2_hand=[],
            player2_in_play=["Umbruh"], # 4/4/4
            player1_charge=2,
            player2_charge=0,
            active_player="player1",
            turn_number=2,
        )

        plan = turn_planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None
        log_plan(plan, "COMBAT MATH: Attacker Advantage")

        # Expect 1 card slept (opponent), not 2
        assert plan.expected_cards_broken == 1, \
            f"AI predicted {plan.expected_cards_broken} cards slept. Should be 1 (attacker wins clean due to SPD bonus)."
