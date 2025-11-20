#!/usr/bin/env python3
"""Debug script to test Twist effect."""

import sys
sys.path.insert(0, '/Users/regis/Projects/ggltcg/backend/src')

from game_engine.game_engine import GameEngine
from game_engine.models.card import Card, CardType, Zone
from game_engine.models.player import Player
from game_engine.models.game_state import GameState, Phase

# Create a simple game
p1 = Player(player_id="player_1", name="Alice")
p2 = Player(player_id="player_2", name="Bob")
game_state = GameState(
    game_id="test_game",
    players={"player_1": p1, "player_2": p2},
    active_player_id="player_1"
)
p1.cc = 5
p2.cc = 5
game_state.phase = Phase.MAIN  # Set to Main phase so cards can be played

engine = GameEngine(game_state)

print("=" * 60)
print("INITIAL STATE")
print("=" * 60)
print(f"Player 1 in_play: {[c.name for c in p1.in_play]}")
print(f"Player 2 in_play: {[c.name for c in p2.in_play]}")

# Give player 1 a Twist card in hand
twist_card = Card(
    name="Twist",
    card_type=CardType.ACTION,
    cost=1,
    effect_text="Take control of a card in play."
)
twist_card.owner = p1.player_id
twist_card.controller = p1.player_id
twist_card.zone = Zone.HAND
p1.hand.append(twist_card)

# Give player 2 a card to steal (Ka)
ka_card = Card(
    name="Ka",
    card_type=CardType.TOY,
    cost=2,
    stamina=3,
    strength=2,
    effect_text=""
)
ka_card.owner = p2.player_id
ka_card.controller = p2.player_id
ka_card.zone = Zone.IN_PLAY
ka_card.current_stamina = 3
p2.in_play.append(ka_card)

print(f"\nAdded Twist to P1 hand: {[c.name for c in p1.hand]}")
print(f"Added Ka to P2 in_play: {[c.name for c in p2.in_play]}")
print(f"Ka controller: {ka_card.controller}")
print(f"Ka zone: {ka_card.zone}")

# Give player 1 enough CC
p1.combat_counters = 5

print("\n" + "=" * 60)
print("PLAYING TWIST WITH TARGET=Ka")
print("=" * 60)

# Check if we can play the card
can_play, reason = engine.can_play_card(twist_card, p1, target=ka_card)
print(f"\ncan_play_card result: {can_play}, reason: '{reason}'")

# Play Twist targeting Ka
success = engine.play_card(p1, twist_card, target=ka_card)

print(f"\nplay_card success: {success}")
print(f"\nPlayer 1 in_play: {[c.name for c in p1.in_play]}")
print(f"Player 2 in_play: {[c.name for c in p2.in_play]}")
print(f"Ka controller: {ka_card.controller}")
print(f"Ka zone: {ka_card.zone}")

print("\n" + "=" * 60)
print("PLAY-BY-PLAY LOG")
print("=" * 60)
for entry in engine.game_state.play_by_play:
    print(f"{entry['player_name']}: {entry['description']}")

print("\n" + "=" * 60)
print("EVENT LOG")
print("=" * 60)
for event in engine.game_state.game_log:
    print(event)
