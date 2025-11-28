"""
Shared pytest fixtures and test helpers for GGLTCG backend tests.

This module provides:
1. Standard game state fixtures
2. Card creation helpers
3. Common test scenarios

Usage:
    from conftest import create_game_with_cards, get_card_template

Guidelines:
    - Always use GameEngine to execute game actions (not GameState directly)
    - Use create_card() helper to create cards with proper initialization
    - Use get_card_template() to get card stats from CSV
    - Set owner AND controller when creating cards
    - Initialize current_stamina = stamina for Toy cards
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_engine.game_engine import GameEngine
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Card, CardType, Zone
from game_engine.data.card_loader import CardLoader


# Cache for card templates loaded from CSV
_card_templates: Optional[Dict[str, Card]] = None


def get_card_templates() -> Dict[str, Card]:
    """
    Load all card templates from CSV (cached).
    
    Returns:
        Dictionary mapping card name to Card template
    """
    global _card_templates
    if _card_templates is None:
        csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
        loader = CardLoader(str(csv_path))
        all_cards = loader.load_cards()
        _card_templates = {card.name: card for card in all_cards}
    return _card_templates


def get_card_template(name: str) -> Card:
    """
    Get a card template by name.
    
    Args:
        name: Card name (e.g., "Knight", "Ka", "Clean")
        
    Returns:
        Card template from CSV
        
    Raises:
        KeyError: If card not found
    """
    templates = get_card_templates()
    if name not in templates:
        available = sorted(templates.keys())
        raise KeyError(f"Card '{name}' not found. Available cards: {available}")
    return templates[name]


def create_card(
    name: str,
    owner: str,
    controller: Optional[str] = None,
    zone: Zone = Zone.HAND,
) -> Card:
    """
    Create a new card instance from template with proper initialization.
    
    Args:
        name: Card name (must exist in cards.csv)
        owner: Player ID who owns the card
        controller: Player ID who controls the card (defaults to owner)
        zone: Initial zone for the card
        
    Returns:
        Fully initialized Card instance
    """
    template = get_card_template(name)
    controller = controller or owner
    
    card = Card(
        name=template.name,
        card_type=template.card_type,
        cost=template.cost,
        effect_text=template.effect_text,
        speed=template.speed,
        strength=template.strength,
        stamina=template.stamina,
        primary_color=template.primary_color,
        accent_color=template.accent_color,
        owner=owner,
        controller=controller,
        zone=zone,
        effect_definitions=template.effect_definitions,
    )
    
    # Initialize current_stamina for Toy cards
    if card.card_type == CardType.TOY and card.stamina is not None:
        card.current_stamina = card.stamina
    
    return card


@dataclass
class GameSetup:
    """Container for a fully set up game with engine and state."""
    engine: GameEngine
    game_state: GameState
    player1: Player
    player2: Player
    
    def get_player(self, player_id: str) -> Player:
        """Get player by ID."""
        return self.game_state.players[player_id]


def create_basic_game(
    player1_cc: int = 10,
    player2_cc: int = 10,
    active_player: str = "player1",
    turn_number: int = 2,  # Default to turn 2 so Rush/Raggy restrictions don't apply
) -> GameSetup:
    """
    Create a basic game with two players and no cards.
    
    Args:
        player1_cc: Starting CC for player 1
        player2_cc: Starting CC for player 2
        active_player: Which player is active ("player1" or "player2")
        turn_number: Current turn number
        
    Returns:
        GameSetup with empty hands and play zones
    """
    player1 = Player(player_id="player1", name="Player 1")
    player2 = Player(player_id="player2", name="Player 2")
    
    player1.cc = player1_cc
    player2.cc = player2_cc
    
    game_state = GameState(
        game_id="test_game",
        players={"player1": player1, "player2": player2},
        active_player_id=active_player,
        first_player_id="player1",
        turn_number=turn_number,
        phase=Phase.MAIN,
    )
    
    engine = GameEngine(game_state)
    
    return GameSetup(
        engine=engine,
        game_state=game_state,
        player1=player1,
        player2=player2,
    )


def create_game_with_cards(
    player1_hand: Optional[List[str]] = None,
    player1_in_play: Optional[List[str]] = None,
    player1_sleep: Optional[List[str]] = None,
    player2_hand: Optional[List[str]] = None,
    player2_in_play: Optional[List[str]] = None,
    player2_sleep: Optional[List[str]] = None,
    player1_cc: int = 10,
    player2_cc: int = 10,
    active_player: str = "player1",
    turn_number: int = 2,
) -> Tuple[GameSetup, Dict[str, Card]]:
    """
    Create a game with specified cards in various zones.
    
    Args:
        player1_hand: List of card names for player 1's hand
        player1_in_play: List of card names for player 1's play zone
        player1_sleep: List of card names for player 1's sleep zone
        player2_hand: List of card names for player 2's hand
        player2_in_play: List of card names for player 2's play zone
        player2_sleep: List of card names for player 2's sleep zone
        player1_cc: Starting CC for player 1
        player2_cc: Starting CC for player 2
        active_player: Which player is active
        turn_number: Current turn number
        
    Returns:
        Tuple of (GameSetup, dict mapping unique keys to Card instances)
        Keys are formatted as "p1_hand_Ka" or "p2_in_play_Knight"
    """
    setup = create_basic_game(player1_cc, player2_cc, active_player, turn_number)
    cards: Dict[str, Card] = {}
    
    def add_cards(player: Player, player_prefix: str, card_names: Optional[List[str]], 
                  zone: Zone, target_list: List[Card]):
        if not card_names:
            return
        for name in card_names:
            card = create_card(name, owner=player.player_id, zone=zone)
            target_list.append(card)
            # Create unique key for lookup
            zone_name = zone.value.lower().replace("_", "")
            key = f"{player_prefix}_{zone_name}_{name}"
            # Handle duplicates by adding index
            if key in cards:
                i = 2
                while f"{key}_{i}" in cards:
                    i += 1
                key = f"{key}_{i}"
            cards[key] = card
    
    # Add cards for player 1
    add_cards(setup.player1, "p1", player1_hand, Zone.HAND, setup.player1.hand)
    add_cards(setup.player1, "p1", player1_in_play, Zone.IN_PLAY, setup.player1.in_play)
    add_cards(setup.player1, "p1", player1_sleep, Zone.SLEEP, setup.player1.sleep_zone)
    
    # Add cards for player 2
    add_cards(setup.player2, "p2", player2_hand, Zone.HAND, setup.player2.hand)
    add_cards(setup.player2, "p2", player2_in_play, Zone.IN_PLAY, setup.player2.in_play)
    add_cards(setup.player2, "p2", player2_sleep, Zone.SLEEP, setup.player2.sleep_zone)
    
    return setup, cards


def steal_card(game_state: GameState, card: Card, new_controller_id: str) -> None:
    """
    Simulate stealing a card (like Twist effect).
    
    Moves card from current controller's in_play to new controller's in_play.
    Updates controller but NOT owner.
    
    Args:
        game_state: Current game state
        card: Card to steal (must be in play)
        new_controller_id: Player ID of new controller
    """
    old_controller = game_state.players[card.controller]
    new_controller = game_state.players[new_controller_id]
    
    # Remove from old controller
    if card in old_controller.in_play:
        old_controller.in_play.remove(card)
    
    # Add to new controller
    new_controller.in_play.append(card)
    
    # Update controller (NOT owner)
    card.controller = new_controller_id


# Pytest fixtures for common scenarios

@pytest.fixture
def basic_game() -> GameSetup:
    """Provide a basic empty game for tests."""
    return create_basic_game()


@pytest.fixture  
def card_templates() -> Dict[str, Card]:
    """Provide card templates dictionary."""
    return get_card_templates()
