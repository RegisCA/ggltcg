"""
Serialization utilities for converting game state to/from database format.

Provides functions to serialize GameState and related objects to JSON-compatible
dictionaries for storage in PostgreSQL JSONB columns, and deserialize them back
to Python objects.
"""

import logging
from typing import Dict, Any, List
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Card, CardType, Zone
from game_engine.data.card_loader import CardLoader

logger = logging.getLogger(__name__)


def serialize_card(card: Card) -> Dict[str, Any]:
    """
    Convert Card object to JSON-serializable dictionary.
    
    Args:
        card: Card object to serialize
        
    Returns:
        Dictionary representation of the card
    """
    return {
        "id": card.id,
        "name": card.name,
        "card_type": card.card_type.value,
        "cost": card.cost,
        "effect_text": card.effect_text,
        "speed": card.speed,
        "strength": card.strength,
        "stamina": card.stamina,
        "primary_color": card.primary_color,
        "accent_color": card.accent_color,
        "owner": card.owner,
        "controller": card.controller,
        "zone": card.zone.value,
        "modifications": card.modifications,
    }


def deserialize_card(data: Dict[str, Any]) -> Card:
    """
    Convert JSON dictionary to Card object.
    
    Args:
        data: Dictionary representation of the card
        
    Returns:
        Card object
    """
    return Card(
        id=data["id"],
        name=data["name"],
        card_type=CardType(data["card_type"]),
        cost=data["cost"],
        effect_text=data["effect_text"],
        speed=data.get("speed"),
        strength=data.get("strength"),
        stamina=data.get("stamina"),
        primary_color=data.get("primary_color"),
        accent_color=data.get("accent_color"),
        owner=data["owner"],
        controller=data["controller"],
        zone=Zone(data["zone"]),
        modifications=data.get("modifications", {}),
    )


def serialize_player(player: Player) -> Dict[str, Any]:
    """
    Convert Player object to JSON-serializable dictionary.
    
    Args:
        player: Player object to serialize
        
    Returns:
        Dictionary representation of the player
    """
    return {
        "player_id": player.player_id,
        "name": player.name,
        "cc": player.cc,
        "hand": [serialize_card(card) for card in player.hand],
        "in_play": [serialize_card(card) for card in player.in_play],
        "sleep_zone": [serialize_card(card) for card in player.sleep_zone],
        "direct_attacks_this_turn": player.direct_attacks_this_turn,
    }


def deserialize_player(data: Dict[str, Any]) -> Player:
    """
    Convert JSON dictionary to Player object.
    
    Args:
        data: Dictionary representation of the player
        
    Returns:
        Player object
    """
    return Player(
        player_id=data["player_id"],
        name=data["name"],
        cc=data["cc"],
        hand=[deserialize_card(card_data) for card_data in data["hand"]],
        in_play=[deserialize_card(card_data) for card_data in data["in_play"]],
        sleep_zone=[deserialize_card(card_data) for card_data in data["sleep_zone"]],
        direct_attacks_this_turn=data.get("direct_attacks_this_turn", 0),
    )


def serialize_game_state(game_state: GameState) -> Dict[str, Any]:
    """
    Convert GameState object to JSON-serializable dictionary.
    
    This is used to store the complete game state in the database as JSONB.
    
    Args:
        game_state: GameState object to serialize
        
    Returns:
        Dictionary representation of the game state
    """
    return {
        "game_id": game_state.game_id,
        "players": {
            player_id: serialize_player(player)
            for player_id, player in game_state.players.items()
        },
        "active_player_id": game_state.active_player_id,
        "turn_number": game_state.turn_number,
        "phase": game_state.phase.value,
        "first_player_id": game_state.first_player_id,
        "winner_id": game_state.winner_id,
        "game_log": game_state.game_log,
        "play_by_play": game_state.play_by_play,
    }


def deserialize_game_state(data: Dict[str, Any]) -> GameState:
    """
    Convert JSON dictionary to GameState object.
    
    This reconstructs the complete game state from database JSONB.
    
    Args:
        data: Dictionary representation of the game state
        
    Returns:
        GameState object
    """
    return GameState(
        game_id=data["game_id"],
        players={
            player_id: deserialize_player(player_data)
            for player_id, player_data in data["players"].items()
        },
        active_player_id=data["active_player_id"],
        turn_number=data["turn_number"],
        phase=Phase(data["phase"]),
        first_player_id=data["first_player_id"],
        winner_id=data.get("winner_id"),
        game_log=data.get("game_log", []),
        play_by_play=data.get("play_by_play", []),
    )


def extract_metadata(game_state: GameState) -> Dict[str, Any]:
    """
    Extract metadata from GameState for denormalized database columns.
    
    This creates the denormalized fields that enable efficient queries
    without having to parse the JSONB column.
    
    Args:
        game_state: GameState object
        
    Returns:
        Dictionary with metadata fields
    """
    # Get player information
    player_ids = list(game_state.players.keys())
    player1_id = player_ids[0]
    player2_id = player_ids[1]
    
    # Determine status
    if game_state.winner_id:
        status = "completed"
    else:
        status = "active"
    
    return {
        "player1_id": player1_id,
        "player1_name": game_state.players[player1_id].name,
        "player2_id": player2_id,
        "player2_name": game_state.players[player2_id].name,
        "status": status,
        "winner_id": game_state.winner_id,
        "turn_number": game_state.turn_number,
        "active_player_id": game_state.active_player_id,
        "phase": game_state.phase.value,
    }
