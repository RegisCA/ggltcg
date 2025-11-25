"""
Integration test: Verify Copy effects work end-to-end through GameService
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.game_service import GameService

# Create game service
cards_csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
service = GameService(str(cards_csv_path))

# Create a new game
game_id = service.create_game(
    player1_id="test_player1",
    player1_name="Test Player 1",
    player2_id="test_player2",
    player2_name="Test Player 2"
)

print(f"Created game: {game_id}")

# Get the game
engine = service.get_game(game_id)
player = engine.game_state.players["test_player1"]

# Find Demideca and Copy in hand
demideca = next((c for c in player.hand if c.name == "Demideca"), None)
copy_card = next((c for c in player.hand if c.name == "Copy"), None)
ka = next((c for c in player.hand if c.name == "Ka"), None)

if not all([demideca, copy_card, ka]):
    print("❌ Required cards not found in hand, skipping test")
    sys.exit(0)

print(f"\nFound cards in hand:")
print(f"  - Demideca (id: {demideca.id})")
print(f"  - Copy (id: {copy_card.id})")
print(f"  - Ka (id: {ka.id})")

# Play Demideca
print(f"\n1. Playing Demideca...")
engine.play_toy("test_player1", demideca.id, "test_player1")
service.save_game(engine)

# Reload game
engine = service.get_game(game_id)
demideca_in_play = next((c for c in engine.game_state.players["test_player1"].in_play if "Demideca" in c.name and "Copy" not in c.name), None)
print(f"   Demideca STR: {engine.get_card_stat(demideca_in_play, 'strength')} (expected 3: 2 base + 1 from Demideca)")

# Play Copy targeting Demideca
print(f"\n2. Playing Copy targeting Demideca...")
player = engine.game_state.players["test_player1"]
copy_in_hand = next((c for c in player.hand if c.name == "Copy"), None)
engine.play_action("test_player1", copy_in_hand.id, {"target_id": demideca_in_play.id})
service.save_game(engine)

# Reload game AFTER Copy played
print("\n3. Reloading game from database...")
engine = service.get_game(game_id)
player = engine.game_state.players["test_player1"]

# Find cards in play
demideca_in_play = next((c for c in player.in_play if c.name == "Demideca" and "Copy" not in c.name), None)
copy_in_play = next((c for c in player.in_play if "Copy of Demideca" in c.name), None)

print(f"\n4. Checking Copy of Demideca after reload:")
print(f"   Has _is_transformed: {hasattr(copy_in_play, '_is_transformed')}")
print(f"   Has _copied_effects: {hasattr(copy_in_play, '_copied_effects')}")

from game_engine.rules.effects import EffectRegistry
effects = EffectRegistry.get_effects(copy_in_play)
print(f"   EffectRegistry returns: {[type(e).__name__ for e in effects]}")

print(f"\n5. Checking stats:")
demideca_str = engine.get_card_stat(demideca_in_play, 'strength')
copy_str = engine.get_card_stat(copy_in_play, 'strength')
print(f"   Demideca STR: {demideca_str} (expected 4: 2 base + 1 Demideca + 1 Copy)")
print(f"   Copy of Demideca STR: {copy_str} (expected 4: 2 base + 1 Demideca + 1 Copy)")

# Play Ka
print(f"\n6. Playing Ka...")
ka_in_hand = next((c for c in player.hand if c.name == "Ka"), None)
if ka_in_hand:
    engine.play_toy("test_player1", ka_in_hand.id, "test_player1")
    service.save_game(engine)
    
    # Reload one more time
    print("\n7. Final reload to test all effects...")
    engine = service.get_game(game_id)
    player = engine.game_state.players["test_player1"]
    
    demideca_in_play = next((c for c in player.in_play if c.name == "Demideca" and "Copy" not in c.name), None)
    copy_in_play = next((c for c in player.in_play if "Copy of Demideca" in c.name), None)
    ka_in_play = next((c for c in player.in_play if c.name == "Ka"), None)
    
    demideca_str = engine.get_card_stat(demideca_in_play, 'strength')
    copy_str = engine.get_card_stat(copy_in_play, 'strength')
    ka_str = engine.get_card_stat(ka_in_play, 'strength')
    
    print(f"\n8. Final stats check:")
    print(f"   Demideca STR: {demideca_str} (expected 4: 2 + 1 Demideca + 1 Copy)")
    print(f"   Copy of Demideca STR: {copy_str} (expected 4: 2 + 1 Demideca + 1 Copy)")
    print(f"   Ka STR: {ka_str} (expected 13: 9 + 2 Ka + 1 Demideca + 1 Copy)")
    
    if ka_str == 13:
        print(f"\n✅ SUCCESS! All Copy effects working correctly after reload!")
    else:
        print(f"\n❌ FAILED! Ka should be 13, got {ka_str}")
else:
    print("   Ka not in hand, skipping Ka test")

print("\nTest complete.")
