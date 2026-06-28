"""
Turn 1 Planning Regression Tests for AI v3.

Tests the exact scenarios from GitHub issues to prevent regressions:
- Issue #267: Charge budgeting - sequential state-tracking
- Issue #272: Drop action card not understood

These tests validate that Turn 1 planning makes sense:
1. With 2 Charge, the AI should play defensive toys
2. Surge enables additional actions (Charge bridge concept)
3. Drop/Archer are useless when opponent has 0 toys

Run with: pytest tests/test_ai_turn1_planning.py -v -s
"""

import pytest
import os
from pathlib import Path

# Add backend/src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards
from ai_test_support import has_valid_ai_api_key, build_turn_planner, validate_charge_math


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


class TestTurn1WithSurge:
    """
    Tests for Turn 1 scenarios where Surge enables additional actions.
    
    Issue #267: AI fails to account for Charge gain from Surge when planning.
    The AI should recognize that:
    - 2 Charge + Surge = 3 Charge total spendable
    - 3 Charge enables: Surge (0) + Knight (1) + Direct Attack (2) = 1 card slept!
    """
    
    def test_turn1_surge_knight_direct_attack(self, turn_planner):
        """
        Turn 1: Surge + Knight + Direct Attack = 1 card slept.
        
        This is the exact scenario from Issue #267.
        Starting: 2 Charge, Hand has Surge and Knight
        Expected: Play Surge (+1 Charge) → Play Knight (1 Charge) → Direct Attack (2 Charge)
        Result: 3 Charge spent, 1 opponent card slept
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Dream", "Umbruh"],
            player1_in_play=[],
            player2_hand=["Knight", "Ka", "Archer", "Wizard", "Drop", "Surge"],
            player2_in_play=[],
            player1_charge=2,  # Turn 1 Charge
            player2_charge=0,
            active_player="player1",
            turn_number=1,
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None, "Plan should be generated"
        log_plan(plan, "TURN 1: Surge + Knight + Direct Attack Test")

        # Validate Charge math in the plan
        charge_errors = validate_charge_math(plan)
        assert not charge_errors, f"Plan has impossible Charge math: {charge_errors}"

        # The AI should find a way to break at least 1 card
        # With Surge + Knight + Direct Attack, this is achievable
        # But we only soft-assert this since the AI might find other valid plans
        if plan.expected_cards_broken == 0:
            print("\n⚠️ WARNING: AI chose to break 0 cards despite having Surge + Knight!")
            print("This may indicate the Surge Charge bridge concept isn't understood.")
    
    def test_turn1_surge_umbruh_direct_attack(self, turn_planner):
        """
        Turn 1: Surge + Umbruh + Direct Attack = 1 card slept.
        
        Alternative valid plan using Umbruh instead of Knight.
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Surge", "Umbruh", "Ka", "Drop"],
            player1_in_play=[],
            player2_hand=["Knight", "Ka", "Archer", "Wizard", "Drop", "Surge"],
            player2_in_play=[],
            player1_charge=2,
            player2_charge=0,
            active_player="player1",
            turn_number=1,
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        log_plan(plan, "TURN 1: Surge + Umbruh + Direct Attack Test")

        # Validate Charge math in the plan
        charge_errors = validate_charge_math(plan)
        assert not charge_errors, f"Plan has impossible Charge math: {charge_errors}"


