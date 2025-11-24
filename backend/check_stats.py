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
    print(f"Total game_stats records: **{count}**")
    
    # Show recent stats
    result = conn.execute(text("""
        SELECT game_id, winner_id, loser_id, total_turns, 
               duration_seconds, created_at
        FROM game_stats 
        ORDER BY created_at DESC 
        LIMIT 30
    """))
    
    rows = result.fetchall()
    if rows:
        print("\n10 most Recent game stats:")
        for row in rows:
            print(f"  Game {row[0]}: Winner={row[1]}, Loser={row[2]}, Turns={row[3]}, Duration(s)={row[4]}, Time={row[5]}")
    else:
        print("\nNo stats found yet")

    # Show recent games by status 
    result = conn.execute(text("""
        SELECT id, created_at, status, turn_number, active_player_id, phase
        FROM games 
        ORDER BY created_at DESC 
        LIMIT 10
    """))
    
    rows = result.fetchall()
    if rows:
        print("\n10 most Recent game statuses:")
        for row in rows:
            print(f"  Game {row[0]}: Created={row[1]}, Status={row[2]}, Turn={row[3]}, Active player={row[4]}, Phase={row[5]}")
    else:
        print("\nNo stats found yet")