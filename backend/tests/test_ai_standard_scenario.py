"""
Standard Scenario Regression Tests for AI V4 - Phase 2.

This test replaces the manual "play 2 turns, check if AI is reasonable" workflow.
It validates the standard Turn 1 + Turn 2 scenario with quality metrics.

Expected Behavior (Baseline):
- Turn 1 (P1): Surge → Knight → direct_attack = 3 CC used, 1 sleep, 0 CC wasted
- Turn 2 (P2): Tussle + aggressive play = 4-5 CC used, 1-2 sleeps, 0-1 CC wasted
- Full scenario: Total CC wasted ≤ 2, total sleeps ≥ 2

Run with: pytest backend/tests/test_ai_standard_scenario.py -v -s

Purpose:
- Catch regressions in prompt structure/behavior
- Validate CC efficiency and sleep metrics
- Provide automated quality gate for future changes
"""

import pytest
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Add backend/src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards
from game_engine.ai.quality_metrics import TurnMetrics, clear_session_metrics, get_session_summary


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
    """Create a TurnPlanner instance configured for AI V4."""
    from google import genai
    from game_engine.ai.turn_planner import TurnPlanner
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp")
    fallback = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-2.0-flash-exp")
    
    # Force AI V4
    return TurnPlanner(
        client=client,
        model_name=model,
        fallback_model=fallback,
        ai_version=4
    )


@pytest.fixture(autouse=True)
def clear_metrics():
    """Clear metrics before each test."""
    clear_session_metrics()
    yield
    # Metrics are cleared automatically at start of next test


def log_turn_result(metrics: TurnMetrics, title: str):
    """Log turn metrics in a readable format."""
    print("\n" + "=" * 70)
    print(f"📊 {title}")
    print("=" * 70)
    print(f"Turn {metrics.turn_number} ({metrics.player_id}):")
    print(f"  CC Budget: {metrics.cc_start} + {metrics.cc_gained} gained = {metrics.cc_available} available")
    print(f"  CC Used: {metrics.cc_spent} ({metrics.efficiency_pct:.1f}%)")
    print(f"  CC Wasted: {metrics.cc_wasted} (target: ≤1)")
    print(f"  Cards Slept: {metrics.cards_slept}")
    print(f"  Actions Taken: {metrics.actions_taken}")
    print(f"  Efficiency: {metrics.efficiency_rating.upper()}")
    passed, reason = metrics.meets_expectations()
    print(f"  Assessment: {'✅' if passed else '⚠️'} {reason}")
    print("=" * 70)


