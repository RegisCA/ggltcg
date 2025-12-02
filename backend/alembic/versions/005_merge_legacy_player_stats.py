"""Merge legacy player stats into Google ID records.

Revision ID: 005_merge_legacy_stats
Revises: 004_create_stats_tables
Create Date: 2025-12-02

This migration consolidates player stats that were recorded with inconsistent
player IDs before the hotfix:

Legacy records to merge:
- Sully: 'human' (24 games, 23 wins) + 'player1' (2 games, 2 wins) → Google ID
- Régis: 'human-*' (3 records, 3 games each) + 'player2' (2 games) → Google ID
- AI: 'ai' (24 games) + 'ai-*' (random UUIDs) → 'ai-gemiknight'

The migration:
1. Identifies the correct Google ID for each player by matching display_name
2. Aggregates stats from legacy records into the Google ID record
3. Deletes the legacy records
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '005_merge_legacy_stats'
down_revision = '004_create_stats_tables'
branch_labels = None
depends_on = None


# Mapping of legacy player IDs to their correct Google ID
# Based on the data analysis from the production database
PLAYER_MAPPINGS = {
    # Sully's legacy records → Sully's Google ID
    'human': '109662458516887657743',
    'player1': '109662458516887657743',
    
    # Régis's legacy records → Régis's Google ID  
    'human-b669ef1a-315a-40ac-ba1a-c3072cfdb882': '112649547955082543047',
    'human-7b629c64-3fb9-41ff-9a99-36f501b484fa': '112649547955082543047',
    'human-b8e10272-f668-4805-b628-212c25fc7a63': '112649547955082543047',
    'player2': '112649547955082543047',
    
    # AI legacy records → consistent AI ID
    'ai': 'ai-gemiknight',
    'ai-708fc4be-aa17-4ba0-bb68-4a229e817acd': 'ai-gemiknight',
    'ai-c1f03223-05db-40dd-b810-f2b3745f0e89': 'ai-gemiknight',
    'ai-fb82911a-1a4c-4f11-b9d5-821c0f17b22a': 'ai-gemiknight',
}


def merge_card_stats(existing: dict, incoming: dict) -> dict:
    """Merge card stats from two records."""
    if not existing:
        return incoming or {}
    if not incoming:
        return existing or {}
    
    merged = dict(existing)
    for card_name, stats in incoming.items():
        if card_name in merged:
            merged[card_name] = {
                'games_played': merged[card_name].get('games_played', 0) + stats.get('games_played', 0),
                'games_won': merged[card_name].get('games_won', 0) + stats.get('games_won', 0),
                'tussles_initiated': merged[card_name].get('tussles_initiated', 0) + stats.get('tussles_initiated', 0),
                'tussles_won': merged[card_name].get('tussles_won', 0) + stats.get('tussles_won', 0),
            }
        else:
            merged[card_name] = stats
    return merged


def upgrade() -> None:
    """Merge legacy player stats into Google ID records."""
    bind = op.get_bind()
    session = Session(bind=bind)
    
    try:
        # Process each legacy record
        for legacy_id, target_id in PLAYER_MAPPINGS.items():
            # Get the legacy record
            legacy_result = session.execute(
                text("""
                    SELECT player_id, display_name, games_played, games_won, 
                           total_tussles, tussles_won, card_stats
                    FROM player_stats 
                    WHERE player_id = :legacy_id
                """),
                {"legacy_id": legacy_id}
            ).fetchone()
            
            if not legacy_result:
                print(f"Legacy record '{legacy_id}' not found, skipping...")
                continue
            
            # Check if target record exists
            target_result = session.execute(
                text("""
                    SELECT player_id, display_name, games_played, games_won,
                           total_tussles, tussles_won, card_stats
                    FROM player_stats 
                    WHERE player_id = :target_id
                """),
                {"target_id": target_id}
            ).fetchone()
            
            if target_result:
                # Merge into existing target record
                print(f"Merging '{legacy_id}' into existing '{target_id}'...")
                
                # Merge card stats (need to handle JSONB)
                legacy_card_stats = legacy_result[6] or {}
                target_card_stats = target_result[6] or {}
                merged_card_stats = merge_card_stats(target_card_stats, legacy_card_stats)
                
                session.execute(
                    text("""
                        UPDATE player_stats SET
                            games_played = games_played + :games_played,
                            games_won = games_won + :games_won,
                            total_tussles = total_tussles + :total_tussles,
                            tussles_won = tussles_won + :tussles_won,
                            card_stats = :card_stats,
                            updated_at = NOW()
                        WHERE player_id = :target_id
                    """),
                    {
                        "target_id": target_id,
                        "games_played": legacy_result[2],
                        "games_won": legacy_result[3],
                        "total_tussles": legacy_result[4],
                        "tussles_won": legacy_result[5],
                        "card_stats": str(merged_card_stats).replace("'", '"'),  # JSON format
                    }
                )
            else:
                # Create new target record from legacy
                print(f"Creating '{target_id}' from '{legacy_id}'...")
                
                # Determine display name for the target
                if target_id == 'ai-gemiknight':
                    display_name = 'Gemiknight'
                else:
                    display_name = legacy_result[1]  # Keep legacy display name
                
                session.execute(
                    text("""
                        INSERT INTO player_stats 
                            (player_id, display_name, games_played, games_won,
                             total_tussles, tussles_won, card_stats, created_at, updated_at)
                        VALUES 
                            (:player_id, :display_name, :games_played, :games_won,
                             :total_tussles, :tussles_won, :card_stats, NOW(), NOW())
                    """),
                    {
                        "player_id": target_id,
                        "display_name": display_name,
                        "games_played": legacy_result[2],
                        "games_won": legacy_result[3],
                        "total_tussles": legacy_result[4],
                        "tussles_won": legacy_result[5],
                        "card_stats": str(legacy_result[6] or {}).replace("'", '"'),
                    }
                )
            
            # Delete the legacy record
            print(f"Deleting legacy record '{legacy_id}'...")
            session.execute(
                text("DELETE FROM player_stats WHERE player_id = :legacy_id"),
                {"legacy_id": legacy_id}
            )
        
        session.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"Migration failed: {e}")
        raise


def downgrade() -> None:
    """
    Downgrade is not fully reversible since we're merging data.
    This would require keeping a backup of the original records.
    """
    # We can't truly reverse this migration without storing the original data
    # For safety, we just log a warning
    print("WARNING: This migration cannot be fully reversed. Data was merged.")
    pass