class TestTurn1DropTrap:
    """
    Tests for Turn 1 Drop trap detection.
    
    Issue #272: AI plays Drop on Turn 1 when opponent has 0 toys.
    The AI should recognize:
    - Drop REQUIRES a valid target (opponent toy IN PLAY)
    - On Turn 1 as first player, opponent has 0 toys
    - Playing Drop is a WASTE
    """
    
    def test_turn1_drop_without_targets(self, turn_planner):
        """
        Turn 1: Drop should NOT be played when opponent has 0 toys.
        
        This is the exact scenario from Issue #272.
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Drop", "Belchaletta", "Ka", "Sock Sorcerer", "Rush", "Jumpscare"],
            player1_in_play=[],
            player2_hand=["Knight", "Ka", "Archer", "Wizard", "Surge", "Umbruh"],
            player2_in_play=[],  # NO toys in play!
            player1_charge=2,
            player2_charge=0,
            active_player="player1",
            turn_number=1,
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        log_plan(plan, "TURN 1: Drop Trap Detection Test")
        
        # Check that Drop is NOT in the action sequence
        drop_played = any(
            action.card_name == "Drop" and action.action_type == "play_card"
            for action in plan.action_sequence
        )
        
        assert not drop_played, \
            "AI should NOT play Drop on Turn 1 when opponent has 0 toys in play! " \
            "Drop requires a valid target."
        
        # The AI should play Belchaletta instead (1 Charge defender)
        # This is a soft check - other defensive plays are also valid
        belchaletta_played = any(
            action.card_name == "Belchaletta"
            for action in plan.action_sequence
        )
        
        if not belchaletta_played:
            print("\n⚠️ Note: AI didn't play Belchaletta (the optimal Turn 1 play)")
            print("Check if another defensive toy was played instead.")


class TestTurn1ArcherTrap:
    """
    Tests for Turn 1 Archer ability trap detection.
    
    Issue #273: AI tries to use Archer ability when opponent has 0 toys.
    The AI should recognize:
    - Archer ability can ONLY target toys IN PLAY
    - On Turn 1 as first player, opponent has 0 toys
    - Archer ability is UNUSABLE
    """
    
    def test_turn1_archer_without_targets(self, turn_planner):
        """
        Turn 1: Archer ability should NOT be planned when opponent has 0 toys.
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Archer", "Knight", "Surge", "Ka"],
            player1_in_play=[],
            player2_hand=["Knight", "Ka", "Wizard", "Surge", "Drop", "Umbruh"],
            player2_in_play=[],  # NO toys in play!
            player1_charge=2,
            player2_charge=0,
            active_player="player1",
            turn_number=1,
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        log_plan(plan, "TURN 1: Archer Trap Detection Test")
        
        # Check that Archer ability is NOT in the action sequence
        archer_ability_used = any(
            action.card_name == "Archer" and action.action_type == "activate_ability"
            for action in plan.action_sequence
        )
        
        assert not archer_ability_used, \
            "AI should NOT use Archer ability when opponent has 0 toys in play! " \
            "Archer ability requires a valid target IN PLAY."
        
        # Playing Archer (0 Charge) as a blocker is VALID, just don't use ability
        archer_played = any(
            action.card_name == "Archer" and action.action_type == "play_card"
            for action in plan.action_sequence
        )
        
        if archer_played:
            print("\n✓ AI correctly played Archer without using its ability (no targets)")


class TestBreakZoneTrap:
    """
    Tests for Break Zone card trap detection.
    
    Bug found: AI tried to play_card Knight directly from Break Zone
    without using Wake first. This is ILLEGAL - you can only play cards
    from your HAND.
    
    The AI should recognize:
    - Break Zone cards are NOT playable directly
    - Wake (1 Charge) returns a card to HAND
    - Then you must PAY Charge to play the card from hand
    """
    
    def test_cannot_play_card_from_break_zone(self, turn_planner):
        """
        Test that AI uses Wake before trying to play a broken card.
        
        Scenario: Knight in break zone, Wake in hand, opponent has Knight.
        CORRECT: Wake → Knight returns to hand → play Knight → tussle
        WRONG: Directly try to play_card Knight from break zone (without Wake first)
        """
        # Set up a mid-game scenario where player needs to recover cards
        setup, cards = create_game_with_cards(
            player1_hand=["Wake", "Surge", "Archer"],
            player1_in_play=[],
            player1_break=["Knight", "Umbruh"],  # Cards in break zone
            player2_hand=["Ka", "Wizard", "Drop"],
            player2_in_play=["Knight"],
            player1_charge=6,  # Mid-game Charge
            player2_charge=0,
            active_player="player1",
            turn_number=4,
        )
        
        # Get the break zone card IDs for checking
        break_zone_ids = {card.id for card in setup.player1.break_zone}
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        log_plan(plan, "BREAK ZONE TRAP: Must Use Wake Before Playing Broken Card")
        
        # Track if Wake was played before any break zone card is played
        wake_played = False
        break_zone_card_played_without_wake = False
        
        for action in plan.action_sequence:
            if action.action_type == "play_card":
                if action.card_name == "Wake":
                    wake_played = True
                elif action.card_id in break_zone_ids:
                    # This card was originally in break zone
                    if not wake_played:
                        break_zone_card_played_without_wake = True
                        print(f"\n❌ CRITICAL: AI tried to play {action.card_name} (ID: {action.card_id}) "
                              f"directly from Break Zone WITHOUT using Wake first!")
        
        assert not break_zone_card_played_without_wake, \
            "AI tried to play a card from Break Zone without using Wake first! " \
            "Cards in Break Zone CANNOT be played directly - must use Wake to return to hand first."
        
        # If a break zone card was played after Wake, that's correct behavior
        break_zone_card_played_after_wake = any(
            action.action_type == "play_card" and action.card_id in break_zone_ids
            for action in plan.action_sequence
        ) and wake_played
        
        if break_zone_card_played_after_wake:
            print("\n✓ AI correctly used Wake before playing a card from break zone")
        elif not any(action.card_id in break_zone_ids for action in plan.action_sequence if action.action_type == "play_card"):
            print("\n⚠️ AI didn't try to play any cards from break zone (may have chosen a different valid strategy)")


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
        WRONG: Direct attack (illegal when opponent has toys in play!)
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
        
        # Check that AI correctly identified opponent has toys
        has_direct_attack = any(
            action.action_type == "direct_attack" 
            for action in plan.action_sequence
        )
        
        has_tussle = any(
            action.action_type == "tussle"
            for action in plan.action_sequence
        )
        
        # Critical check: direct_attack is ILLEGAL when opponent has toys!
        # EXCEPTION: If we tussle first to clear the board, then direct attack is valid.
        if has_direct_attack:
            # Find index of first direct attack
            da_index = next(i for i, a in enumerate(plan.action_sequence) if a.action_type == "direct_attack")
            # Check if there's a tussle before it
            tussle_before = any(a.action_type == "tussle" for a in plan.action_sequence[:da_index])
            
            if not tussle_before:
                print("\n❌ CRITICAL: AI used direct_attack when opponent has toys in play!")
                print("   This is ILLEGAL - must use tussle when opponent has toys!")
                assert False, \
                    "AI used direct_attack when opponent has toys in play! " \
                    "Direct attack is only legal when opponent has 0 toys. " \
                    "The AI hallucinated 'opponent has no toys' - this is a game state reading error."
            else:
                print("\n✅ AI correctly tussled first to clear board before direct attacking.")
        
        # The winning play is to tussle
        assert has_tussle, \
            "AI should have used tussle to attack opponent's Umbruh! " \
            "With 5/6 cards broken, one tussle (even a trade) wins the game."
        
        print("\n✓ AI correctly chose tussle over direct_attack")
        print("  This scenario breaks opponent's 6th card = VICTORY!")


