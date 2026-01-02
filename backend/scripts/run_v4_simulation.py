#!/usr/bin/env python3
"""
Run V4 AI simulation tests.

This script runs a configurable number of AI vs AI games using V4 planning
(dual-request architecture) and reports comprehensive metrics.

Usage:
    # Quick test (2 games)
    python scripts/run_v4_simulation.py --quick
    
    # Standard test (10 games)
    python scripts/run_v4_simulation.py
    
    # Custom test (20 games)
    python scripts/run_v4_simulation.py --games 20
    
    # Compare V4 vs V3 (runs both)
    python scripts/run_v4_simulation.py --compare

Environment:
    PLANNING_VERSION: Set automatically by this script
    GOOGLE_API_KEY: Required for Gemini API calls
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulation.runner import SimulationRunner
from simulation.config import DeckConfig, GameOutcome
from simulation.deck_loader import load_simulation_decks_dict
from game_engine.ai.turn_planner import TurnPlanner


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SimulationSummary:
    """Summary of a simulation run."""
    planning_version: str  # Actually AI version now (3 or 4)
    total_games: int
    completed_games: int
    player1_wins: int
    player2_wins: int
    draws: int
    errors: int
    avg_turns: float
    avg_duration_ms: float
    total_v2_fallbacks: int
    total_illegal_actions: int
    v4_metrics: dict
    duration_seconds: float


def run_simulation(
    num_games: int,
    ai_version: str,
    player1_model: str = "gemini-2.5-flash-lite",
    player2_model: str = "gemini-2.5-flash-lite",
) -> SimulationSummary:
    """
    Run a simulation with specified AI version.
    
    Args:
        num_games: Number of games to run
        ai_version: "3" or "4"
        player1_model: Model for player 1
        player2_model: Model for player 2
        
    Returns:
        SimulationSummary with aggregate results
    """
    # Set AI version environment variable
    os.environ["AI_VERSION"] = ai_version
    logger.info(f"=== Starting AI V{ai_version} Simulation ({num_games} games) ===")
    
    # Load decks
    decks = load_simulation_decks_dict()
    if not decks:
        raise ValueError("No decks found. Check data/simulation_decks.csv")
    
    # Use first two available decks
    deck_names = list(decks.keys())[:2]
    deck1 = decks[deck_names[0]]
    deck2 = decks[deck_names[1]]
    logger.info(f"Decks: {deck1.name} vs {deck2.name}")
    
    # Initialize runner
    runner = SimulationRunner(
        player1_model=player1_model,
        player2_model=player2_model,
        max_turns=40,
    )
    
    # Track results
    results = []
    start_time = time.time()
    
    # Reset V4 metrics before simulation
    TurnPlanner.reset_v4_metrics()
    
    for game_num in range(1, num_games + 1):
        logger.info(f"\n--- Game {game_num}/{num_games} ---")
        try:
            result = runner.run_game(deck1, deck2, game_number=game_num)
            results.append(result)
            
            outcome_str = result.outcome.value
            logger.info(
                f"Game {game_num}: {outcome_str} in {result.turn_count} turns, "
                f"V2 fallbacks: {result.v2_fallback_count}"
            )
        except Exception as e:
            logger.error(f"Game {game_num} failed with error: {e}")
            results.append(None)
    
    elapsed = time.time() - start_time
    
    # Aggregate results
    completed = [r for r in results if r is not None]
    
    summary = SimulationSummary(
        planning_version=ai_version,
        total_games=num_games,
        completed_games=len(completed),
        player1_wins=sum(1 for r in completed if r.outcome == GameOutcome.PLAYER1_WIN),
        player2_wins=sum(1 for r in completed if r.outcome == GameOutcome.PLAYER2_WIN),
        draws=sum(1 for r in completed if r.outcome == GameOutcome.DRAW),
        errors=num_games - len(completed),
        avg_turns=sum(r.turn_count for r in completed) / len(completed) if completed else 0,
        avg_duration_ms=sum(r.duration_ms for r in completed) / len(completed) if completed else 0,
        total_v2_fallbacks=sum(r.v2_fallback_count for r in completed),
        total_illegal_actions=sum(r.illegal_action_count for r in completed),
        v4_metrics=TurnPlanner.get_v4_metrics() if ai_version == "4" else {},
        duration_seconds=elapsed,
    )
    
    return summary


def print_summary(summary: SimulationSummary):
    """Print a formatted summary."""
    print("\n" + "=" * 60)
    print(f"SIMULATION SUMMARY - AI V{summary.planning_version}")
    print("=" * 60)
    print(f"Games: {summary.completed_games}/{summary.total_games} completed")
    print(f"Duration: {summary.duration_seconds:.1f}s ({summary.avg_duration_ms:.0f}ms/game avg)")
    print(f"Average turns: {summary.avg_turns:.1f}")
    print()
    print("Results:")
    print(f"  Player 1 wins: {summary.player1_wins}")
    print(f"  Player 2 wins: {summary.player2_wins}")
    print(f"  Draws: {summary.draws}")
    print(f"  Errors: {summary.errors}")
    print()
    
    if summary.planning_version == "4":
        print("V4 Metrics:")
        print(f"  Total V2 fallbacks: {summary.total_v2_fallbacks}")
        print(f"  Total illegal actions: {summary.total_illegal_actions}")
        if summary.v4_metrics:
            m = summary.v4_metrics
            print(f"  V4 success: {m.get('v4_success', 0)}")
            print(f"  V2 fallback rate: {m.get('v2_fallback_rate', 'N/A')}")
            print(f"  Request 1 success rate: {m.get('request1_success_rate', 'N/A')}")
            print(f"  Request 2 success rate: {m.get('request2_success_rate', 'N/A')}")
    print("=" * 60)


def save_results(summary: SimulationSummary, filename: str):
    """Save results to JSON file."""
    data = {
        "ai_version": summary.planning_version,
        "timestamp": datetime.now().isoformat(),
        "total_games": summary.total_games,
        "completed_games": summary.completed_games,
        "player1_wins": summary.player1_wins,
        "player2_wins": summary.player2_wins,
        "draws": summary.draws,
        "errors": summary.errors,
        "avg_turns": summary.avg_turns,
        "avg_duration_ms": summary.avg_duration_ms,
        "total_v2_fallbacks": summary.total_v2_fallbacks,
        "total_illegal_actions": summary.total_illegal_actions,
        "v4_metrics": summary.v4_metrics,
        "duration_seconds": summary.duration_seconds,
    }
    
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Results saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Run AI simulation tests")
    parser.add_argument("--games", type=int, default=10, help="Number of games to run")
    parser.add_argument("--quick", action="store_true", help="Quick test (2 games)")
    parser.add_argument("--compare", action="store_true", help="Compare V4 vs V3")
    parser.add_argument("--version", type=str, default="4", choices=["3", "4"],
                       help="AI version to test (3=single-request, 4=dual-request)")
    parser.add_argument("--save", type=str, help="Save results to JSON file")
    parser.add_argument("--player1-model", type=str, default="gemini-2.5-flash-lite",
                       help="Model for player 1")
    parser.add_argument("--player2-model", type=str, default="gemini-2.5-flash-lite",
                       help="Model for player 2")
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.environ.get("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY environment variable not set")
        sys.exit(1)
    
    num_games = 2 if args.quick else args.games
    
    if args.compare:
        # Run both V3 and V4
        print("\n=== COMPARING AI V3 vs V4 ===\n")
        
        v3_summary = run_simulation(num_games, "3", args.player1_model, args.player2_model)
        print_summary(v3_summary)
        
        v4_summary = run_simulation(num_games, "4", args.player1_model, args.player2_model)
        print_summary(v4_summary)
        
        # Print comparison
        print("\n" + "=" * 60)
        print("COMPARISON")
        print("=" * 60)
        print(f"V3 avg turns: {v3_summary.avg_turns:.1f} | V4 avg turns: {v4_summary.avg_turns:.1f}")
        print(f"V3 avg duration: {v3_summary.avg_duration_ms:.0f}ms | V4 avg duration: {v4_summary.avg_duration_ms:.0f}ms")
        print(f"V3 errors: {v3_summary.errors} | V4 errors: {v4_summary.errors}")
        if v4_summary.v4_metrics:
            print(f"V4 fallback rate: {v4_summary.v4_metrics.get('v2_fallback_rate', 'N/A')}")
        
        if args.save:
            save_results(v3_summary, args.save.replace(".json", "_v3.json"))
            save_results(v4_summary, args.save.replace(".json", "_v4.json"))
    else:
        # Run single version
        summary = run_simulation(num_games, args.version, args.player1_model, args.player2_model)
        print_summary(summary)
        
        if args.save:
            save_results(summary, args.save)
    
    # Return success if most games completed
    completed_ratio = summary.completed_games / num_games if not args.compare else 1.0
    sys.exit(0 if completed_ratio >= 0.8 else 1)


if __name__ == "__main__":
    main()