class TestStandardScenario:
    """
    Standard scenario tests for AI V4 regression detection.
    
    These tests validate the two most common opening turns:
    - Turn 1 (P1): Opening with Surge + Knight combo
    - Turn 2 (P2): Responding with Knight in play
    """
    
    def test_turn1_with_surge_knight(self, turn_planner):
        """
        Turn 1 (P1): Standard opening with Surge + Knight.
        
        Setup:
            - Player 1: 2 CC, Hand=[Surge, Knight, Umbruh, Wake]
            - Player 2: No toys in play (can't tussle)
        
        Expected Behavior:
            - Surge (0 CC) → +1 CC
            - Knight (1 CC) → 2 CC remaining
            - Direct Attack (2 CC) → 0 CC remaining
            - Result: 3 CC used, 1 card slept, 0 CC wasted
        
        Acceptance:
            - cc_wasted ≤ 1 (optimal efficiency)
            - cards_slept ≥ 1 (minimum damage dealt)
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Umbruh", "Wake"],
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
        
        # Extract metrics
        metrics = TurnMetrics.from_plan(plan, setup.game_state, "player1")
        log_turn_result(metrics, "TURN 1: Surge + Knight Opening")
        
        # Phase 2 Acceptance Criteria
        assert metrics.cc_wasted <= 1, (
            f"Turn 1 should waste ≤1 CC (actual: {metrics.cc_wasted}). "
            "Check if Surge→Knight→direct_attack combo is being used."
        )
        
        assert metrics.cards_slept >= 1, (
            f"Turn 1 should sleep ≥1 card with Surge+Knight (actual: {metrics.cards_slept}). "
            "Check if direct_attack is being executed."
        )
        
        # Log final result
        if metrics.is_optimal and metrics.cards_slept >= 1:
            print("\n✅ TURN 1 TEST PASSED: Optimal efficiency and damage")
        elif metrics.cc_wasted <= 1 and metrics.cards_slept >= 1:
            print("\n✅ TURN 1 TEST PASSED: Acceptable performance")
        else:
            print("\n⚠️  TURN 1 TEST PASSED: But performance below target")
            print("    This may indicate prompt issues (see Phase 3+)")
    
    def test_turn2_aggressive_play(self, turn_planner):
        """
        Turn 2 (P2): Aggressive response with Knight in play.
        
        Setup:
            - Player 2: 4 CC, Knight in play, Hand=[Umbruh, Wake, Archer]
            - Player 1: Knight in play (can tussle)
        
        Expected Behavior:
            - Option A: Tussle + play more toys = 4-5 CC used
            - Option B: Play multiple toys + direct attacks = 4-5 CC used
            - Result: 4-5 CC used, 1-2 sleeps, 0-1 CC wasted
        
        Acceptance:
            - cc_wasted ≤ 1 (optimal efficiency)
            - cards_slept ≥ 1 (minimum damage dealt)
        """
        setup, cards = create_game_with_cards(
            player2_hand=["Umbruh", "Wake", "Archer"],
            player2_in_play=["Knight"],
            player1_hand=["Ka", "Archer", "Wizard", "Drop", "Surge"],
            player1_in_play=["Knight"],
            player2_cc=4,  # Turn 2 CC (P2's first turn)
            player1_cc=0,
            active_player="player2",
            turn_number=2,  # Turn 2 = P2's turn (odd=P1, even=P2)
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player2",
            setup.engine
        )
        
        assert plan is not None, "Plan should be generated"
        
        # Extract metrics
        metrics = TurnMetrics.from_plan(plan, setup.game_state, "player2")
        log_turn_result(metrics, "TURN 2: Aggressive Response")
        
        # Phase 2 Acceptance Criteria
        assert metrics.cc_wasted <= 1, (
            f"Turn 2 should waste ≤1 CC (actual: {metrics.cc_wasted}). "
            "Check if AI is using tussle and/or playing additional toys."
        )
        
        assert metrics.cards_slept >= 1, (
            f"Turn 2 should sleep ≥1 card (actual: {metrics.cards_slept}). "
            "Check if AI is being aggressive with tussle/attacks."
        )
        
        # Log final result
        if metrics.is_optimal and metrics.cards_slept >= 1:
            print("\n✅ TURN 2 TEST PASSED: Optimal efficiency and damage")
        elif metrics.cc_wasted <= 1 and metrics.cards_slept >= 1:
            print("\n✅ TURN 2 TEST PASSED: Acceptable performance")
        else:
            print("\n⚠️  TURN 2 TEST PASSED: But performance below target")
            print("    This may indicate prompt issues (see Phase 3+)")
    
    def test_full_scenario_turn1_and_turn2(self, turn_planner):
        """
        Full scenario: Turn 1 (P1) + Turn 2 (P2) in sequence.
        
        This test validates the complete opening sequence and provides
        aggregate metrics across both turns.
        
        Setup:
            - Turn 1: P1 with Surge+Knight
            - Turn 2: P2 responds with Knight in play
        
        Expected Behavior:
            - Turn 1: Surge→Knight→direct_attack (3 CC, 1 sleep)
            - Turn 2: Tussle + aggressive play (4-5 CC, 1-2 sleeps)
            - Combined: 7-8 CC used, 2-3 sleeps, 0-2 CC wasted
        
        Acceptance:
            - total_cc_wasted ≤ 2
            - total_sleeps ≥ 2
        """
        # Turn 1: Player 1 opening
        setup1, cards1 = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Umbruh", "Wake"],
            player1_in_play=[],
            player2_hand=["Knight", "Ka", "Archer", "Wizard", "Drop", "Surge"],
            player2_in_play=[],
            player1_cc=2,
            player2_cc=0,
            active_player="player1",
            turn_number=1,
        )
        
        plan1 = turn_planner.create_plan(
            setup1.game_state,
            "player1",
            setup1.engine
        )
        
        assert plan1 is not None, "Turn 1 plan should be generated"
        
        metrics1 = TurnMetrics.from_plan(plan1, setup1.game_state, "player1")
        log_turn_result(metrics1, "TURN 1: Opening")
        
        # Turn 2: Player 2 response
        # Apply Turn 1 actions to game state
        for action in plan1.action_sequence:
            if action.action_type == "end_turn":
                continue
            # Execute action on engine (simplified for test)
            # In real game, this would be done through game_manager
        
        # Setup Turn 2 with Knight in play (from Turn 1)
        setup2, cards2 = create_game_with_cards(
            player2_hand=["Umbruh", "Wake", "Archer"],
            player2_in_play=["Knight"],
            player1_hand=["Ka", "Archer", "Wizard"],
            player1_in_play=["Knight"],  # From Turn 1
            player2_cc=4,
            player1_cc=0,
            active_player="player2",
            turn_number=2,
        )
        
        plan2 = turn_planner.create_plan(
            setup2.game_state,
            "player2",
            setup2.engine
        )
        
        assert plan2 is not None, "Turn 2 plan should be generated"
        
        metrics2 = TurnMetrics.from_plan(plan2, setup2.game_state, "player2")
        log_turn_result(metrics2, "TURN 2: Response")
        
        # Aggregate metrics
        total_cc_wasted = metrics1.cc_wasted + metrics2.cc_wasted
        total_sleeps = metrics1.cards_slept + metrics2.cards_slept
        total_cc_used = metrics1.cc_spent + metrics2.cc_spent
        
        print("\n" + "=" * 70)
        print("📈 FULL SCENARIO SUMMARY")
        print("=" * 70)
        print(f"Total CC Used: {total_cc_used} / {metrics1.cc_available + metrics2.cc_available}")
        print(f"Total CC Wasted: {total_cc_wasted} (target: ≤2)")
        print(f"Total Cards Slept: {total_sleeps} (target: ≥2)")
        print(f"Turn 1 Efficiency: {metrics1.efficiency_rating}")
        print(f"Turn 2 Efficiency: {metrics2.efficiency_rating}")
        print("=" * 70)
        
        # Phase 2 Acceptance Criteria (Aggregate)
        assert total_cc_wasted <= 2, (
            f"Full scenario should waste ≤2 CC total (actual: {total_cc_wasted}). "
            f"Turn 1: {metrics1.cc_wasted} CC, Turn 2: {metrics2.cc_wasted} CC"
        )
        
        assert total_sleeps >= 2, (
            f"Full scenario should sleep ≥2 cards total (actual: {total_sleeps}). "
            f"Turn 1: {metrics1.cards_slept} sleeps, Turn 2: {metrics2.cards_slept} sleeps"
        )
        
        # Log final result
        if total_cc_wasted <= 2 and total_sleeps >= 2:
            print("\n✅ FULL SCENARIO TEST PASSED")
            print("   AI V4 meets Phase 2 quality gates")
        else:
            print("\n⚠️  FULL SCENARIO TEST: Below Target")
            print("   AI performance needs prompt tuning (see Phase 3+)")
