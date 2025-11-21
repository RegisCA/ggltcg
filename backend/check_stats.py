"""Quick script to check game stats in database."""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("DATABASE_URL not set!")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check total stats
    result = conn.execute(text("SELECT COUNT(*) FROM game_stats"))
    count = result.scalar()
    print(f"Total game_stats records: {count}")
    
    # Show recent stats
    result = conn.execute(text("""
        SELECT game_id, winner_id, loser_id, total_turns, 
               winner_cards_played, winner_tussles_initiated, winner_direct_attacks,
               created_at
        FROM game_stats 
        ORDER BY created_at DESC 
        LIMIT 5
    """))
    
    rows = result.fetchall()
    if rows:
        print("\nRecent games:")
        for row in rows:
            print(f"  Game {row[0]}: Winner={row[1]}, Turns={row[3]}, Cards={row[4]}, Tussles={row[5]}, Attacks={row[6]}")
    else:
        print("\nNo stats found yet")
