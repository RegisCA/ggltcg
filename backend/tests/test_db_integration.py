#!/usr/bin/env python3
"""Integration test for database persistence"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import pytest
from dotenv import load_dotenv
load_dotenv()

from api.game_service import GameService

@pytest.mark.skip(reason="Requires database setup - integration test")
def test_create_and_load_game():
    """Test creating a game, saving to DB, and loading it back"""
    from pathlib import Path
    cards_csv = Path(__file__).parent.parent / "data" / "cards.csv"
    service = GameService(cards_csv_path=str(cards_csv), use_database=True)
    
    print("\n🎮 Testing Database Persistence Integration")
    print("=" * 60)
    
    # Create a new game
    print("\n1️⃣ Creating new game...")
    game_id, engine = service.create_game(
        player1_id="test-player-1",
        player1_name="Alice",
        player1_deck=["Beary", "Knight", "Wizard"],  # Valid cards from CSV
        player2_id="ai",
        player2_name="AI Opponent",
        player2_deck=["Beary", "Knight", "Wizard"],  # Same deck
    )
    print(f"   ✓ Game created: {game_id}")
    print(f"   ✓ Initial turn: {engine.game_state.turn_number}")
    print(f"   ✓ Active player: {engine.game_state.get_active_player().name}")
    
    # Clear in-memory cache to force DB load
    print("\n2️⃣ Clearing in-memory cache...")
    service._cache.clear()
    print("   ✓ Cache cleared")
    
    # Load game from database
    print("\n3️⃣ Loading game from database...")
    loaded_engine = service.get_game(game_id)
    
    if loaded_engine is None:
        print("   ❌ FAILED: Game not found in database!")
        return False
    
    print(f"   ✓ Game loaded: {game_id}")
    print(f"   ✓ Turn number: {loaded_engine.game_state.turn_number}")
    print(f"   ✓ Active player: {loaded_engine.game_state.get_active_player().name}")
    print(f"   ✓ Status: active")
    
    # Verify data matches
    print("\n4️⃣ Verifying data integrity...")
    p1_id = list(engine.game_state.players.keys())[0]
    p2_id = list(engine.game_state.players.keys())[1]
    
    checks = [
        (engine.game_state.turn_number == loaded_engine.game_state.turn_number, "Turn number"),
        (engine.game_state.active_player_id == loaded_engine.game_state.active_player_id, "Active player ID"),
        (len(engine.game_state.players[p1_id].hand) == len(loaded_engine.game_state.players[p1_id].hand), "Player 1 hand size"),
        (len(engine.game_state.players[p2_id].hand) == len(loaded_engine.game_state.players[p2_id].hand), "Player 2 hand size"),
    ]
    
    all_passed = True
    for passed, check_name in checks:
        status = "✓" if passed else "❌"
        print(f"   {status} {check_name}")
        if not passed:
            all_passed = False
    
    # Test game update
    print("\n5️⃣ Testing game state update...")
    # Get the engine from cache (it was loaded in get_game)
    engine = service._cache[game_id]
    original_turn = engine.game_state.turn_number
    
    # Simulate a turn change
    engine.game_state.turn_number += 1
    service.update_game(game_id, engine)
    print(f"   ✓ Updated turn: {original_turn} → {engine.game_state.turn_number}")
    
    # Clear cache and reload
    service._cache.clear()
    updated_engine = service.get_game(game_id)
    
    if updated_engine.game_state.turn_number == engine.game_state.turn_number:
        print(f"   ✓ Update persisted: Turn {updated_engine.game_state.turn_number}")
    else:
        print(f"   ❌ Update NOT persisted: Expected {engine.game_state.turn_number}, got {updated_engine.game_state.turn_number}")
        all_passed = False
    
    # Cleanup
    print("\n6️⃣ Cleaning up test data...")
    service.delete_game(game_id)
    print("   ✓ Test game deleted")
    
    # Final result
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Database persistence is working!")
    else:
        print("❌ SOME TESTS FAILED - Check output above")
    print("=" * 60 + "\n")
    
    return all_passed

if __name__ == "__main__":
    success = test_create_and_load_game()
    sys.exit(0 if success else 1)
