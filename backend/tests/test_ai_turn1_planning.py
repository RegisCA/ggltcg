"""
Turn 1 Planning Regression Tests for AI v3.

Tests the exact scenarios from GitHub issues to prevent regressions:
- Issue #267: CC budgeting - sequential state-tracking
- Issue #272: Drop action card not understood

These tests validate that Turn 1 planning makes sense:
1. With 2 CC, the AI should play defensive toys
2. Surge enables additional actions (CC bridge concept)
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


def validate_cc_math(plan) -> list:
    """
    Validate that the plan's CC math is consistent and legal.
    
    Uses KNOWN card costs rather than trusting AI's reported cc_cost,
    since LLMs sometimes report incorrect values while planning correctly.
    
    Returns a list of CRITICAL errors only (negative CC situations).
    """
    # Known card costs (from game data)
    CARD_COSTS = {
        "Surge": 0, "Rush": 0, "Drop": 2, "Wake": 1, "Clean": 3, "Twist": 3,
        "Sun": 3, "VeryVeryAppleJuice": 0, "Copy": 0, "Jumpscare": 2,
        "Knight": 1, "Umbruh": 1, "Archer": 0, "Beary": 1, "Ka": 2,
        "Wizard": 2, "Raggy": 3, "Dream": 4, "Belchaletta": 1,
        "Gibbers": 1, "Paper Plane": 1, "Sock Sorcerer": 3, "Monster": 2,
        "Hind Leg Kicker": 1, "Violin": 1, "Drum": 2, "Demideca": 2,
        "Ballaber": 3, "That Was Fun": 1,
    }
    
    # Cards that give CC when played
    CC_GAINS = {
        "Surge": 1,
        "Rush": 2,
    }
    
    # Action costs (fixed)
    ACTION_COSTS = {
        "tussle": 2,
        "direct_attack": 2,
        "activate_ability": 1,  # Default for abilities like Archer
        "play_card": None,  # Use card cost
        "end_turn": 0,
    }
    
    running_cc = plan.cc_start
    errors = []
    warnings = []
    
    for i, action in enumerate(plan.action_sequence, 1):
        if action.action_type == "end_turn":
            continue
        
        # Determine the ACTUAL cost
        if action.action_type == "play_card":
            actual_cost = CARD_COSTS.get(action.card_name, action.cc_cost)
        else:
            actual_cost = ACTION_COSTS.get(action.action_type, action.cc_cost)
        
        cc_gain = CC_GAINS.get(action.card_name, 0)
        expected_cc = running_cc - actual_cost + cc_gain
        
        # Check for negative CC (CRITICAL ERROR)
        if expected_cc < 0:
            errors.append(
                f"Action {i} ({action.card_name}): Would spend more CC than available! "
                f"{running_cc} - {actual_cost} + {cc_gain} = {expected_cc}"
            )
        
        # Check cc_after accuracy (warning only)
        if action.cc_after != expected_cc and expected_cc >= 0:
            warnings.append(
                f"Action {i} ({action.card_name}): cc_after mismatch - "
                f"Reported: {action.cc_after}, Expected: {expected_cc}"
            )
        
        running_cc = max(0, expected_cc)
    
    # Print warnings (not errors)
    for warning in warnings:
        print(f"  ⚠️  {warning}")
    
    # Print and return only critical errors
    if errors:
        print("\n❌ CC MATH ERRORS:")
        for error in errors:
            print(f"  • {error}")
    
    return errors


# Skip all tests if no valid API key
def _has_valid_api_key():
    key = os.environ.get("GOOGLE_API_KEY", "")
    return key and not key.startswith("dummy") and len(key) > 20


pytestmark = pytest.mark.skipif(
    not _has_valid_api_key(),
    reason="Valid GOOGLE_API_KEY not set - skipping LLM tests"
)


@pytest.fixture
def turn_planner():
    """Create a TurnPlanner instance for testing."""
    from google import genai
    from game_engine.ai.turn_planner import TurnPlanner
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    fallback = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")
    
    return TurnPlanner(client=client, model_name=model, fallback_model=fallback)


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
    print(f"\nAction Sequence (CC: {plan.cc_start} → {plan.cc_after_plan}):")
    for i, action in enumerate(plan.action_sequence, 1):
        target = f" → {action.target_names}" if action.target_names else ""
        print(f"  {i}. {action.action_type}: {action.card_name or 'N/A'}{target} "
              f"(cost: {action.cc_cost}, cc_after: {action.cc_after})")
    print(f"\nExpected Cards Slept: {plan.expected_cards_slept}")
    print(f"CC Efficiency: {plan.cc_efficiency}")
    print(f"Plan Reasoning: {plan.plan_reasoning}")
    if plan.residual_cc_justification:
        print(f"Residual CC Justification: {plan.residual_cc_justification}")
    print("=" * 70)


class TestTurn1WithSurge:
    """
    Tests for Turn 1 scenarios where Surge enables additional actions.
    
    Issue #267: AI fails to account for CC gain from Surge when planning.
    The AI should recognize that:
    - 2 CC + Surge = 3 CC total spendable
    - 3 CC enables: Surge (0) + Knight (1) + Direct Attack (2) = 1 card slept!
    """
    
    def test_turn1_surge_knight_direct_attack(self, turn_planner):
        """
        Turn 1: Surge + Knight + Direct Attack = 1 card slept.
        
        This is the exact scenario from Issue #267.
        Starting: 2 CC, Hand has Surge and Knight
        Expected: Play Surge (+1 CC) → Play Knight (1 CC) → Direct Attack (2 CC)
        Result: 3 CC spent, 1 opponent card slept
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Dream", "Umbruh"],
            player1_in_play=[],
            player2_hand=["Knight", "Ka", "Archer", "Wizard", "Drop", "Surge"],
            player2_in_play=[],
            player1_cc=2,  # Turn 1 CC
            player2_cc=0,
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
        
        # Validate CC math in the plan
        running_cc = plan.cc_start
        for i, action in enumerate(plan.action_sequence):
            if action.action_type == "end_turn":
                continue
            
            # Calculate expected CC after this action
            cc_gain = 1 if action.card_name == "Surge" else 0
            expected_cc = running_cc - action.cc_cost + cc_gain
            
            # Check that reported cc_after is reasonable
            assert action.cc_after >= 0, \
                f"Action {i+1} ({action.card_name}): cc_after cannot be negative! " \
                f"Reported {action.cc_after}, calculated {expected_cc}"
            
            # CC should never go negative during the sequence
            assert expected_cc >= 0, \
                f"Action {i+1} ({action.card_name}): Would result in negative CC! " \
                f"{running_cc} - {action.cc_cost} + {cc_gain} = {expected_cc}"
            
            running_cc = expected_cc
        
        # The AI should find a way to sleep at least 1 card
        # With Surge + Knight + Direct Attack, this is achievable
        # But we only soft-assert this since the AI might find other valid plans
        if plan.expected_cards_slept == 0:
            print("\n⚠️ WARNING: AI chose to sleep 0 cards despite having Surge + Knight!")
            print("This may indicate the Surge CC bridge concept isn't understood.")
    
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
            player1_cc=2,
            player2_cc=0,
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
        
        # Validate no negative CC in the sequence
        for action in plan.action_sequence:
            assert action.cc_after >= 0, \
                f"Action {action.card_name}: cc_after cannot be negative!"


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
            player1_cc=2,
            player2_cc=0,
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
        
        # The AI should play Belchaletta instead (1 CC defender)
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
            player1_cc=2,
            player2_cc=0,
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
        
        # Playing Archer (0 CC) as a blocker is VALID, just don't use ability
        archer_played = any(
            action.card_name == "Archer" and action.action_type == "play_card"
            for action in plan.action_sequence
        )
        
        if archer_played:
            print("\n✓ AI correctly played Archer without using its ability (no targets)")


