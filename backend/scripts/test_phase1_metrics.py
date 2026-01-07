#!/usr/bin/env python3
"""
Test Phase 1 Quality Metrics with Real AI

This script verifies that quality metrics are being tracked correctly
during actual AI gameplay.
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
    get_session_metrics,
    get_session_summary,
    clear_session_metrics,
)

# Import test fixture
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
from conftest import create_game_with_cards


def main():
    # Check API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key or api_key.startswith("dummy"):
        print("❌ ERROR: Valid GOOGLE_API_KEY not found in .env")
        return 1
    
    print("=" * 70)
    print("PHASE 1 QUALITY METRICS TEST")
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
    
    clear_session_metrics()
    
    print("\n" + "=" * 70)
    print("TURN 1 (Player 1)")
    print("=" * 70)
    
    # Turn 1: Player 1 with Surge and Knight
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
    
    print("Setup: P1 has Surge, Knight in hand; 2 CC")
    print("Expected: Surge → Knight → direct_attack (3 CC used, 1 sleep)")
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
    
    # Check metrics were recorded
    metrics = get_session_metrics()
    if not metrics:
        print("❌ FAILED: No metrics recorded!")
        return 1
    
    print(f"\n📊 Metrics recorded: {len(metrics)} turn(s)")
    m1 = metrics[0]
    print(f"   Turn {m1.turn_number}:")
    print(f"   - CC: {m1.cc_spent}/{m1.cc_available} used")
    print(f"   - CC wasted: {m1.cc_wasted}")
    print(f"   - Cards slept: {m1.cards_slept}")
    print(f"   - Efficiency: {m1.efficiency_rating}")
    print(f"   - Meets expectations: {m1.meets_expectations()[0]}")
    
    # Verify Turn 1 quality
    if m1.cc_wasted > 1:
        print(f"⚠️  WARNING: Turn 1 wasted {m1.cc_wasted} CC (expected ≤1)")
    else:
        print(f"✅ Turn 1 CC efficiency: GOOD")
    
    print("\n" + "=" * 70)
    print("TURN 2 (Player 2)")
    print("=" * 70)
    
    # Turn 2: Player 2 with Knight in play
    setup2, cards2 = create_game_with_cards(
        player2_hand=["Umbruh", "Wake", "Archer"],
        player2_in_play=["Knight"],
        player1_hand=["Ka", "Archer", "Wizard", "Drop", "Surge"],
        player1_in_play=["Knight"],
        player2_cc=4,
        player1_cc=0,
        active_player="player2",
        turn_number=2,
    )
    
    print("Setup: P2 has Knight in play; 4 CC")
    print("Expected: tussle or play more toys (4-5 CC used, 1+ sleep)")
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
    
    # Check metrics
    metrics = get_session_metrics()
    if len(metrics) < 2:
        print("❌ FAILED: Turn 2 metrics not recorded!")
        return 1
    
    m2 = metrics[1]
    print(f"\n📊 Metrics recorded: {len(metrics)} turn(s)")
    print(f"   Turn {m2.turn_number}:")
    print(f"   - CC: {m2.cc_spent}/{m2.cc_available} used")
    print(f"   - CC wasted: {m2.cc_wasted}")
    print(f"   - Cards slept: {m2.cards_slept}")
    print(f"   - Efficiency: {m2.efficiency_rating}")
    print(f"   - Meets expectations: {m2.meets_expectations()[0]}")
    
    # Verify Turn 2 quality
    if m2.cc_wasted > 1:
        print(f"⚠️  WARNING: Turn 2 wasted {m2.cc_wasted} CC (expected ≤1)")
    else:
        print(f"✅ Turn 2 CC efficiency: GOOD")
    
    # Session summary
    print("\n" + "=" * 70)
    print("SESSION SUMMARY")
    print("=" * 70)
    
    summary = get_session_summary()
    print(f"Total turns: {summary['turns']}")
    print(f"Optimal turns: {summary['optimal_turns']} ({summary['optimal_pct']}%)")
    print(f"Wasteful turns: {summary['wasteful_turns']} ({summary['wasteful_pct']}%)")
    print(f"Avg CC wasted: {summary['avg_cc_wasted']} (target: {summary['target_avg_waste']})")
    print(f"Avg cards slept: {summary['avg_cards_slept']}")
    
    # Final assessment
    print("\n" + "=" * 70)
    total_waste = m1.cc_wasted + m2.cc_wasted
    total_sleeps = m1.cards_slept + m2.cards_slept
    
    if total_waste <= 2 and total_sleeps >= 2:
        print("✅ PHASE 1 TEST PASSED")
        print(f"   Total CC wasted: {total_waste}/2 ✓")
        print(f"   Total sleeps: {total_sleeps}/2 ✓")
        print("=" * 70)
        return 0
    else:
        print("⚠️  PHASE 1 TEST: Quality Below Target")
        print(f"   Total CC wasted: {total_waste}/2 {'✓' if total_waste <= 2 else '✗'}")
        print(f"   Total sleeps: {total_sleeps}/2 {'✓' if total_sleeps >= 2 else '✗'}")
        print("=" * 70)
        print("\nNote: Test completed but AI performance below optimal.")
        print("This is expected if prompts need tuning (see Phase 2+).")
        return 0  # Still pass - we're testing metrics, not AI quality


if __name__ == "__main__":
    sys.exit(main())
