#!/usr/bin/env python3
"""
Quick Manual Verification Script for Standard Scenario Test.

This script runs the same Turn 1 + Turn 2 test as test_ai_standard_scenario.py
but provides more verbose output for manual verification and debugging.

Usage:
    python backend/scripts/run_standard_scenario.py

Purpose:
    - Quick smoke test without pytest overhead
    - Detailed logging for debugging prompt issues
    - Verify metrics are being tracked correctly
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from google import genai
from game_engine.ai.turn_planner import TurnPlanner
from game_engine.ai.quality_metrics import (
    TurnMetrics,
    clear_session_metrics,
    get_session_summary,
)

# Import test fixture
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
from conftest import create_game_with_cards


def log_plan_details(plan, title: str):
    """Log detailed plan information."""
    print("\n" + "=" * 70)
    print(f"📋 {title}")
    print("=" * 70)
    print(f"Selected Strategy: {plan.selected_strategy}")
    print(f"\nAction Sequence (CC: {plan.cc_start} → {plan.cc_after_plan}):")
    for i, action in enumerate(plan.action_sequence, 1):
        target = f" → {action.target_names}" if action.target_names else ""
        print(f"  {i}. {action.action_type}: {action.card_name or 'N/A'}{target} "
              f"(cost: {action.cc_cost}, cc_after: {action.cc_after})")
    print(f"\nExpected Cards Slept: {plan.expected_cards_slept}")
    print(f"CC Efficiency: {plan.cc_efficiency}")
    print("=" * 70)


def log_metrics(metrics: TurnMetrics, title: str):
    """Log turn metrics."""
    print("\n" + "=" * 70)
    print(f"📊 {title}")
    print("=" * 70)
    print(f"Turn {metrics.turn_number} ({metrics.player_id}):")
    print(f"  CC Budget: {metrics.cc_start} + {metrics.cc_gained} gained = {metrics.cc_available} available")
    print(f"  CC Used: {metrics.cc_spent} ({metrics.efficiency_pct:.1f}%)")
    print(f"  CC Wasted: {metrics.cc_wasted} (target: ≤1)")
    print(f"  Cards Slept: {metrics.cards_slept}")
    print(f"  Toys Played: {metrics.toys_played}")
    print(f"  Actions Taken: {metrics.actions_taken}")
    print(f"  Efficiency Rating: {metrics.efficiency_rating.upper()}")
    passed, reason = metrics.meets_expectations()
    print(f"  Assessment: {'✅' if passed else '⚠️'} {reason}")
    print("=" * 70)


def main():
    # Check API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key or api_key.startswith("dummy"):
        print("❌ ERROR: Valid GOOGLE_API_KEY not found in .env")
        print("   Set GOOGLE_API_KEY in backend/.env to run this test")
        return 1
    
    print("=" * 70)
    print("STANDARD SCENARIO TEST - PHASE 2")
    print("=" * 70)
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Setup AI
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp")
    print(f"✅ Using model: {model}")
    
    # Force AI V4
    planner = TurnPlanner(
        client=client,
        model_name=model,
        fallback_model=model,
        ai_version=4
    )
    print("✅ TurnPlanner initialized (AI V4)")
    
    clear_session_metrics()
    
    # ===========================
    # TURN 1: Player 1 Opening
    # ===========================
    print("\n" + "=" * 70)
    print("TURN 1 (PLAYER 1): Surge + Knight Opening")
    print("=" * 70)
    
    setup1, cards1 = create_game_with_cards(
        player1_hand=["Surge", "Knight", "Umbruh", "Wake"],
        player1_in_play=[],
        player2_hand=["Knight", "Ka", "Archer", "Wizard", "Drop", "Surge"],
        player2_in_play=[],
        player1_cc=2,  # Turn 1 CC
        player2_cc=0,
        active_player="player1",
        turn_number=1,
    )
    
    print("Setup: P1 has Surge, Knight in hand; 2 CC")
    print("Expected: Surge → Knight → direct_attack (3 CC used, 1 sleep, 0 wasted)")
    print("\nGenerating plan...")
    
    plan1 = planner.create_plan(
        setup1.game_state,
        "player1",
        setup1.engine
    )
    
    if not plan1:
        print("❌ FAILED: No plan generated for Turn 1")
        return 1
    
    print(f"✅ Plan generated with {len(plan1.action_sequence)} actions")
    log_plan_details(plan1, "TURN 1 PLAN")
    
    # Extract and log metrics
    metrics1 = TurnMetrics.from_plan(plan1, setup1.game_state, "player1")
    log_metrics(metrics1, "TURN 1 METRICS")
    
    # Validate Turn 1
    turn1_pass = metrics1.cc_wasted <= 1 and metrics1.cards_slept >= 1
    if turn1_pass:
        print("\n✅ TURN 1 PASSED: Meets Phase 2 acceptance criteria")
    else:
        print("\n⚠️  TURN 1: Below target performance")
        if metrics1.cc_wasted > 1:
            print(f"   - CC waste: {metrics1.cc_wasted} (expected ≤1)")
        if metrics1.cards_slept < 1:
            print(f"   - Cards slept: {metrics1.cards_slept} (expected ≥1)")
    
    # ===========================
    # TURN 2: Player 2 Response
    # ===========================
    print("\n" + "=" * 70)
    print("TURN 2 (PLAYER 2): Aggressive Response")
    print("=" * 70)
    
    setup2, cards2 = create_game_with_cards(
        player2_hand=["Umbruh", "Wake", "Archer"],
        player2_in_play=["Knight"],
        player1_hand=["Ka", "Archer", "Wizard"],
        player1_in_play=["Knight"],
        player2_cc=4,  # Turn 2 CC (P2's first turn)
        player1_cc=0,
        active_player="player2",
        turn_number=2,
    )
    
    print("Setup: P2 has Knight in play; 4 CC")
    print("Expected: Tussle or play toys (4-5 CC used, 1+ sleep, 0-1 wasted)")
    print("\nGenerating plan...")
    
    plan2 = planner.create_plan(
        setup2.game_state,
        "player2",
        setup2.engine
    )
    
    if not plan2:
        print("❌ FAILED: No plan generated for Turn 2")
        return 1
    
    print(f"✅ Plan generated with {len(plan2.action_sequence)} actions")
    log_plan_details(plan2, "TURN 2 PLAN")
    
    # Extract and log metrics
    metrics2 = TurnMetrics.from_plan(plan2, setup2.game_state, "player2")
    log_metrics(metrics2, "TURN 2 METRICS")
    
    # Validate Turn 2
    turn2_pass = metrics2.cc_wasted <= 1 and metrics2.cards_slept >= 1
    if turn2_pass:
        print("\n✅ TURN 2 PASSED: Meets Phase 2 acceptance criteria")
    else:
        print("\n⚠️  TURN 2: Below target performance")
        if metrics2.cc_wasted > 1:
            print(f"   - CC waste: {metrics2.cc_wasted} (expected ≤1)")
        if metrics2.cards_slept < 1:
            print(f"   - Cards slept: {metrics2.cards_slept} (expected ≥1)")
    
    # ===========================
    # FULL SCENARIO SUMMARY
    # ===========================
    print("\n" + "=" * 70)
    print("📈 FULL SCENARIO SUMMARY")
    print("=" * 70)
    
    total_cc_wasted = metrics1.cc_wasted + metrics2.cc_wasted
    total_sleeps = metrics1.cards_slept + metrics2.cards_slept
    total_cc_used = metrics1.cc_spent + metrics2.cc_spent
    total_cc_available = metrics1.cc_available + metrics2.cc_available
    
    print(f"Total CC Available: {total_cc_available}")
    print(f"Total CC Used: {total_cc_used} ({total_cc_used/total_cc_available*100:.1f}%)")
    print(f"Total CC Wasted: {total_cc_wasted} (target: ≤2)")
    print(f"Total Cards Slept: {total_sleeps} (target: ≥2)")
    print(f"Turn 1 Efficiency: {metrics1.efficiency_rating}")
    print(f"Turn 2 Efficiency: {metrics2.efficiency_rating}")
    
    # Session summary
    summary = get_session_summary()
    print(f"\nSession Stats:")
    print(f"  Optimal turns: {summary['optimal_turns']}/{summary['turns']} ({summary['optimal_pct']}%)")
    print(f"  Wasteful turns: {summary['wasteful_turns']}/{summary['turns']} ({summary['wasteful_pct']}%)")
    print(f"  Avg CC wasted: {summary['avg_cc_wasted']} (target: {summary['target_avg_waste']})")
    
    # Final assessment
    print("\n" + "=" * 70)
    scenario_pass = total_cc_wasted <= 2 and total_sleeps >= 2
    
    if scenario_pass:
        print("✅ FULL SCENARIO PASSED")
        print("   AI V4 meets Phase 2 quality gates")
        print(f"   - Total CC wasted: {total_cc_wasted}/2 ✓")
        print(f"   - Total sleeps: {total_sleeps}/2 ✓")
        print("=" * 70)
        return 0
    else:
        print("⚠️  FULL SCENARIO: Performance Below Target")
        print(f"   - Total CC wasted: {total_cc_wasted}/2 {'✓' if total_cc_wasted <= 2 else '✗'}")
        print(f"   - Total sleeps: {total_sleeps}/2 {'✓' if total_sleeps >= 2 else '✗'}")
        print("=" * 70)
        print("\nNote: Test completed but AI performance below optimal.")
        print("This may indicate prompt issues (see Phase 3+).")
        print("The test infrastructure is working correctly.")
        return 0  # Still pass - we're testing infrastructure, not AI quality


if __name__ == "__main__":
    sys.exit(main())
