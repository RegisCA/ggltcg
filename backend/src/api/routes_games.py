"""
Game management API routes.

Endpoints for creating, retrieving, and deleting games.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from api.schemas import (
    GameCreate,
    GameCreated,
    GameStateResponse,
    PlayerState,
    CardState,
    ErrorResponse,
    RandomDeckRequest,
    RandomDeckResponse,
    NarrativeRequest,
    NarrativeResponse,
    CardDataResponse,
)
from api.game_service import get_game_service
from game_engine.models.card import Zone
from game_engine.data.card_loader import random_deck, load_all_cards
from game_engine.ai.prompts import get_narrative_prompt
from game_engine.ai.llm_player import get_llm_response

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/cards", response_model=List[CardDataResponse])
async def get_all_cards() -> List[CardDataResponse]:
    """
    Get all available cards from the card database.
    
    Returns a list of all cards with their stats, effects, and metadata.
    This is the single source of truth for card data.
    Uses the same card source as game creation.
    """
    try:
        service = get_game_service()
        all_cards = service.all_cards
        
        return [
            CardDataResponse(
                name=card.name,
                card_type=card.card_type.value,
                cost=card.cost,
                effect=card.effect_text,
                speed=card.speed,
                strength=card.strength,
                stamina=card.stamina,
                primary_color=card.primary_color,
                accent_color=card.accent_color,
            )
            for card in all_cards
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load cards: {str(e)}")


@router.post("", response_model=GameCreated, status_code=201)
async def create_game(game_data: GameCreate) -> GameCreated:
    """
    Create a new game with two players.
    
    - **player1**: First player configuration (id, name, deck)
    - **player2**: Second player configuration (id, name, deck)
    - **first_player_id**: Optional - which player goes first (random if not specified)
    
    Returns the created game ID.
    """
    service = get_game_service()
    
    try:
        game_id, engine = service.create_game(
            player1_id=game_data.player1.player_id,
            player1_name=game_data.player1.name,
            player1_deck=game_data.player1.deck,
            player2_id=game_data.player2.player_id,
            player2_name=game_data.player2.name,
            player2_deck=game_data.player2.deck,
            first_player_id=game_data.first_player_id,
        )
        
        return GameCreated(game_id=game_id)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create game: {str(e)}")


@router.post("/random-deck", response_model=RandomDeckResponse)
async def get_random_deck(request: RandomDeckRequest) -> RandomDeckResponse:
    """
    Generate a random deck with specified composition.
    
    - **num_toys**: Number of Toy cards to include (0-6)
    - **num_actions**: Number of Action cards to include (0-6)
    - Sum must equal 6
    
    Returns a list of unique card names for the deck.
    Uses the same card source as game creation.
    """
    try:
        service = get_game_service()
        deck = service.generate_random_deck(num_toys=request.num_toys, num_actions=request.num_actions)
        return RandomDeckResponse(
            deck=deck,
            num_toys=request.num_toys,
            num_actions=request.num_actions,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate random deck: {str(e)}")


@router.get("/{game_id}", response_model=GameStateResponse)
async def get_game_state(game_id: str, player_id: str = None) -> GameStateResponse:
    """
    Get the current state of a game.
    
    - **game_id**: The game ID
    - **player_id**: Optional - if provided, includes that player's hand
    
    Returns complete game state including player info, cards in play, etc.
    """
    service = get_game_service()
    engine = service.get_game(game_id)
    
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    game_state = engine.game_state
    
    # Convert to response format
    players_state = {}
    for pid, player in game_state.players.items():
        # Convert cards to CardState
        in_play_cards = [_card_to_state(c, engine) for c in player.in_play]
        sleep_cards = [_card_to_state(c, engine) for c in player.sleep_zone]
        
        # Only include hand if player_id matches
        hand_cards = None
        if player_id == pid:
            hand_cards = [_card_to_state(c, engine) for c in player.hand]
        
        players_state[pid] = PlayerState(
            player_id=pid,
            name=player.name,
            cc=player.cc,
            hand_count=len(player.hand),
            hand=hand_cards,
            in_play=in_play_cards,
            sleep_zone=sleep_cards,
            direct_attacks_this_turn=player.direct_attacks_this_turn,
        )
    
    # Check if game is over
    winner = game_state.check_victory()
    
    return GameStateResponse(
        game_id=game_id,
        turn_number=game_state.turn_number,
        phase=game_state.phase.value,
        active_player_id=game_state.active_player_id,
        first_player_id=game_state.first_player_id,
        players=players_state,
        winner=winner,
        is_game_over=winner is not None,
        play_by_play=game_state.play_by_play,  # Include play-by-play history
    )


@router.delete("/{game_id}")
async def delete_game(game_id: str) -> Dict[str, str]:
    """
    Delete a game.
    
    - **game_id**: The game ID to delete
    
    Returns success message.
    """
    service = get_game_service()
    
    if not service.delete_game(game_id):
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    return {"message": f"Game {game_id} deleted successfully"}


def _card_to_state(card, engine) -> CardState:
    """Convert a Card to CardState with current stats."""
    # Get modified stats if applicable (with continuous effects applied)
    current_speed = None
    current_strength = None
    current_stamina_max = None  # Max stamina with buffs
    current_stamina = None  # Actual stamina (can be damaged)
    base_speed = None
    base_strength = None
    base_stamina = None
    
    if card.is_toy():  # Use the is_toy() method instead of string comparison
        # Get effective stats (with continuous effects like Demideca, Ka, etc.)
        current_speed = engine.get_card_stat(card, "speed")
        current_strength = engine.get_card_stat(card, "strength")
        current_stamina_max = engine.get_card_stat(card, "stamina")  # Max stamina with buffs
        
        # Calculate current stamina with buffs applied
        # If max stamina is buffed, current stamina should also be buffed by the same amount
        stamina_buff = current_stamina_max - card.stamina if card.stamina else 0
        current_stamina = card.current_stamina + stamina_buff if card.current_stamina is not None else None
        
        # Store base stats (from card definition, before buffs)
        base_speed = card.speed
        base_strength = card.strength
        base_stamina = card.stamina
    
    return CardState(
        id=card.id,
        name=card.name,
        card_type=card.card_type.value,  # Convert enum to string
        cost=card.cost,
        effect_text=card.effect_text,  # Include effect description
        zone=card.zone.value,
        owner=card.owner,
        controller=card.controller,
        speed=current_speed,
        strength=current_strength,
        stamina=current_stamina_max,  # Effective max stamina (with buffs)
        current_stamina=current_stamina,
        base_speed=base_speed,
        base_strength=base_strength,
        base_stamina=base_stamina,
        is_sleeped=(card.zone == Zone.SLEEP),
        primary_color=card.primary_color,
        accent_color=card.accent_color,
    )


@router.get("/{game_id}/logs")
async def get_game_logs(game_id: str) -> Dict[str, List[str]]:
    """
    Get the game event log for debugging.
    
    Returns the internal game_log which contains all game events including debug messages.
    """
    service = get_game_service()
    engine = service.get_game(game_id)
    
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    return {"logs": engine.game_state.game_log}


@router.get("/{game_id}/debug")
async def get_game_debug_state(game_id: str) -> Dict[str, Any]:
    """
    Get detailed debug information about a game's internal state.
    
    ⚠️ **DEV-ONLY ENDPOINT** - Not secure for production use.
    Exposes complete internal game state including:
    - All cards in all zones with full details
    - Effect definitions (CSV strings)
    - Parsed effect objects (_copied_effects)
    - Card modifications and transformations
    - Internal flags like _is_transformed
    
    **Security Note**: This endpoint reveals complete game state including opponent's
    hand. If test players discover this and use it to cheat, we'll buy them pizza! 🍕
    
    Returns:
        Comprehensive debug view of the game state with all internal details exposed.
    """
    from game_engine.rules.effects.effect_registry import EffectFactory
    
    service = get_game_service()
    engine = service.get_game(game_id)
    
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    game_state = engine.game_state
    
    def _debug_card(card) -> Dict[str, Any]:
        """Extract all card details for debugging."""
        # Parse effects to show what would be created
        parsed_effects = []
        if hasattr(card, 'effect_definitions') and card.effect_definitions:
            try:
                effects = EffectFactory.parse_effects(card.effect_definitions, card)
                parsed_effects = [
                    {
                        "class": type(effect).__name__,
                        "repr": repr(effect),
                    }
                    for effect in effects
                ]
            except Exception as e:
                parsed_effects = [{"error": str(e)}]
        
        # Get copied effects if present (for transformed Copy cards)
        copied_effects = []
        if hasattr(card, '_copied_effects') and card._copied_effects:
            copied_effects = [
                {
                    "class": type(effect).__name__,
                    "repr": repr(effect),
                }
                for effect in card._copied_effects
            ]
        
        # Get effective stats from engine
        effective_stats = {}
        if card.is_toy():
            effective_stats = {
                "speed": engine.get_card_stat(card, "speed"),
                "strength": engine.get_card_stat(card, "strength"),
                "stamina": engine.get_card_stat(card, "stamina"),
            }
        
        return {
            # Basic card info
            "id": card.id,
            "name": card.name,
            "card_type": card.card_type.value,
            "cost": card.cost,
            "zone": card.zone.value,
            "owner": card.owner,
            "controller": card.controller,
            
            # Base stats
            "base_stats": {
                "speed": card.speed,
                "strength": card.strength,
                "stamina": card.stamina,
                "current_stamina": card.current_stamina,
            } if card.is_toy() else None,
            
            # Effective stats (with all effects applied)
            "effective_stats": effective_stats if effective_stats else None,
            
            # Effect system details
            "effect_text": card.effect_text,
            "effect_definitions": getattr(card, 'effect_definitions', ''),
            "parsed_effects": parsed_effects,
            "copied_effects": copied_effects,  # For Copy cards
            
            # Modifications and state
            "modifications": card.modifications,
            "is_transformed": getattr(card, '_is_transformed', False),
            
            # Colors
            "primary_color": card.primary_color,
            "accent_color": card.accent_color,
        }
    
    def _debug_player(player) -> Dict[str, Any]:
        """Extract all player details for debugging."""
        return {
            "player_id": player.player_id,
            "name": player.name,
            "cc": player.cc,
            "direct_attacks_this_turn": player.direct_attacks_this_turn,
            "hand": [_debug_card(card) for card in player.hand],
            "in_play": [_debug_card(card) for card in player.in_play],
            "sleep_zone": [_debug_card(card) for card in player.sleep_zone],
            "hand_count": len(player.hand),
            "in_play_count": len(player.in_play),
            "sleep_zone_count": len(player.sleep_zone),
        }
    
    # Build comprehensive debug state
    debug_state = {
        "game_id": game_id,
        "turn_number": game_state.turn_number,
        "phase": game_state.phase.value,
        "active_player_id": game_state.active_player_id,
        "first_player_id": game_state.first_player_id,
        "winner_id": game_state.winner_id,
        
        # Complete player state (including opponent's hand)
        "players": {
            player_id: _debug_player(player)
            for player_id, player in game_state.players.items()
        },
        
        # Game logs
        "game_log": game_state.game_log,
        "play_by_play": game_state.play_by_play,
        
        # Metadata
        "total_cards": sum(
            len(p.hand) + len(p.in_play) + len(p.sleep_zone)
            for p in game_state.players.values()
        ),
        
        # Warning about security
        "_warning": "This endpoint exposes complete game state. Dev-only. Pizza-worthy if exploited! 🍕",
    }
    
    return debug_state


@router.post("/narrative", response_model=NarrativeResponse)
async def generate_narrative(request: NarrativeRequest) -> NarrativeResponse:
    """
    Generate a narrative "bedtime story" version of the play-by-play.
    
    Takes the factual play-by-play entries and transforms them into an enchanting
    narrative suitable for a bedtime story about epic toy battles in Googooland.
    
    - **play_by_play**: List of play-by-play entries from the game
    
    Returns a narrative story version of the game events.
    """
    try:
        # Generate narrative prompt
        prompt = get_narrative_prompt(request.play_by_play)
        
        # Get narrative from LLM
        narrative = get_llm_response(prompt, is_json=False)
        
        return NarrativeResponse(narrative=narrative)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate narrative: {str(e)}")
