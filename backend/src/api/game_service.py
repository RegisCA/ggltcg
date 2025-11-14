"""
Game service for managing active games.

This service maintains a dictionary of active games and provides
methods for game lifecycle management.
"""

import uuid
import logging
from typing import Dict, Optional
import os
from pathlib import Path

logger = logging.getLogger(__name__)

from game_engine.game_engine import GameEngine
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Card
from game_engine.data.card_loader import CardLoader


class GameService:
    """
    Manages active game sessions.
    
    In a production environment, this would be replaced with a database
    and proper session management. For the MVP, we keep games in memory.
    """
    
    def __init__(self, cards_csv_path: str):
        """
        Initialize the game service.
        
        Args:
            cards_csv_path: Path to cards.csv file
        """
        self.games: Dict[str, GameEngine] = {}
        self.card_loader = CardLoader(cards_csv_path)
        self.all_cards = self.card_loader.load_cards()
    
    def create_game(
        self,
        player1_id: str,
        player1_name: str,
        player1_deck: list[str],
        player2_id: str,
        player2_name: str,
        player2_deck: list[str],
        first_player_id: Optional[str] = None,
    ) -> tuple[str, GameEngine]:
        """
        Create a new game with two players.
        
        Args:
            player1_id: Unique ID for player 1
            player1_name: Display name for player 1
            player1_deck: List of card names for player 1's deck
            player2_id: Unique ID for player 2
            player2_name: Display name for player 2
            player2_deck: List of card names for player 2's deck
            first_player_id: ID of player who goes first (random if None)
            
        Returns:
            Tuple of (game_id, GameEngine instance)
        """
        # Generate unique game ID
        game_id = str(uuid.uuid4())
        
        # Create player 1's cards
        player1_cards = self._create_deck(player1_deck, player1_id)
        
        # Create player 2's cards
        player2_cards = self._create_deck(player2_deck, player2_id)
        
        # Create players
        player1 = Player(
            player_id=player1_id,
            name=player1_name,
            hand=player1_cards,
        )
        
        player2 = Player(
            player_id=player2_id,
            name=player2_name,
            hand=player2_cards,
        )
        
        # Determine first player
        if first_player_id is None:
            import random
            first_player_id = random.choice([player1_id, player2_id])
        
        # Create game state
        game_state = GameState(
            game_id=game_id,
            players={player1_id: player1, player2_id: player2},
            active_player_id=first_player_id,
            first_player_id=first_player_id,
            turn_number=1,
            phase=Phase.START,
        )
        
        # Create game engine
        engine = GameEngine(game_state)
        
        # Start the first turn
        engine.start_turn()
        
        # Store game
        self.games[game_id] = engine
        
        return game_id, engine
    
    def get_game(self, game_id: str) -> Optional[GameEngine]:
        """
        Get a game by ID.
        
        Args:
            game_id: The game ID
            
        Returns:
            GameEngine instance or None if not found
        """
        return self.games.get(game_id)
    
    def delete_game(self, game_id: str) -> bool:
        """
        Delete a game.
        
        Args:
            game_id: The game ID
            
        Returns:
            True if deleted, False if not found
        """
        if game_id in self.games:
            del self.games[game_id]
            return True
        return False
    
    def _create_deck(self, card_names: list[str], owner_id: str) -> list[Card]:
        """
        Create a deck of cards from card names.
        
        Args:
            card_names: List of card names
            owner_id: ID of the player who owns these cards
            
        Returns:
            List of Card instances
        """
        deck = []
        for name in card_names:
            # Find card template
            template = next((c for c in self.all_cards if c.name == name), None)
            if template is None:
                raise ValueError(f"Card '{name}' not found in card database")
            
            # Create a copy of the card
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
                owner=owner_id,
                controller=owner_id,
            )
            deck.append(card)
        
        return deck
    
    def get_active_games_count(self) -> int:
        """Get the number of active games."""
        return len(self.games)


# Singleton instance
_game_service: Optional[GameService] = None


def get_game_service() -> GameService:
    """
    Get the singleton game service instance.
    
    The cards CSV path can be customized via the CARDS_CSV_PATH environment variable.
    If not set, defaults to backend/data/cards.csv.
    
    Returns:
        GameService instance
    """
    global _game_service
    if _game_service is None:
        # Determine path to cards.csv

        # Check for environment variable first
        cards_path_str = os.environ.get("CARDS_CSV_PATH")
        
        if cards_path_str:
            cards_path = Path(cards_path_str)
            logger.info(f"Using cards CSV from environment: {cards_path}")
        else:
            # Default to backend/data/cards.csv
            backend_dir = Path(__file__).parent.parent.parent
            cards_path = backend_dir / "data" / "cards.csv"
            logger.info(f"Using default cards CSV: {cards_path}")
        
        _game_service = GameService(str(cards_path))
    return _game_service
