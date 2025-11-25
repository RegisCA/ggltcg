"""
Quick script to check the actual game state for debugging Copy effect issue.
"""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("DATABASE_URL not set!")
    exit(1)


def check_game_state(game_id: str):
    """Check the game state stored in the database."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(
            text('SELECT game_state FROM games WHERE id = :game_id'),
            {'game_id': game_id}
        )
        row = result.fetchone()
        
        if not row:
            print(f"Game {game_id} not found in database")
            return
        
        game_state = row[0]  # Already a dict, not JSON string
        
        # Display cards in play for each player
        for player_id, player_data in game_state.get('players', {}).items():
            player_name = player_data.get('name', player_id)
            print(f"\n{'='*60}")
            print(f"{player_name} - CARDS IN PLAY")
            print('='*60)
            
            in_play = player_data.get('in_play', [])
            if not in_play:
                print("  (no cards in play)")
                continue
            
            for card in in_play:
                print(f"\n  {card['name']} ({card['card_type']}):")
                print(f"    ID: {card['id']}")
                
                if card['card_type'] == 'Toy':
                    print(f"    STR: {card.get('strength')} (base: {card.get('base_strength')})")
                    print(f"    SPD: {card.get('speed')} (base: {card.get('base_speed')})")
                    print(f"    STA: {card.get('stamina')} (base: {card.get('base_stamina')})")
                
                if card.get('effect_text'):
                    print(f"    Effect: {card['effect_text']}")


if __name__ == '__main__':
    import sys
    game_id = '2e9ce7c5-5464-40b3-8a95-9080d2d268d5'
    if len(sys.argv) > 1:
        game_id = sys.argv[1]
    
    print(f"Checking game state for: {game_id}\n")
    check_game_state(game_id)