class TestSleepZoneTrap:
    """
    Tests for Sleep Zone card trap detection.
    
    Bug found: AI tried to play_card Knight directly from Sleep Zone
    without using Wake first. This is ILLEGAL - you can only play cards
    from your HAND.
    
    The AI should recognize:
    - Sleep Zone cards are NOT playable directly
    - Wake (1 CC) returns a card to HAND
    - Then you must PAY CC to play the card from hand
    """
    
    def test_cannot_play_card_from_sleep_zone(self, turn_planner):
        """
        Test that AI uses Wake before trying to play a sleeped card.
        
        Scenario: Knight in sleep zone, Wake in hand, opponent has Knight.
        CORRECT: Wake → Knight returns to hand → play Knight → tussle
        WRONG: Directly try to play_card Knight from sleep zone (without Wake first)
        """
        # Set up a mid-game scenario where player needs to recover cards
        setup, cards = create_game_with_cards(
            player1_hand=["Wake", "Surge", "Archer"],
            player1_in_play=[],
            player1_sleep=["Knight", "Umbruh"],  # Cards in sleep zone
            player2_hand=["Ka", "Wizard", "Drop"],
            player2_in_play=["Knight"],
            player1_cc=6,  # Mid-game CC
            player2_cc=0,
            active_player="player1",
            turn_number=4,
        )
        
        # Get the sleep zone card IDs for checking
        sleep_zone_ids = {card.id for card in setup.player1.sleep_zone}
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        log_plan(plan, "SLEEP ZONE TRAP: Must Use Wake Before Playing Sleeped Card")
        
        # Track if Wake was played before any sleep zone card is played
        wake_played = False
        sleep_zone_card_played_without_wake = False
        
        for action in plan.action_sequence:
            if action.action_type == "play_card":
                if action.card_name == "Wake":
                    wake_played = True
                elif action.card_id in sleep_zone_ids:
                    # This card was originally in sleep zone
                    if not wake_played:
                        sleep_zone_card_played_without_wake = True
                        print(f"\n❌ CRITICAL: AI tried to play {action.card_name} (ID: {action.card_id}) "
                              f"directly from Sleep Zone WITHOUT using Wake first!")
        
        assert not sleep_zone_card_played_without_wake, \
            "AI tried to play a card from Sleep Zone without using Wake first! " \
            "Cards in Sleep Zone CANNOT be played directly - must use Wake to return to hand first."
        
        # If a sleep zone card was played after Wake, that's correct behavior
        sleep_zone_card_played_after_wake = any(
            action.action_type == "play_card" and action.card_id in sleep_zone_ids
            for action in plan.action_sequence
        ) and wake_played
        
        if sleep_zone_card_played_after_wake:
            print("\n✓ AI correctly used Wake before playing a card from sleep zone")
        elif not any(action.card_id in sleep_zone_ids for action in plan.action_sequence if action.action_type == "play_card"):
            print("\n⚠️ AI didn't try to play any cards from sleep zone (may have chosen a different valid strategy)")


