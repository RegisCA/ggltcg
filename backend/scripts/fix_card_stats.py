#!/usr/bin/env python3
"""
One-off script to recalculate card stats from game playback data.

This script fixes card stats that weren't properly persisted due to
the SQLAlchemy JSON mutation detection bug (missing flag_modified).

Run from backend directory:
    python scripts/fix_card_stats.py

Or with dry-run to see what would change:
    python scripts/fix_card_stats.py --dry-run
"""

import sys
import os
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


def recalculate_card_stats(dry_run: bool = False):
    """
    Recalculate card stats from game playback data.
    
    Args:
        dry_run: If True, print what would change but don't save
    """
    db = SessionLocal()
    
    try:
        # Get all game playbacks (within retention period)
        playbacks = db.query(GamePlaybackModel).all()
        print(f"Found {len(playbacks)} game playbacks to process")
        
        if not playbacks:
            print("No playbacks found. Nothing to fix.")
            return
        
        # Aggregate card stats per player
        # Structure: {player_id: {card_name: {"games_played": N, "games_won": N}}}
        player_card_stats = defaultdict(lambda: defaultdict(lambda: {"games_played": 0, "games_won": 0}))
        player_names = {}  # player_id -> display_name
        
        for playback in playbacks:
            winner_id = playback.winner_id
            
            # Process player 1
            p1_id = playback.player1_id
            p1_name = playback.player1_name
            p1_deck = playback.starting_deck_p1 or []
            p1_won = (winner_id == p1_id)
            
            player_names[p1_id] = p1_name
            for card_name in set(p1_deck):  # Use set to count each card once per game
                player_card_stats[p1_id][card_name]["games_played"] += 1
                if p1_won:
                    player_card_stats[p1_id][card_name]["games_won"] += 1
            
            # Process player 2
            p2_id = playback.player2_id
            p2_name = playback.player2_name
            p2_deck = playback.starting_deck_p2 or []
            p2_won = (winner_id == p2_id)
            
            player_names[p2_id] = p2_name
            for card_name in set(p2_deck):  # Use set to count each card once per game
                player_card_stats[p2_id][card_name]["games_played"] += 1
                if p2_won:
                    player_card_stats[p2_id][card_name]["games_won"] += 1
        
        # Update player stats in database
        print(f"\nProcessing {len(player_card_stats)} players...")
        
        for player_id, card_stats in player_card_stats.items():
            player_name = player_names.get(player_id, "Unknown")
            
            # Get existing player stats
            stats = db.query(PlayerStatsModel).filter(
                PlayerStatsModel.player_id == player_id
            ).first()
            
            if not stats:
                print(f"  ⚠️  No stats record for {player_name} ({player_id}) - skipping")
                continue
            
            # Convert defaultdict to regular dict
            new_card_stats = {k: dict(v) for k, v in card_stats.items()}
            
            print(f"\n  📊 {player_name} ({player_id}):")
            print(f"     Current card_stats: {stats.card_stats}")
            print(f"     New card_stats:     {new_card_stats}")
            
            if not dry_run:
                stats.card_stats = new_card_stats
                flag_modified(stats, 'card_stats')
        
        if dry_run:
            print("\n🔍 DRY RUN - No changes saved")
        else:
            db.commit()
            print("\n✅ Card stats updated successfully!")
            
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Recalculate card stats from game playback data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without saving"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("Card Stats Recalculation Script")
    print("=" * 60)
    
    recalculate_card_stats(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
