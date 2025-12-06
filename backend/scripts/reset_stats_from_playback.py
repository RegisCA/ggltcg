#!/usr/bin/env python3
"""
One-off script to reset all player stats from game playback data only.

This wipes existing stats and rebuilds them ONLY from games we have
complete playback records for (with accurate starting decks, turn counts,
and durations).

Run from backend directory:
    python scripts/reset_stats_from_playback.py

Or with dry-run to see what would change:
    python scripts/reset_stats_from_playback.py --dry-run
"""

import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import argparse
from collections import defaultdict

from api.database import SessionLocal
from api.db_models import GamePlaybackModel, PlayerStatsModel


def reset_stats_from_playback(dry_run: bool = False):
    """
    Reset all player stats using only game playback data.
    
    Args:
        dry_run: If True, print what would change but don't save
    """
    db = SessionLocal()
    
    try:
        # Get all game playbacks
        playbacks = db.query(GamePlaybackModel).all()
        print(f"Found {len(playbacks)} game playbacks to process")
        
        if not playbacks:
            print("No playbacks found. This would wipe all stats!")
            if not dry_run:
                response = input("Continue and wipe all stats? (yes/no): ")
                if response.lower() != "yes":
                    print("Aborted.")
                    return
        
        # Aggregate complete stats per player from playback data
        # Structure: {player_id: {all stats fields}}
        player_stats = defaultdict(lambda: {
            "display_name": "",
            "games_played": 0,
            "games_won": 0,
            "total_tussles": 0,  # Not tracked in playback, will be 0
            "tussles_won": 0,    # Not tracked in playback, will be 0
            "total_turns": 0,
            "total_game_duration_seconds": 0,
            "card_stats": defaultdict(lambda: {"games_played": 0, "games_won": 0}),
        })
        
        for playback in playbacks:
            winner_id = playback.winner_id
            turn_count = playback.turn_count or 0
            
            # Calculate duration from timestamps
            duration_seconds = 0
            if playback.completed_at and playback.created_at:
                duration_seconds = int((playback.completed_at - playback.created_at).total_seconds())
            
            # Process player 1
            p1_id = playback.player1_id
            p1_won = (winner_id == p1_id)
            p1_deck = playback.starting_deck_p1 or []
            
            player_stats[p1_id]["display_name"] = playback.player1_name
            player_stats[p1_id]["games_played"] += 1
            if p1_won:
                player_stats[p1_id]["games_won"] += 1
            player_stats[p1_id]["total_turns"] += turn_count
            player_stats[p1_id]["total_game_duration_seconds"] += duration_seconds
            
            for card_name in set(p1_deck):
                player_stats[p1_id]["card_stats"][card_name]["games_played"] += 1
                if p1_won:
                    player_stats[p1_id]["card_stats"][card_name]["games_won"] += 1
            
            # Process player 2
            p2_id = playback.player2_id
            p2_won = (winner_id == p2_id)
            p2_deck = playback.starting_deck_p2 or []
            
            player_stats[p2_id]["display_name"] = playback.player2_name
            player_stats[p2_id]["games_played"] += 1
            if p2_won:
                player_stats[p2_id]["games_won"] += 1
            player_stats[p2_id]["total_turns"] += turn_count
            player_stats[p2_id]["total_game_duration_seconds"] += duration_seconds
            
            for card_name in set(p2_deck):
                player_stats[p2_id]["card_stats"][card_name]["games_played"] += 1
                if p2_won:
                    player_stats[p2_id]["card_stats"][card_name]["games_won"] += 1
        
        # Show summary
        print(f"\n{'='*60}")
        print("STATS RESET SUMMARY")
        print(f"{'='*60}")
        
        # Get existing stats for comparison
        existing_stats = {s.player_id: s for s in db.query(PlayerStatsModel).all()}
        
        for player_id, new_stats in sorted(player_stats.items(), key=lambda x: x[1]["games_played"], reverse=True):
            old = existing_stats.get(player_id)
            name = new_stats["display_name"]
            
            games = new_stats["games_played"]
            wins = new_stats["games_won"]
            win_rate = (wins / games * 100) if games > 0 else 0
            avg_turns = new_stats["total_turns"] / games if games > 0 else 0
            avg_duration = new_stats["total_game_duration_seconds"] / games if games > 0 else 0
            
            print(f"\n📊 {name}")
            if old:
                print(f"   Games: {old.games_played} -> {games}")
                print(f"   Wins:  {old.games_won} -> {wins}")
                print(f"   Win%:  {old.win_rate:.1f}% -> {win_rate:.1f}%")
            else:
                print(f"   Games: (new) {games}")
                print(f"   Wins:  (new) {wins}")
                print(f"   Win%:  (new) {win_rate:.1f}%")
            print(f"   Avg turns: {avg_turns:.1f}")
            print(f"   Avg duration: {avg_duration:.0f}s")
            print(f"   Cards tracked: {len(new_stats['card_stats'])}")
        
        # Check for players who will lose all stats
        players_to_delete = set(existing_stats.keys()) - set(player_stats.keys())
        if players_to_delete:
            print(f"\n⚠️  Players with NO playback data (stats will be deleted):")
            for pid in players_to_delete:
                old = existing_stats[pid]
                print(f"   - {old.display_name}: {old.games_played} games will be lost")
        
        if dry_run:
            print(f"\n🔍 DRY RUN - No changes saved")
            return
        
        # Confirm before proceeding
        print(f"\n{'='*60}")
        response = input("Apply these changes? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            return
        
        # Delete players not in playback data
        for pid in players_to_delete:
            db.query(PlayerStatsModel).filter(PlayerStatsModel.player_id == pid).delete()
        
        # Update or create stats for each player
        for player_id, new_stats in player_stats.items():
            stats = existing_stats.get(player_id)
            
            # Convert card_stats defaultdict to regular dict
            card_stats_dict = {k: dict(v) for k, v in new_stats["card_stats"].items()}
            
            if stats:
                # Update existing
                stats.display_name = new_stats["display_name"]
                stats.games_played = new_stats["games_played"]
                stats.games_won = new_stats["games_won"]
                stats.total_tussles = 0  # Reset - not tracked in playback
                stats.tussles_won = 0    # Reset - not tracked in playback
                stats.total_turns = new_stats["total_turns"]
                stats.total_game_duration_seconds = new_stats["total_game_duration_seconds"]
                stats.card_stats = card_stats_dict
            else:
                # Create new
                stats = PlayerStatsModel(
                    player_id=player_id,
                    display_name=new_stats["display_name"],
                    games_played=new_stats["games_played"],
                    games_won=new_stats["games_won"],
                    total_tussles=0,
                    tussles_won=0,
                    total_turns=new_stats["total_turns"],
                    total_game_duration_seconds=new_stats["total_game_duration_seconds"],
                    card_stats=card_stats_dict,
                )
                db.add(stats)
        
        db.commit()
        print(f"\n✅ Stats reset successfully for {len(player_stats)} players!")
            
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Reset all player stats from game playback data only"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without saving"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("PLAYER STATS RESET SCRIPT")
    print("=" * 60)
    print("\n⚠️  WARNING: This will REPLACE all player stats with data")
    print("    from game_playback table only (last 24 hours of games).")
    print("    Historical game counts will be lost!\n")
    
    reset_stats_from_playback(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