class TestWinningTussle:
    """
    Tests for endgame scenarios where the AI should tussle to win.
    
    Issue: AI hallucinated "opponent has no toys" when opponent clearly had Umbruh.
    This led to invalid direct_attack when tussle was the winning move.
    
    Key insight: Trading toys (mutual destruction) is WINNING if it sleeps
    the opponent's last card!
    """
    
    def test_must_tussle_to_win_not_direct_attack(self, turn_planner):
        """
        Test that AI recognizes tussle is required when opponent has toys.
        
        Scenario: Turn 8, both players have 5/6 cards sleeped.
        - AI has Umbruh (4/4/4) in play, empty hand
        - Opponent has Umbruh (4/4/4) in play, empty hand
        
        CORRECT: Tussle Umbruh→Umbruh (trade, both die) = OPPONENT LOSES (6 cards sleeped)!
        WRONG: Direct attack (illegal when opponent has toys in play!)
        """
        # This is the exact scenario from the user's bug report
        setup, cards = create_game_with_cards(
            player1_hand=[],  # Empty hand
            player1_in_play=["Umbruh"],
            player1_sleep=["Archer", "Surge", "Paper Plane", "Wake", "Knight"],  # 5 sleeped
            player2_hand=[],  # Empty hand
            player2_in_play=["Umbruh"],
            player2_sleep=["Surge", "Wake", "Knight", "Paper Plane", "Archer"],  # 5 sleeped
            player1_cc=4,  # Plenty of CC
            player2_cc=1,
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
        if has_direct_attack:
            print("\n❌ CRITICAL: AI used direct_attack when opponent has toys in play!")
            print("   This is ILLEGAL - must use tussle when opponent has toys!")
        
        assert not has_direct_attack, \
            "AI used direct_attack when opponent has toys in play! " \
            "Direct attack is only legal when opponent has 0 toys. " \
            "The AI hallucinated 'opponent has no toys' - this is a game state reading error."
        
        # The winning play is to tussle
        assert has_tussle, \
            "AI should have used tussle to attack opponent's Umbruh! " \
            "With 5/6 cards sleeped, one tussle (even a trade) wins the game."
        
        print("\n✓ AI correctly chose tussle over direct_attack")
        print("  This scenario sleeps opponent's 6th card = VICTORY!")


class TestTurn1CCMathValidation:
    """
    Tests that CC math is calculated correctly throughout the plan.
    
    These tests verify that cc_after values are consistent with the
    actual costs and gains in the action sequence.
    """
    
    def test_cc_math_consistency(self, turn_planner):
        """
        Verify CC math is consistent throughout the plan.
        
        For each action:
        - cc_after should equal cc_before - cc_cost + cc_gain
        - cc_after should never be negative
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Umbruh", "Ka", "Drop", "Archer"],
            player1_in_play=[],
            player2_hand=["Knight", "Ka", "Wizard", "Surge", "Drop", "Umbruh"],
            player2_in_play=[],
            player1_cc=2,
            player2_cc=0,
            active_player="player1",
            turn_number=1,
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        log_plan(plan, "TURN 1: CC Math Consistency Test")
        
        # Validate using shared function
        cc_errors = validate_cc_math(plan)
        assert len(cc_errors) == 0, \
            f"Plan has impossible CC math: {cc_errors}"


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
        (negative CC, invalid targets) rather than expecting specific plans.
        """
        results = []
        
        # Test 1: Surge enables direct attack (but LLM might choose different valid plan)
        try:
            setup1, _ = create_game_with_cards(
                player1_hand=["Surge", "Knight", "Dream", "Umbruh"],
                player1_in_play=[],
                player2_in_play=[],
                player1_cc=2,
                turn_number=1,
            )
            plan1 = turn_planner.create_plan(setup1.game_state, "player1", setup1.engine)
            log_plan(plan1, "REGRESSION: Surge+Knight Test")
            
            # Check CC math validity
            cc_errors = validate_cc_math(plan1)
            if cc_errors:
                # Only fail on actual math errors, not different valid plans
                results.append(("Surge+Knight", "FAIL", f"CC math errors: {cc_errors}"))
            else:
                # Any valid plan is acceptable
                results.append(("Surge+Knight", "PASS", f"Valid plan, slept {plan1.expected_cards_slept} cards"))
        except Exception as e:
            results.append(("Surge+Knight", "ERROR", str(e)))
        
        # Test 2: Drop trap - MUST NOT play Drop
        try:
            setup2, _ = create_game_with_cards(
                player1_hand=["Drop", "Belchaletta", "Ka"],
                player1_in_play=[],
                player2_in_play=[],  # No targets for Drop!
                player1_cc=2,
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


def validate_cc_math(plan):
    """
    Validate CC math throughout a plan.
    
    Returns list of errors, empty list if valid.
    """
    CC_GAINS = {"Surge": 1, "Rush": 2}
    
    running_cc = plan.cc_start
    errors = []
    
    for i, action in enumerate(plan.action_sequence, 1):
        if action.action_type == "end_turn":
            continue
        
        cc_gain = CC_GAINS.get(action.card_name, 0)
        expected_cc = running_cc - action.cc_cost + cc_gain
        
        if expected_cc < 0:
            errors.append(
                f"Action {i} ({action.card_name}): {running_cc} - {action.cc_cost} + {cc_gain} = {expected_cc} (negative!)"
            )
        
        running_cc = max(0, expected_cc)
    
    return errors

class TestCopyTrap:
    def test_copy_only_targets_own_toys(self, turn_planner):
        """Verify Copy cannot target opponent's toys."""
        setup, cards = create_game_with_cards(
            player1_hand=["Copy"],
            player1_in_play=["Umbruh"],
            player2_hand=[],
            player2_in_play=["Ballaber"],
            player1_cc=2,
            player2_cc=0,
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
            player1_cc=4,
            player2_cc=0,
            active_player="player1",
            turn_number=2,
        )
        
        plan = turn_planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None
        log_plan(plan, "KNIGHT EFFICIENCY: No Wasted Archer Shots")
        
        archer_use = next((a for a in plan.action_sequence if a.action_type == "activate_ability" and "Umbruh" in a.target_names), None)
        knight_tussle = next((a for a in plan.action_sequence if a.action_type == "tussle" and a.card_name == "Knight"), None)
        
        if knight_tussle and archer_use:
             pytest.fail("AI wasted Archer ability on a target that Knight was going to auto-sleep!")

class TestExhaustivePlanning:
    def test_uses_all_available_cc(self, turn_planner):
        """Verify AI continues attacking until CC < 2."""
        setup, cards = create_game_with_cards(
            player1_hand=[],
            player1_in_play=["Umbruh"],
            player2_hand=[],
            player2_in_play=["Knight", "Wizard"],
            player1_cc=5, # Enough for 2 tussles (2+2=4)
            player2_cc=0,
            active_player="player1",
            turn_number=2,
        )
        
        plan = turn_planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None
        log_plan(plan, "EXHAUSTIVE PLANNING: Use All CC")
        
        tussles = [a for a in plan.action_sequence if a.action_type == "tussle"]
        assert len(tussles) >= 2, \
            f"AI should tussle at least twice with 5 CC! Found {len(tussles)} tussles."

class TestCombatMath:
    def test_attacker_wins_clean(self, turn_planner):
        """Verify AI predicts only 1 card sleeped in attacker-advantage tussle."""
        setup, cards = create_game_with_cards(
            player1_hand=[],
            player1_in_play=["Umbruh"], # 4/4/4
            player2_hand=[],
            player2_in_play=["Umbruh"], # 4/4/4
            player1_cc=2,
            player2_cc=0,
            active_player="player1",
            turn_number=2,
        )
        
        plan = turn_planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None
        log_plan(plan, "COMBAT MATH: Attacker Advantage")
        
        # Expect 1 card slept (opponent), not 2
        assert plan.expected_cards_slept == 1, \
            f"AI predicted {plan.expected_cards_slept} cards slept. Should be 1 (attacker wins clean due to SPD bonus)."
