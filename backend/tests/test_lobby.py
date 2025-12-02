"""
Test the multiplayer lobby flow.

Tests: create lobby, join lobby, submit decks, start game.
"""

import pytest
import requests
import json

BASE_URL = "http://localhost:8000"

@pytest.mark.skip(reason="Requires running server - integration test")
def test_lobby_flow():
    """Test complete lobby flow."""
    
    # Use Google-ID-like strings for testing
    player1_id = "google_111222333444"
    player2_id = "google_555666777888"
    
    print("=== STEP 1: Player 1 creates lobby ===")
    create_response = requests.post(
        f"{BASE_URL}/games/lobby/create",
        json={"player1_id": player1_id, "player1_name": "Alice"}
    )
    create_response.raise_for_status()
    create_data = create_response.json()
    print(f"✓ Lobby created: {create_data['game_code']}")
    print(f"  Game ID: {create_data['game_id']}")
    print(f"  Player 1 ID: {create_data['player1_id']}")
    print(f"  Status: {create_data['status']}")
    
    game_code = create_data['game_code']
    game_id = create_data['game_id']
    
    print(f"\n=== STEP 2: Check lobby status (waiting) ===")
    status_response = requests.get(f"{BASE_URL}/games/lobby/{game_code}/status")
    status_response.raise_for_status()
    status_data = status_response.json()
    print(f"✓ Status: {status_data['status']}")
    print(f"  Player 1: {status_data['player1_name']} ({status_data['player1_id']})")
    print(f"  Player 2: {status_data['player2_name']}")
    
    print(f"\n=== STEP 3: Player 2 joins lobby ===")
    join_response = requests.post(
        f"{BASE_URL}/games/lobby/{game_code}/join",
        json={"player2_id": player2_id, "player2_name": "Bob"}
    )
    join_response.raise_for_status()
    join_data = join_response.json()
    print(f"✓ Player 2 joined")
    print(f"  Player 1: {join_data['player1_name']} ({join_data['player1_id']})")
    print(f"  Player 2: {join_data['player2_name']} ({join_data['player2_id']})")
    print(f"  Status: {join_data['status']}")
    
    print(f"\n=== STEP 4: Check lobby status (both players joined) ===")
    status_response = requests.get(f"{BASE_URL}/games/lobby/{game_code}/status")
    status_response.raise_for_status()
    status_data = status_response.json()
    print(f"✓ Status: {status_data['status']}")
    print(f"  Ready to start: {status_data['ready_to_start']}")
    
    print(f"\n=== STEP 5: Player 1 submits deck ===")
    p1_deck = ["Ka", "Demideca", "Ballaber", "Twist", "Clean", "Sun"]
    start1_response = requests.post(
        f"{BASE_URL}/games/lobby/{game_code}/start",
        json={
            "player_id": player1_id,
            "deck": p1_deck
        }
    )
    start1_response.raise_for_status()
    start1_data = start1_response.json()
    print(f"✓ Player 1 deck submitted")
    print(f"  Status: {start1_data['status']}")
    print(f"  Ready: {start1_data.get('ready', False)}")
    
    print(f"\n=== STEP 6: Player 2 submits deck ===")
    p2_deck = ["Ka", "Demideca", "Ballaber", "Twist", "Clean", "Sun"]
    start2_response = requests.post(
        f"{BASE_URL}/games/lobby/{game_code}/start",
        json={
            "player_id": player2_id,
            "deck": p2_deck
        }
    )
    start2_response.raise_for_status()
    start2_data = start2_response.json()
    print(f"✓ Player 2 deck submitted")
    print(f"  Status: {start2_data['status']}")
    print(f"  Ready: {start2_data.get('ready', False)}")
    
    if start2_data['status'] == 'active':
        print(f"\n✅ GAME STARTED!")
        print(f"  First player: {start2_data['first_player_id']}")
        print(f"  Game ID: {start2_data['game_id']}")
        
        # Verify we can get the game state
        print(f"\n=== STEP 7: Verify game state ===")
        game_response = requests.get(f"{BASE_URL}/games/{game_id}")
        game_response.raise_for_status()
        game_data = game_response.json()
        print(f"✓ Game retrieved")
        print(f"  Turn: {game_data['turn_number']}")
        print(f"  Phase: {game_data['phase']}")
        print(f"  Active player: {game_data['active_player_id']}")
    else:
        print(f"\n❌ GAME NOT STARTED")
        print(f"  Final status: {start2_data['status']}")

if __name__ == "__main__":
    try:
        test_lobby_flow()
        print("\n✅ ALL TESTS PASSED")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
