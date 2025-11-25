"""
Check what's actually serialized for Copy of Demideca
"""
from pathlib import Path
import sys
import json
import os

# Set DATABASE_URL
os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL', 'postgresql://localhost/ggltcg')

sys.path.insert(0, str(Path(__file__).parent / "src"))

from api.game_service import GameService

# Create game service
cards_csv_path = Path(__file__).parent / "data" / "cards.csv"
service = GameService(str(cards_csv_path))

# Get the game
game_id = '8592a7ee-d0a7-47e6-9f7f-8324bda06514'
engine = service.get_game(game_id)
player = engine.game_state.players["human"]

# Find Copy in play
copy_in_play = next((c for c in player.in_play if "Copy of" in c.name), None)

if copy_in_play:
    print(f"Copy card: {copy_in_play.name}")
    print(f"  Has _is_transformed: {hasattr(copy_in_play, '_is_transformed')}")
    if hasattr(copy_in_play, '_is_transformed'):
        print(f"  _is_transformed value: {copy_in_play._is_transformed}")
    print(f"  Has _copied_effects: {hasattr(copy_in_play, '_copied_effects')}")
    if hasattr(copy_in_play, '_copied_effects'):
        print(f"  _copied_effects: {copy_in_play._copied_effects}")
    print(f"  effect_definitions: {copy_in_play.effect_definitions}")
    print(f"  modifications: {copy_in_play.modifications}")
    
    # Now serialize it
    from api.serialization import serialize_card
    serialized = serialize_card(copy_in_play)
    print(f"\nSerialized Copy:")
    print(json.dumps(serialized, indent=2))
else:
    print("No Copy found in play")