class TestTurn1ChargeMathValidation:
    """
    Tests that Charge math is calculated correctly throughout the plan.
    
    These tests verify that charge_after values are consistent with the
    actual costs and gains in the action sequence.
    """
    
    def test_charge_math_consistency(self, turn_planner):
        """
        Verify Charge math is consistent throughout the plan.
        
        For each action:
        - charge_after should equal charge_before - charge_cost + charge_gain
        - charge_after should never be negative
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Umbruh", "Ka", "Drop", "Archer"],
            player1_in_play=[],
            player2_hand=["Knight", "Ka", "Wizard", "Surge", "Drop", "Umbruh"],
            player2_in_play=[],
            player1_charge=2,
            player2_charge=0,
            active_player="player1",
            turn_number=1,
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        log_plan(plan, "TURN 1: Charge Math Consistency Test")
        
        # Validate using shared function
        charge_errors = validate_charge_math(plan)
        assert len(charge_errors) == 0, \
            f"Plan has impossible Charge math: {charge_errors}"


class TestTurn1Regression:
    """
    Regression test suite - run all Turn 1 tests together to catch regressions.
    """
    
    def test_turn1_regression_suite(self, turn_planner):
        """
        Combined regression test for Turn 1 scenarios.
        
        This test runs multiple scenarios and reports all failures at once,
        making it easier to identify regressions.
        
        Note: Due to LLM non-determinism, we only check for CRITICAL errors
        (negative Charge, invalid targets) rather than expecting specific plans.
        """
        results = []
        
        # Test 1: Surge enables direct attack (but LLM might choose different valid plan)
        try:
            setup1, _ = create_game_with_cards(
                player1_hand=["Surge", "Knight", "Dream", "Umbruh"],
                player1_in_play=[],
                player2_in_play=[],
                player1_charge=2,
                turn_number=1,
            )
            plan1 = turn_planner.create_plan(setup1.game_state, "player1", setup1.engine)
            log_plan(plan1, "REGRESSION: Surge+Knight Test")
            
            # Check Charge math validity
            charge_errors = validate_charge_math(plan1)
            if charge_errors:
                # Only fail on actual math errors, not different valid plans
                results.append(("Surge+Knight", "FAIL", f"Charge math errors: {charge_errors}"))
            else:
                # Any valid plan is acceptable
                results.append(("Surge+Knight", "PASS", f"Valid plan, slept {plan1.expected_cards_broken} cards"))
        except Exception as e:
            results.append(("Surge+Knight", "ERROR", str(e)))
        
        # Test 2: Drop trap - MUST NOT play Drop
        try:
            setup2, _ = create_game_with_cards(
                player1_hand=["Drop", "Belchaletta", "Ka"],
                player1_in_play=[],
                player2_in_play=[],  # No targets for Drop!
                player1_charge=2,
                turn_number=1,
            )
            plan2 = turn_planner.create_plan(setup2.game_state, "player1", setup2.engine)
            log_plan(plan2, "REGRESSION: Drop Trap Test")
            
            drop_played = any(a.card_name == "Drop" for a in plan2.action_sequence if a.action_type == "play_card")
            if drop_played:
                results.append(("Drop trap", "FAIL", "Played Drop without valid targets"))
            else:
                results.append(("Drop trap", "PASS", "Correctly avoided Drop"))
        except Exception as e:
            results.append(("Drop trap", "ERROR", str(e)))
        
        # Print results summary
        print("\n" + "=" * 70)
        print("📊 TURN 1 REGRESSION TEST RESULTS")
        print("=" * 70)
        
        for test_name, status, message in results:
            icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "ERROR": "💥"}[status]
            print(f"{icon} {test_name}: {status} - {message}")
        
        print("=" * 70)
        
        # Fail if any critical failures
        failures = [r for r in results if r[1] == "FAIL"]
        assert len(failures) == 0, \
            f"Regression tests failed: {[r[0] for r in failures]}"


class TestCopyTrap:
    def test_copy_only_targets_own_toys(self, turn_planner):
        """Verify Copy cannot target opponent's toys."""
        setup, cards = create_game_with_cards(
            player1_hand=["Copy"],
            player1_in_play=["Umbruh"],
            player2_hand=[],
            player2_in_play=["Ballaber"],
            player1_charge=2,
            player2_charge=0,
            active_player="player1",
            turn_number=2,
        )
        
        plan = turn_planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None
        log_plan(plan, "COPY TRAP: Must Target Own Toy")
        
        copy_action = next((a for a in plan.action_sequence if a.card_name == "Copy"), None)
        if copy_action:
            # Verify target is NOT Ballaber
            assert "Ballaber" not in copy_action.target_names, \
                "AI tried to Copy opponent's Ballaber! Illegal!"
            assert "Umbruh" in copy_action.target_names, \
                "AI should copy its own Umbruh."

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
        """Verify AI predicts only 1 card broken in attacker-advantage tussle."""
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

    def test_suicide_attack_prevention(self, turn_planner):
        """
        Verify AI does NOT attack if it will die before dealing damage.
        Scenario: Paper Plane (2/2/1) vs Knight (4/4/3).
        Paper Plane SPD (2+1=3) < Knight SPD (4).
        Knight attacks first -> Paper Plane breaks.
        Paper Plane deals 0 damage.
        Result: 0 opponent cards slept, 1 own card slept.
        """
        setup, cards = create_game_with_cards(
            player1_hand=[],
            player1_in_play=["Paper Plane"], # 2/2/1
            player2_hand=[],
            player2_in_play=["Knight"], # 4/4/3
            player1_charge=2,
            player2_charge=0,
            active_player="player1",
            turn_number=2,
        )
        
        plan = turn_planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None
        log_plan(plan, "COMBAT MATH: Suicide Prevention")
        
        tussles = [a for a in plan.action_sequence if a.action_type == "tussle"]
        
        # Should NOT tussle because it's a suicide mission with 0 benefit
        assert len(tussles) == 0, \
            f"AI should NOT tussle! Paper Plane dies before dealing damage. Actions: {plan.action_sequence}"


class TestMultiToyDefense:
    def test_cannot_direct_attack_if_second_toy_remains(self, turn_planner):
        """
        Regression Test for Hallucination:
        Opponent has 2 toys (Umbruh, Archer).
        AI breaks Umbruh.
        AI MUST NOT direct attack afterwards, because Archer is still there.
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Surge", "Knight"],
            player1_in_play=[],
            player2_hand=["Knight", "Ka", "Archer", "Wizard"],
            player2_in_play=["Umbruh", "Archer"],  # Two toys!
            player1_charge=4,
            player2_charge=1,
            active_player="player1",
            turn_number=1,
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        # Check actions
        actions = plan.action_sequence
        
        # Should play Surge (optional but likely) and Knight
        # Should Tussle Umbruh (High threat)
        # Should NOT Direct Attack
        
        direct_attacks = [a for a in actions if a.action_type == "direct_attack"]
        
        assert len(direct_attacks) == 0, \
            f"AI performed Direct Attack despite Archer remaining in play! Actions: {actions}"

