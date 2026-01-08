#!/usr/bin/env python3
"""
Script to compare AI models in head-to-head simulation games.

Usage:
    cd backend
    python scripts/compare_models.py --p1 gemini-2.0-flash --p2 gemini-2.5-flash --games 5
"""

import sys
import os
import logging
import argparse
import time
import statistics
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup paths
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR / "src"))

# Load environment
from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Reduce noise
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('google_genai').setLevel(logging.WARNING)
logging.getLogger('game_engine.ai.llm_player').setLevel(logging.INFO)

logger = logging.getLogger("compare_models")

try:
    from simulation import SimulationRunner
    from simulation.deck_loader import load_simulation_decks_dict
    from simulation.config import GameResult, GameOutcome
except ImportError as e:
    logger.error(f"Failed to import simulation modules: {e}")
    sys.exit(1)


def run_single_game(runner, deck1, deck2, game_num):
    """Run a single game and return the result."""
    try:
        logger.info(f"Starting Game {game_num}...")
        start_time = time.time()
        result = runner.run_game(deck1, deck2, game_number=game_num)
        duration = time.time() - start_time
        return result
    except Exception as e:
        logger.error(f"Game {game_num} failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Compare AI models in GGLTCG")
    parser.add_argument("--p1", default="gemini-2.0-flash", help="Model for Player 1")
    parser.add_argument("--p2", default="gemini-2.0-flash", help="Model for Player 2")
    parser.add_argument("--games", type=int, default=5, help="Number of games to run")
    parser.add_argument("--deck1", default="Aggro_Rush", help="Deck for Player 1")
    parser.add_argument("--deck2", default="Aggro_Rush", help="Deck for Player 2")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers")
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info(f"MODEL COMPARISON: {args.p1} vs {args.p2}")
    logger.info(f"Decks: {args.deck1} vs {args.deck2}")
    logger.info(f"Games: {args.games} | Workers: {args.workers}")
    logger.info("=" * 60)
    
    # Load decks
    try:
        decks = load_simulation_decks_dict()
        if args.deck1 not in decks:
            logger.error(f"Deck '{args.deck1}' not found. Available: {list(decks.keys())}")
            return 1
        if args.deck2 not in decks:
            logger.error(f"Deck '{args.deck2}' not found. Available: {list(decks.keys())}")
            return 1
            
        deck1_obj = decks[args.deck1]
        deck2_obj = decks[args.deck2]
    except Exception as e:
        logger.error(f"Failed to load decks: {e}")
        return 1
        
    # Initialize runner
    # Note: We create a new runner for each game in the thread to ensure thread safety if needed,
    # or we can share one if it's stateless enough. SimulationRunner seems to be designed for single use or sequential.
    # But for parallel execution, let's create one per thread or just one if it's safe.
    # Looking at SIMULATION_SYSTEM.md, it says "Each parallel worker: Creates its own SimulationRunner instance".
    
    results = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = []
        for i in range(args.games):
            # Create a fresh runner for each game to avoid state pollution
            runner = SimulationRunner(
                player1_model=args.p1,
                player2_model=args.p2,
                max_turns=20  # Cap turns to avoid infinite loops
            )
            futures.append(executor.submit(run_single_game, runner, deck1_obj, deck2_obj, i+1))
            
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                
    # Analyze results
    if not results:
        logger.error("No games completed successfully.")
        return 1
        
    p1_wins = sum(1 for r in results if r.outcome == GameOutcome.PLAYER1_WIN)
    p2_wins = sum(1 for r in results if r.outcome == GameOutcome.PLAYER2_WIN)
    draws = sum(1 for r in results if r.outcome == GameOutcome.DRAW)
    
    durations = [r.duration_ms / 1000.0 for r in results]
    turns = [r.turn_count for r in results]
    
    logger.info("\n" + "=" * 60)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Games: {len(results)}")
    logger.info(f"P1 Wins ({args.p1}): {p1_wins} ({p1_wins/len(results)*100:.1f}%)")
    logger.info(f"P2 Wins ({args.p2}): {p2_wins} ({p2_wins/len(results)*100:.1f}%)")
    logger.info(f"Draws: {draws} ({draws/len(results)*100:.1f}%)")
    logger.info("-" * 60)
    logger.info(f"Avg Duration: {statistics.mean(durations):.2f}s (Min: {min(durations):.2f}s, Max: {max(durations):.2f}s)")
    logger.info(f"Avg Turns: {statistics.mean(turns):.1f} (Min: {min(turns)}, Max: {max(turns)})")
    logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
