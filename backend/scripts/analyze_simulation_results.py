import sys
import os
from pathlib import Path
import json
from collections import defaultdict
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))
sys.path.append(str(backend_dir / "src"))

# Load environment variables
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

from src.api.database import SessionLocal
from src.api.db_models import SimulationRunModel, SimulationGameModel

def analyze_runs(run_ids):
    db = SessionLocal()
    try:
        print(f"Analyzing runs: {run_ids}")
        print("-" * 80)
        
        all_games = []
        run_configs = {}
        
        for run_id in run_ids:
            run = db.query(SimulationRunModel).filter(SimulationRunModel.id == run_id).first()
            if not run:
                print(f"Run {run_id} not found!")
                continue
                
            run_configs[run_id] = run.config
            games = db.query(SimulationGameModel).filter(SimulationGameModel.run_id == run_id).all()
            all_games.extend(games)
            
            p1_model = run.config.get("player1_model")
            p2_model = run.config.get("player2_model")
            
            print(f"Run {run_id}: {len(games)} games")
            print(f"  P1: {p1_model}")
            print(f"  P2: {p2_model}")
            
            # Calculate run-specific stats
            p1_wins = sum(1 for g in games if g.outcome == "player1_win")
            p2_wins = sum(1 for g in games if g.outcome == "player2_win")
            draws = sum(1 for g in games if g.outcome == "draw")
            
            print(f"  Results: P1 Wins: {p1_wins} ({p1_wins/len(games):.1%}), P2 Wins: {p2_wins} ({p2_wins/len(games):.1%}), Draws: {draws}")
            print("-" * 40)

        # Cross-Run Analysis
        # We want to compare 2.0 vs 2.5-lite
        
        # Group 1: Mirror Matches (Baseline)
        # Run 18: 2.0 vs 2.0
        # Run 26: 2.5-lite vs 2.5-lite
        
        # Group 2: Head-to-Head
        # Run 22: P1=2.0, P2=2.5-lite
        # Run 23: P1=2.5-lite, P2=2.0
        
        print("\nHEAD-TO-HEAD ANALYSIS (2.0 vs 2.5-lite)")
        print("=" * 80)
        
        h2h_games = [g for g in all_games if g.run_id in [22, 23]]
        
        model_stats = defaultdict(lambda: {"wins": 0, "games": 0, "turns": 0})
        
        for game in h2h_games:
            p1_model = game.player1_model
            p2_model = game.player2_model
            
            # Track stats for P1 model
            model_stats[p1_model]["games"] += 1
            model_stats[p1_model]["turns"] += game.turn_count
            if game.outcome == "player1_win":
                model_stats[p1_model]["wins"] += 1
            
            # Track stats for P2 model
            model_stats[p2_model]["games"] += 1
            model_stats[p2_model]["turns"] += game.turn_count
            if game.outcome == "player2_win":
                model_stats[p2_model]["wins"] += 1

        for model, stats in model_stats.items():
            win_rate = stats["wins"] / stats["games"] if stats["games"] > 0 else 0
            avg_turns = stats["turns"] / stats["games"] if stats["games"] > 0 else 0
            print(f"Model: {model}")
            print(f"  Games Played: {stats['games']}")
            print(f"  Wins: {stats['wins']}")
            print(f"  Win Rate: {win_rate:.1%}")
            print(f"  Avg Turns: {avg_turns:.1f}")
            print("-" * 20)

        print("\nMATCHUP BREAKDOWN (Head-to-Head)")
        print("=" * 80)
        
        # Breakdown by Deck Matchup
        matchups = defaultdict(lambda: {"2.0_wins": 0, "2.5_lite_wins": 0, "total": 0})
        
        for game in h2h_games:
            # Normalize matchup key (alphabetical order of decks)
            decks = sorted([game.deck1_name, game.deck2_name])
            matchup_key = f"{decks[0]} vs {decks[1]}"
            
            matchups[matchup_key]["total"] += 1
            
            winner_model = ""
            if game.outcome == "player1_win":
                winner_model = game.player1_model
            elif game.outcome == "player2_win":
                winner_model = game.player2_model
                
            if winner_model == "gemini-2.0-flash":
                matchups[matchup_key]["2.0_wins"] += 1
            elif winner_model == "gemini-2.5-flash-lite":
                matchups[matchup_key]["2.5_lite_wins"] += 1
                
        print(f"{'Matchup':<40} | {'2.0 Wins':<10} | {'2.5-Lite Wins':<15} | {'Total':<5}")
        print("-" * 80)
        for matchup, stats in matchups.items():
            print(f"{matchup:<40} | {stats['2.0_wins']:<10} | {stats['2.5_lite_wins']:<15} | {stats['total']:<5}")

        print("\nFIRST PLAYER ADVANTAGE (Mirror Matches)")
        print("=" * 80)
        
        mirror_runs = [18, 26]
        for run_id in mirror_runs:
            run_games = [g for g in all_games if g.run_id == run_id]
            if not run_games:
                continue
                
            model = run_configs[run_id].get("player1_model")
            p1_wins = sum(1 for g in run_games if g.outcome == "player1_win")
            p1_win_rate = p1_wins / len(run_games)
            
            print(f"Model: {model} (Run {run_id})")
            print(f"  Games: {len(run_games)}")
            print(f"  P1 Win Rate: {p1_win_rate:.1%}")
            print("-" * 20)

    finally:
        db.close()

if __name__ == "__main__":
    analyze_runs([18, 22, 23, 26])
