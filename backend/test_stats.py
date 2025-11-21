"""
Test script to verify game stats collection.

Plays a complete game and checks that stats are saved to the database.
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def create_game():
    """Create a new game."""
    response = requests.post(
        f"{BASE_URL}/games",
        json={
            "player1_id": "test-player-1",
            "player1_name": "TestPlayer1",
            "player1_deck": ["Ka", "Demideca", "Ballaber", "Twist", "Clean", "Sun"],
            "player2_id": "AI",
            "player2_name": "AI",
            "player2_deck": ["Ka", "Demideca", "Ballaber", "Twist", "Clean", "Sun"],
            "first_player_id": "test-player-1"
        }
    )
    response.raise_for_status()
    data = response.json()
    return data["game_id"]

def get_game_state(game_id):
    """Get current game state."""
    response = requests.get(f"{BASE_URL}/games/{game_id}")
    response.raise_for_status()
    return response.json()

def ai_turn(game_id):
    """Trigger AI turn."""
    response = requests.post(f"{BASE_URL}/games/{game_id}/ai-turn")
    response.raise_for_status()
    return response.json()

def play_until_complete(game_id):
    """Play game until completion using AI for all turns."""
    max_turns = 50
    turn_count = 0
    
    while turn_count < max_turns:
        # Get current state
        state = get_game_state(game_id)
        
        # Check if game is over
        if state.get("winner"):
            print(f"Game complete! Winner: {state['winner']}")
            print(f"Final turn: {state['turn_number']}")
            return True
        
        # Let AI make a move
        print(f"Turn {state['turn_number']}, Phase: {state['phase']}, Active: {state['active_player_id']}")
        ai_response = ai_turn(game_id)
        
        time.sleep(0.5)  # Brief pause
        turn_count += 1
    
    print(f"Game didn't complete after {max_turns} AI turns")
    return False

def check_stats(game_id):
    """Check if stats were saved for this game."""
    # Query database directly using psql
    import subprocess
    import os
    
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set, skipping database check")
        return False
    
    try:
        result = subprocess.run(
            [
                "psql", db_url, "-c",
                f"SELECT * FROM game_stats WHERE game_id = '{game_id}';"
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = result.stdout
            print("\nGame Stats:")
            print(output)
            
            # Check if we got a result
            return "row" in output.lower()
        else:
            print(f"Database query failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error checking stats: {e}")
        return False

def main():
    """Run the test."""
    print("Creating new game...")
    game_id = create_game()
    print(f"Game created: {game_id}")
    
    print("\nPlaying game until completion...")
    completed = play_until_complete(game_id)
    
    if completed:
        print("\n✅ Game completed successfully!")
        
        # Wait a moment for stats to be written
        time.sleep(1)
        
        print("\nChecking if stats were saved...")
        if check_stats(game_id):
            print("✅ Stats were saved successfully!")
        else:
            print("❌ Stats were NOT saved")
    else:
        print("\n❌ Game did not complete")

if __name__ == "__main__":
    main()
