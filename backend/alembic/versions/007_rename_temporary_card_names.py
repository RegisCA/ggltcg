"""rename temporary card names in card_stats

Revision ID: 007
Revises: 006
Create Date: 2025-12-15 00:00:00.000000

This migration renames temporary card names that were used during development:
- Dwumm → Drum
- Twombon → Violin

Updates the card_stats JSONB column in player_stats table to replace the old
card names with the new ones.

Issue: https://github.com/RegisCA/ggltcg/issues/225
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename temporary card names in player_stats.card_stats."""
    
    # Get database connection
    connection = op.get_bind()
    
    # SQL to update card_stats JSONB:
    # 1. Remove old key "Dwumm" and add to "Drum"
    # 2. Remove old key "Twombon" and add to "Violin"
    
    # Update Dwumm → Drum
    # For each player that has "Dwumm" stats, merge them into "Drum"
    update_dwumm_sql = text("""
        UPDATE player_stats
        SET card_stats = 
            -- Remove Dwumm key and merge its stats into Drum
            CASE
                WHEN card_stats ? 'Dwumm' THEN
                    -- If both exist, merge the stats
                    CASE
                        WHEN card_stats ? 'Drum' THEN
                            card_stats 
                            - 'Dwumm'
                            || jsonb_build_object(
                                'Drum',
                                jsonb_build_object(
                                    'games_played', 
                                    COALESCE((card_stats->'Drum'->>'games_played')::int, 0) + 
                                    COALESCE((card_stats->'Dwumm'->>'games_played')::int, 0),
                                    'games_won',
                                    COALESCE((card_stats->'Drum'->>'games_won')::int, 0) + 
                                    COALESCE((card_stats->'Dwumm'->>'games_won')::int, 0),
                                    'tussles_initiated',
                                    COALESCE((card_stats->'Drum'->>'tussles_initiated')::int, 0) + 
                                    COALESCE((card_stats->'Dwumm'->>'tussles_initiated')::int, 0),
                                    'tussles_won',
                                    COALESCE((card_stats->'Drum'->>'tussles_won')::int, 0) + 
                                    COALESCE((card_stats->'Dwumm'->>'tussles_won')::int, 0)
                                )
                            )
                        -- If only Dwumm exists, just rename it to Drum
                        ELSE
                            (card_stats - 'Dwumm') || jsonb_build_object('Drum', card_stats->'Dwumm')
                    END
                ELSE
                    card_stats
            END
        WHERE card_stats ? 'Dwumm'
    """)
    
    # Update Twombon → Violin
    update_twombon_sql = text("""
        UPDATE player_stats
        SET card_stats = 
            -- Remove Twombon key and merge its stats into Violin
            CASE
                WHEN card_stats ? 'Twombon' THEN
                    -- If both exist, merge the stats
                    CASE
                        WHEN card_stats ? 'Violin' THEN
                            card_stats 
                            - 'Twombon'
                            || jsonb_build_object(
                                'Violin',
                                jsonb_build_object(
                                    'games_played', 
                                    COALESCE((card_stats->'Violin'->>'games_played')::int, 0) + 
                                    COALESCE((card_stats->'Twombon'->>'games_played')::int, 0),
                                    'games_won',
                                    COALESCE((card_stats->'Violin'->>'games_won')::int, 0) + 
                                    COALESCE((card_stats->'Twombon'->>'games_won')::int, 0),
                                    'tussles_initiated',
                                    COALESCE((card_stats->'Violin'->>'tussles_initiated')::int, 0) + 
                                    COALESCE((card_stats->'Twombon'->>'tussles_initiated')::int, 0),
                                    'tussles_won',
                                    COALESCE((card_stats->'Violin'->>'tussles_won')::int, 0) + 
                                    COALESCE((card_stats->'Twombon'->>'tussles_won')::int, 0)
                                )
                            )
                        -- If only Twombon exists, just rename it to Violin
                        ELSE
                            (card_stats - 'Twombon') || jsonb_build_object('Violin', card_stats->'Twombon')
                    END
                ELSE
                    card_stats
            END
        WHERE card_stats ? 'Twombon'
    """)
    
    # Execute updates
    result_dwumm = connection.execute(update_dwumm_sql)
    result_twombon = connection.execute(update_twombon_sql)
    
    print(f"Updated {result_dwumm.rowcount} player records with Dwumm → Drum")
    print(f"Updated {result_twombon.rowcount} player records with Twombon → Violin")


def downgrade() -> None:
    """Revert card name changes (Drum → Dwumm, Violin → Twombon)."""
    
    # Get database connection
    connection = op.get_bind()
    
    # This is a best-effort downgrade. If stats were merged, we can't
    # perfectly split them back. We'll just rename the keys back.
    
    # Revert Drum → Dwumm
    revert_drum_sql = text("""
        UPDATE player_stats
        SET card_stats = 
            (card_stats - 'Drum') || jsonb_build_object('Dwumm', card_stats->'Drum')
        WHERE card_stats ? 'Drum'
    """)
    
    # Revert Violin → Twombon
    revert_violin_sql = text("""
        UPDATE player_stats
        SET card_stats = 
            (card_stats - 'Violin') || jsonb_build_object('Twombon', card_stats->'Violin')
        WHERE card_stats ? 'Violin'
    """)
    
    # Execute reverts
    result_drum = connection.execute(revert_drum_sql)
    result_violin = connection.execute(revert_violin_sql)
    
    print(f"Reverted {result_drum.rowcount} player records with Drum → Dwumm")
    print(f"Reverted {result_violin.rowcount} player records with Violin → Twombon")
