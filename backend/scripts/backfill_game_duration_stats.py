#!/usr/bin/env python3
"""
One-off script to backfill game duration stats from game playback data.

This script populates total_turns and total_game_duration_seconds in player_stats
from existing game_playback records before they expire (24-hour retention).

Run from backend directory:
    python scripts/backfill_game_duration_stats.py

Or with dry-run to see what would change:
    python scripts/backfill_game_duration_stats.py --dry-run
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
from sqlalchemy.orm.attributes import flag_modified

from api.database import SessionLocal
from api.db_models import GamePlaybackModel, PlayerStatsModel


def backfill_game_duration_stats(dry_run: bool = False):
    """
    Backfill total_turns and total_game_duration_seconds from game playback data.
    
    Args:
        dry_run: If True, print what would change but don't save
    """
    db = SessionLocal()
    
    try:
        # Get all game playbacks (within retention period)
        playbacks = db.query(GamePlaybackModel).all()
        print(f"Found {len(playbacks)} game playbacks to process")
        
        if not playbacks:
            print("No playbacks found. Nothing to backfill.")
            return
        
        # Aggregate stats per player
        # Structure: {player_id: {"total_turns": N, "total_duration": N, "name": str}}
        player_stats_agg = defaultdict(lambda: {"total_turns": 0, "total_duration": 0, "name": ""})
        
        for playback in playbacks:
            turn_count = playback.turn_count or 0
            
            # Calculate duration from timestamps
            duration_seconds = 0
            if playback.completed_at and playback.created_at:
                duration_seconds = int((playback.completed_at - playback.created_at).total_seconds())
            
            # Player 1
            p1_id = playback.player1_id
            player_stats_agg[p1_id]["total_turns"] += turn_count
            player_stats_agg[p1_id]["total_duration"] += duration_seconds
            player_stats_agg[p1_id]["name"] = playback.player1_name
            
            # Player 2
            p2_id = playback.player2_id
            player_stats_agg[p2_id]["total_turns"] += turn_count
            player_stats_agg[p2_id]["total_duration"] += duration_seconds
            player_stats_agg[p2_id]["name"] = playback.player2_name
        
        # Update player stats in database
        print(f"\nProcessing {len(player_stats_agg)} players...")
        
        updated_count = 0
        for player_id, agg_data in player_stats_agg.items():
            player_name = agg_data["name"]
            
            # Get existing player stats
            stats = db.query(PlayerStatsModel).filter(
                PlayerStatsModel.player_id == player_id
            ).first()
            
            if not stats:
                print(f"  ⚠️  No stats record for {player_name} ({player_id}) - skipping")
                continue
            
            old_turns = getattr(stats, 'total_turns', 0) or 0
            old_duration = getattr(stats, 'total_game_duration_seconds', 0) or 0
            new_turns = agg_data["total_turns"]
            new_duration = agg_data["total_duration"]
            
            # Calculate averages for display
            games = stats.games_played or 1
            old_avg_turns = old_turns / games if old_turns else 0
            new_avg_turns = new_turns / games if new_turns else 0
            old_avg_duration = old_duration / games if old_duration else 0
            new_avg_duration = new_duration / games if new_duration else 0
            
            print(f"\n  📊 {player_name} ({stats.games_played} games):")
            print(f"     Avg turns: {old_avg_turns:.1f} -> {new_avg_turns:.1f}")
            print(f"     Avg duration: {old_avg_duration:.0f}s -> {new_avg_duration:.0f}s")
            
            if not dry_run:
                stats.total_turns = new_turns
                stats.total_game_duration_seconds = new_duration
                updated_count += 1
        
        if dry_run:
            print(f"\n🔍 DRY RUN - No changes saved (would update {len(player_stats_agg)} players)")
        else:
            db.commit()
            print(f"\n✅ Updated {updated_count} player records successfully!")
            
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Backfill game duration stats from game playback data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without saving"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("Game Duration Stats Backfill Script")
    print("=" * 60)
    
    backfill_game_duration_stats(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
