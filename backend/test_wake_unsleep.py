"""
Debug script to test Wake/unsleep functionality.
"""

from src.game_engine.game_engine import GameEngine
from src.game_engine.models.player import Player
from src.game_engine.models.card import Card, CardType, Zone
from src.game_engine.models.game_state import GameState

# Create game
game_state = GameState()
engine = GameEngine(game_state)
p1_id, p2_id = engine.start_game(
    player1_name="Player1",
    player2_name="Player2",
    player1_deck_name="Strength",
    player2_deck_name="Strength"
)

game_state = engine.game_state
p1 = game_state.players[p1_id]
p2 = game_state.players[p2_id]

print(f"\n=== Initial State ===")
print(f"P1 hand: {[c.name for c in p1.hand]}")
print(f"P1 sleep: {[c.name for c in p1.sleep_zone]}")

# Manually put Ka in sleep zone
ka = None
for card in p1.hand:
    if card.name == "Ka":
        ka = card
        break

if ka:
    print(f"\n=== Moving Ka to sleep zone ===")
    p1.hand.remove(ka)
    ka.zone = Zone.SLEEP
    p1.sleep_zone.append(ka)
    print(f"P1 sleep: {[c.name for c in p1.sleep_zone]}")
    print(f"Ka zone: {ka.zone}")
    print(f"Ka ID: {ka.id}")

# Find Wake card
wake = None
for card in p1.hand:
    if card.name == "Wake":
        wake = card
        break

if wake:
    print(f"\n=== Playing Wake to unsleep Ka ===")
    print(f"Wake ID: {wake.id}")
    
    # Test what happens when we call unsleep_card directly
    print(f"\nDirect unsleep test:")
    print(f"  Before - Ka in sleep_zone: {ka in p1.sleep_zone}")
    print(f"  Before - Ka in hand: {ka in p1.hand}")
    
    # Try the unsleep method
    game_state.unsleep_card(ka, p1)
    
    print(f"  After - Ka in sleep_zone: {ka in p1.sleep_zone}")
    print(f"  After - Ka in hand: {ka in p1.hand}")
    print(f"  After - Ka zone: {ka.zone}")
    
    # Put Ka back in sleep for the real test
    if ka in p1.hand:
        p1.hand.remove(ka)
        ka.zone = Zone.SLEEP
        p1.sleep_zone.append(ka)
        print(f"\n  Reset - Ka back in sleep zone")
    
    # Now try playing Wake with Ka as target
    print(f"\n=== Playing Wake card with Ka as target ===")
    success = engine.play_card(p1, wake, targets=[ka])
    
    print(f"  Success: {success}")
    print(f"  After play - Ka in sleep_zone: {ka in p1.sleep_zone}")
    print(f"  After play - Ka in hand: {ka in p1.hand}")
    print(f"  After play - Ka zone: {ka.zone}")
    print(f"  After play - Wake in sleep_zone: {wake in p1.sleep_zone}")
    print(f"  After play - Wake zone: {wake.zone}")
    
    print(f"\nP1 hand: {[c.name for c in p1.hand]}")
    print(f"P1 sleep: {[c.name for c in p1.sleep_zone]}")
else:
    print("Wake not found in hand!")
