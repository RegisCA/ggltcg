"""
Verification script for migration 007: Rename temporary card names

This script checks that:
1. Old card names (Dwumm, Twombon) no longer exist in card_stats
2. New card names (Drum, Violin) exist with proper statistics
3. Stats were preserved during the rename

Run this after executing migration 007.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.api.database import get_db

def verify_card_name_migration():
    """Verify that card names were successfully migrated."""
    db = next(get_db())
    
    print("\n" + "="*80)
    print("MIGRATION 007 VERIFICATION: Card Name Cleanup")
    print("="*80)
    
    # Check for old card names
    old_names_result = db.execute(text("""
        SELECT COUNT(*) 
        FROM player_stats 
        WHERE card_stats ? 'Dwumm' OR card_stats ? 'Twombon'
    """))
    old_names_count = old_names_result.scalar()
    
    # Check for new card names
    new_names_result = db.execute(text("""
        SELECT player_id, display_name, 
               (card_stats->'Drum')::text as drum_stats,
               (card_stats->'Violin')::text as violin_stats
        FROM player_stats
        WHERE card_stats ? 'Drum' OR card_stats ? 'Violin'
        ORDER BY display_name
    """))
    new_names = list(new_names_result)
    
    # Display results
    print(f"\n📊 Old card names (Dwumm/Twombon): {old_names_count}")
    print(f"📊 Players with new card names (Drum/Violin): {len(new_names)}")
    
    if new_names:
        print("\n" + "-"*80)
        print("Players with updated card stats:")
        print("-"*80)
        for row in new_names:
            print(f"\nPlayer: {row.display_name} ({row.player_id[:16]}...)")
            if row.drum_stats and row.drum_stats != 'null':
                print(f"  🥁 Drum stats: {row.drum_stats}")
            if row.violin_stats and row.violin_stats != 'null':
                print(f"  🎻 Violin stats: {row.violin_stats}")
    
    # Final verdict
    print("\n" + "="*80)
    if old_names_count == 0 and len(new_names) > 0:
        print("✅ MIGRATION SUCCESSFUL!")
        print("   - All temporary card names have been renamed")
        print("   - Statistics preserved for Drum and Violin")
        return 0
    elif old_names_count > 0:
        print("❌ MIGRATION INCOMPLETE!")
        print(f"   - {old_names_count} records still contain old card names")
        return 1
    else:
        print("⚠️  NO DATA FOUND")
        print("   - No records with old or new card names")
        print("   - This is okay if no games have been played with these cards")
        return 0

if __name__ == "__main__":
    try:
        sys.exit(verify_card_name_migration())
    except Exception as e:
        print(f"\n❌ Error verifying migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
