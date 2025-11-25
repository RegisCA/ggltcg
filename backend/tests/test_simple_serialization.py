"""
Test that Copy card effects survive serialization/deserialization.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_engine.models.card import Card, CardType, Zone
from game_engine.models.player import Player
from game_engine.models.game_state import GameState, Phase
from game_engine.game_engine import GameEngine
from game_engine.data.card_loader import CardLoader
from api.serialization import serialize_game_state, deserialize_game_state
from game_engine.rules.effects import EffectRegistry
from game_engine.rules.effects.effect_registry import EffectFactory

# Load cards from CSV
cards_csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
loader = CardLoader(str(cards_csv_path))
all_cards = loader.load_cards_dict()

# Create Ka card in play
ka = Card(
    name=all_cards['Ka'].name,
    card_type=all_cards['Ka'].card_type,
    cost=all_cards['Ka'].cost,
    effect_text=all_cards['Ka'].effect_text,
    effect_definitions=all_cards['Ka'].effect_definitions,
    speed=all_cards['Ka'].speed,
    strength=all_cards['Ka'].strength,
    stamina=all_cards['Ka'].stamina,
    owner="player1",
    controller="player1",
    zone=Zone.IN_PLAY,
)

# Create transformed Copy card
copy_card = Card(
    name="Copy of Ka",
    card_type=CardType.TOY,
    cost=all_cards['Ka'].cost,
    effect_text=all_cards['Ka'].effect_text,
    effect_definitions=all_cards['Ka'].effect_definitions,
    speed=all_cards['Ka'].speed,
    strength=all_cards['Ka'].strength,
    stamina=all_cards['Ka'].stamina,
    owner="player1",
    controller="player1",
    zone=Zone.IN_PLAY,
)

# Mark as transformed and create _copied_effects
copy_card._is_transformed = True
copy_card._copied_effects = EffectFactory.parse_effects(
    copy_card.effect_definitions,
    copy_card
)

print(f"Copy BEFORE serialization:")
print(f"  Has _is_transformed: {hasattr(copy_card, '_is_transformed')}")
print(f"  Has _copied_effects: {hasattr(copy_card, '_copied_effects')}")
print(f"  _copied_effects count: {len(copy_card._copied_effects) if hasattr(copy_card, '_copied_effects') else 0}")

# Create players
player1 = Player(
    player_id="player1",
    name="Player 1",
    cc=6,
    hand=[],
    in_play=[ka, copy_card],
    sleep_zone=[],
)

player2 = Player(
    player_id="player2",
    name="Player 2",
    cc=6,
    hand=[],
    in_play=[],
    sleep_zone=[],
)

# Create game state
game_state = GameState(
    game_id="test-game",
    players={"player1": player1, "player2": player2},
    active_player_id="player1",
    turn_number=1,
    phase=Phase.MAIN,
    first_player_id="player1",
)

# Create engine
engine = GameEngine(game_state=game_state)

# Check Ka's strength before serialization
ka_strength_before = engine.get_card_stat(ka, 'strength')
print(f"\nKa strength BEFORE serialization: {ka_strength_before} (expected 13: 9 base + 2 Ka + 2 Copy)")

# Serialize
serialized = serialize_game_state(game_state)
print(f"\nSerialized Copy modifications: {serialized['players']['player1']['in_play'][1].get('modifications', {})}")
print(f"Serialized Copy has effect_definitions: {'effect_definitions' in serialized['players']['player1']['in_play'][1]}")

# Deserialize
deserialized_state = deserialize_game_state(serialized)
deserialized_copy = deserialized_state.players["player1"].in_play[1]

print(f"\nCopy AFTER deserialization:")
print(f"  Has _is_transformed: {hasattr(deserialized_copy, '_is_transformed')}")
print(f"  Has _copied_effects: {hasattr(deserialized_copy, '_copied_effects')}")
print(f"  _copied_effects count: {len(deserialized_copy._copied_effects) if hasattr(deserialized_copy, '_copied_effects') else 0}")

# Check EffectRegistry
effects = EffectRegistry.get_effects(deserialized_copy)
print(f"  EffectRegistry returns: {[type(e).__name__ for e in effects]}")

# Create new engine with deserialized state
engine2 = GameEngine(game_state=deserialized_state)
deserialized_ka = deserialized_state.players["player1"].in_play[0]

# Check Ka's strength after deserialization
ka_strength_after = engine2.get_card_stat(deserialized_ka, 'strength')
print(f"\nKa strength AFTER deserialization: {ka_strength_after} (expected 13)")

if ka_strength_after == 13:
    print("\n✅ TEST PASSED! Copy effects survived serialization!")
else:
    print(f"\n❌ TEST FAILED! Expected 13, got {ka_strength_after}")
