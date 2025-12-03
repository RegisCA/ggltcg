"""
Game service for managing active games.

This service manages game persistence using PostgreSQL database.
Games are stored in the database and loaded on demand.
"""

import uuid
import logging
from typing import Dict, Optional
import os
from pathlib import Path
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from game_engine.game_engine import GameEngine
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Card
from game_engine.data.card_loader import CardLoader
from api.database import SessionLocal, get_session_local
from api.db_models import GameModel, GameStatsModel
from api.serialization import (
    serialize_game_state,
    deserialize_game_state,
    extract_metadata,
)
from api.stats_service import get_stats_service


class GameService:
    """
    Manages active game sessions with PostgreSQL persistence.
    
    Games are stored in the database and loaded on demand.
    An in-memory cache is maintained for active games to improve performance.
    """
    
    def __init__(self, cards_csv_path: str, use_database: bool = True):
        """
        Initialize the game service.
        
        Args:
            cards_csv_path: Path to cards.csv file
            use_database: If True, use database persistence. If False, use in-memory only (for testing)
        """
        self.card_loader = CardLoader(cards_csv_path)
        self.all_cards = self.card_loader.load_cards()
        self.use_database = use_database
        
        # In-memory cache for active games (improves performance)
        self._cache: Dict[str, GameEngine] = {}
        
        if use_database:
            logger.info("GameService initialized with database persistence")
        else:
            logger.warning("GameService running in memory-only mode (database disabled)")
    
    def _save_game_to_db(self, game_id: str, engine: GameEngine) -> None:
        """
        Save game to database.
        
        Args:
            game_id: Game ID
            engine: GameEngine instance to save
        """
        if not self.use_database:
            return
        
        db = SessionLocal()
        try:
            # Serialize game state
            game_state_dict = serialize_game_state(engine.game_state)
            metadata = extract_metadata(engine.game_state)
            
            # Check if game exists
            game_model = db.query(GameModel).filter(GameModel.id == uuid.UUID(game_id)).first()
            
            if game_model:
                # Update existing game
                game_model.game_state = game_state_dict
                game_model.turn_number = metadata["turn_number"]
                game_model.active_player_id = metadata["active_player_id"]
                game_model.phase = metadata["phase"]
                game_model.status = metadata["status"]
                game_model.winner_id = metadata["winner_id"]
                logger.debug(f"Updated game {game_id} in database")
            else:
                # Create new game
                game_model = GameModel(
                    id=uuid.UUID(game_id),
                    player1_id=metadata["player1_id"],
                    player1_name=metadata["player1_name"],
                    player2_id=metadata["player2_id"],
                    player2_name=metadata["player2_name"],
                    status=metadata["status"],
                    winner_id=metadata["winner_id"],
                    turn_number=metadata["turn_number"],
                    active_player_id=metadata["active_player_id"],
                    phase=metadata["phase"],
                    game_state=game_state_dict,
                )
                db.add(game_model)
                logger.info(f"Created new game {game_id} in database")
            
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save game {game_id} to database: {e}")
            raise
        finally:
            db.close()
    
    def _load_game_from_db(self, game_id: str) -> Optional[GameEngine]:
        """
        Load game from database.
        
        Args:
            game_id: Game ID to load
            
        Returns:
            GameEngine instance or None if not found
        """
        if not self.use_database:
            return None
        
        db = SessionLocal()
        try:
            game_model = db.query(GameModel).filter(GameModel.id == uuid.UUID(game_id)).first()
            
            if not game_model:
                return None
            
            # Deserialize game state
            game_state = deserialize_game_state(game_model.game_state)
            
            # Create GameEngine instance
            engine = GameEngine(game_state)
            
            logger.debug(f"Loaded game {game_id} from database")
            return engine
        except Exception as e:
            logger.error(f"Failed to load game {game_id} from database: {e}")
            raise
        finally:
            db.close()
    
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
        
        # Save to database
        self._save_game_to_db(game_id, engine)
        
        # Cache in memory
        self._cache[game_id] = engine
        
        return game_id, engine
    
    def get_game(self, game_id: str) -> Optional[GameEngine]:
        """
        Get a game by ID.
        
        First checks in-memory cache, then loads from database if not found.
        
        Args:
            game_id: The game ID
            
        Returns:
            GameEngine instance or None if not found
        """
        # Check cache first
        if game_id in self._cache:
            return self._cache[game_id]
        
        # Load from database
        engine = self._load_game_from_db(game_id)
        
        # Cache if found
        if engine:
            self._cache[game_id] = engine
        
        return engine
    
    def update_game(self, game_id: str, engine: GameEngine) -> None:
        """
        Update a game in the database.
        
        This should be called after any game state changes to persist them.
        
        Args:
            game_id: Game ID
            engine: Updated GameEngine instance
        """
        # Update cache
        self._cache[game_id] = engine
        
        # Save to database
        self._save_game_to_db(game_id, engine)
        
        # If game just completed, save stats
        if engine.game_state.winner_id is not None:
            self._save_game_stats(game_id, engine)
    
    def delete_game(self, game_id: str) -> bool:
        """
        Delete a game.
        
        Args:
            game_id: The game ID
            
        Returns:
            True if deleted, False if not found
        """
        # Remove from cache
        if game_id in self._cache:
            del self._cache[game_id]
        
        # Remove from database
        if self.use_database:
            db = SessionLocal()
            try:
                game_model = db.query(GameModel).filter(GameModel.id == uuid.UUID(game_id)).first()
                if game_model:
                    db.delete(game_model)
                    db.commit()
                    logger.info(f"Deleted game {game_id} from database")
                    return True
                return False
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to delete game {game_id}: {e}")
                return False
            finally:
                db.close()
        
        return True
    
    def _calculate_game_stats(self, game_id: str, engine: GameEngine) -> dict:
        """
        Calculate game statistics from completed game.
        
        Args:
            game_id: Game ID
            engine: Completed GameEngine instance
            
        Returns:
            Dict with stats data ready for database
        """
        game_state = engine.game_state
        
        # Validate game is complete
        if game_state.winner_id is None:
            raise ValueError("Cannot calculate stats for incomplete game")
        
        # Determine winner and loser
        winner_id = game_state.winner_id
        loser_id = next(
            (pid for pid in game_state.players.keys() if pid != winner_id),
            None
        )
        
        if loser_id is None:
            raise ValueError("Could not determine loser")
        
        # Get player names (instead of IDs)
        winner_name = game_state.players[winner_id].name
        loser_name = game_state.players[loser_id].name
        
        # Count actions from play-by-play log
        winner_cards_played = 0
        winner_tussles = 0
        winner_direct_attacks = 0
        loser_cards_played = 0
        loser_tussles = 0
        loser_direct_attacks = 0
        
        for entry in game_state.play_by_play:
            player = entry.get('player', '')
            description = entry.get('description', '').lower()
            
            # Count cards played (look for "spent X CC to play")
            if 'spent' in description and 'cc to play' in description:
                if player == winner_id:
                    winner_cards_played += 1
                elif player == loser_id:
                    loser_cards_played += 1
            
            # Count tussles (look for "initiated tussle" or "tussle")
            if 'tussle' in description:
                if player == winner_id:
                    winner_tussles += 1
                elif player == loser_id:
                    loser_tussles += 1
            
            # Count direct attacks (look for "attacked directly" or "direct attack")
            if 'direct' in description and 'attack' in description:
                if player == winner_id:
                    winner_direct_attacks += 1
                elif player == loser_id:
                    loser_direct_attacks += 1
        
        return {
            'game_id': uuid.UUID(game_id),
            'winner_id': winner_name,
            'loser_id': loser_name,
            'total_turns': game_state.turn_number,
            'winner_cards_played': winner_cards_played,
            'winner_tussles_initiated': winner_tussles,
            'winner_direct_attacks': winner_direct_attacks,
            'loser_cards_played': loser_cards_played,
            'loser_tussles_initiated': loser_tussles,
            'loser_direct_attacks': loser_direct_attacks,
        }
    
    def _save_game_stats(self, game_id: str, engine: GameEngine) -> None:
        """
        Save game statistics to database.
        
        Also saves game playback and updates player stats via StatsService.
        
        Args:
            game_id: Game ID
            engine: Completed GameEngine instance
        """
        if not self.use_database:
            return
        
        game_state = engine.game_state
        stats_service = get_stats_service()
        
        # Extract player info
        player_ids = list(game_state.players.keys())
        player1_id = player_ids[0]
        player2_id = player_ids[1]
        player1 = game_state.players[player1_id]
        player2 = game_state.players[player2_id]
        
        # Reconstruct starting decks from current state
        # (hand + in_play + sleep_zone = all cards the player has)
        def get_deck_names(player: Player) -> list[str]:
            all_cards = player.hand + player.in_play + player.sleep_zone
            # Normalize Copy cards back to "Copy" for deck reconstruction
            # Copy cards change their name to "Copy of [Target]" when played
            deck_names = []
            for card in all_cards:
                if card.name.startswith("Copy of "):
                    deck_names.append("Copy")
                else:
                    deck_names.append(card.name)
            return deck_names
        
        starting_deck_p1 = get_deck_names(player1)
        starting_deck_p2 = get_deck_names(player2)
        
        # Calculate tussle stats from play-by-play
        # Note: The game engine logs tussles as "{player}'s {card} tussles {opponent}'s {card}"
        # We can count initiations but tussle wins are not explicitly logged
        p1_tussles = 0
        p1_tussles_won = 0
        p2_tussles = 0
        p2_tussles_won = 0
        
        for entry in game_state.play_by_play:
            description = entry.get('description', '').lower()
            player_name = entry.get('player', '')
            
            # Match tussle format: "{player}'s {card} tussles {opponent}'s {card}"
            if ' tussles ' in description:
                # Find which player initiated by checking whose name appears first
                if description.startswith(player1.name.lower()):
                    p1_tussles += 1
                elif description.startswith(player2.name.lower()):
                    p2_tussles += 1
            
            # Note: Tussle wins are not explicitly logged in play-by-play
            # We would need to infer from "is sleeped" entries following tussles
            # For now, tussles_won will remain 0 until we add explicit logging
        
        # Save game playback
        try:
            # Get game start time from database for accurate duration
            game_started_at = None
            if self.use_database:
                SessionLocal = get_session_local()
                db = SessionLocal()
                try:
                    game_model = db.query(GameModel).filter(GameModel.id == game_id).first()
                    if game_model:
                        game_started_at = game_model.created_at
                finally:
                    db.close()
            
            stats_service.record_game_playback(
                game_id=game_id,
                player1_id=player1_id,
                player1_name=player1.name,
                player2_id=player2_id,
                player2_name=player2.name,
                winner_id=game_state.winner_id,
                starting_deck_p1=starting_deck_p1,
                starting_deck_p2=starting_deck_p2,
                first_player_id=game_state.first_player_id,
                play_by_play=game_state.play_by_play,
                turn_count=game_state.turn_number,
                game_started_at=game_started_at,
            )
        except Exception as e:
            logger.error(f"Failed to save game playback: {e}")
        
        # Update player stats for both players
        winner_id = game_state.winner_id
        try:
            stats_service.update_player_stats(
                player_id=player1_id,
                display_name=player1.name,
                won=(winner_id == player1_id),
                cards_used=starting_deck_p1,
                tussles_initiated=p1_tussles,
                tussles_won=p1_tussles_won,
            )
            stats_service.update_player_stats(
                player_id=player2_id,
                display_name=player2.name,
                won=(winner_id == player2_id),
                cards_used=starting_deck_p2,
                tussles_initiated=p2_tussles,
                tussles_won=p2_tussles_won,
            )
        except Exception as e:
            logger.error(f"Failed to update player stats: {e}")
        
        # Save legacy game stats (GameStatsModel)
        db = SessionLocal()
        try:
            # Check if stats already exist (idempotent)
            existing_stats = db.query(GameStatsModel).filter(
                GameStatsModel.game_id == uuid.UUID(game_id)
            ).first()
            
            if existing_stats:
                logger.debug(f"Stats already exist for game {game_id}")
                return
            
            # Calculate stats
            stats_data = self._calculate_game_stats(game_id, engine)
            
            # Get game model to calculate duration
            game_model = db.query(GameModel).filter(
                GameModel.id == uuid.UUID(game_id)
            ).first()
            
            if game_model:
                duration = (game_model.updated_at - game_model.created_at).total_seconds()
                stats_data['duration_seconds'] = int(duration)
            
            # Create stats record
            stats_model = GameStatsModel(**stats_data)
            db.add(stats_model)
            db.commit()
            
            logger.info(
                f"Saved stats for game {game_id}: "
                f"Winner {stats_data['winner_id']} in {stats_data['total_turns']} turns"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save stats for game {game_id}: {e}")
            # Don't raise - stats are optional, game should still save
        finally:
            db.close()
    
    # ===== LOBBY SYSTEM METHODS =====
    
    def create_lobby(self, player1_id: str, player1_name: str) -> tuple[str, str]:
        """
        Create a new game lobby waiting for player 2.
        
        Args:
            player1_id: Google ID for player 1 (for stats tracking)
            player1_name: Display name for player 1
            
        Returns:
            Tuple of (game_id, game_code)
        """
        from api.game_codes import generate_unique_game_code
        
        if not self.use_database:
            raise ValueError("Lobby system requires database to be enabled")
        
        db = SessionLocal()
        try:
            # Generate unique game code
            game_code = generate_unique_game_code(db)
            
            # Generate game ID
            game_id = str(uuid.uuid4())
            
            # Create minimal game model (waiting for player 2)
            game_model = GameModel(
                id=uuid.UUID(game_id),
                player1_id=player1_id,  # Use actual Google ID
                player1_name=player1_name,
                player2_id=None,  # Will be set when player 2 joins
                player2_name=None,
                game_code=game_code,
                status="waiting_for_player",
                turn_number=0,
                active_player_id="",
                phase="",
                game_state={}  # Empty until game starts
            )
            
            db.add(game_model)
            db.commit()
            
            logger.info(f"Created lobby {game_id} with code {game_code}")
            
            return game_id, game_code
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create lobby: {e}")
            raise
        finally:
            db.close()
    
    def join_lobby(self, game_code: str, player2_id: str, player2_name: str) -> tuple[str, str, str]:
        """
        Join an existing lobby as player 2.
        
        Args:
            game_code: 6-character game code
            player2_id: Google ID for player 2 (for stats tracking)
            player2_name: Display name for player 2
            
        Returns:
            Tuple of (game_id, player1_id, player1_name)
            
        Raises:
            ValueError: If lobby not found or already full
        """
        from api.game_codes import find_game_by_code
        
        if not self.use_database:
            raise ValueError("Lobby system requires database to be enabled")
        
        db = SessionLocal()
        try:
            # Find game by code
            game_model = find_game_by_code(db, game_code)
            
            if not game_model:
                raise ValueError(f"Lobby with code {game_code} not found")
            
            if game_model.status != "waiting_for_player":
                raise ValueError(f"Lobby {game_code} is not accepting players")
            
            if game_model.player2_id is not None:
                raise ValueError(f"Lobby {game_code} is already full")
            
            # Add player 2 with actual Google ID
            game_model.player2_id = player2_id
            game_model.player2_name = player2_name
            game_model.status = "deck_selection"
            
            db.commit()
            
            logger.info(f"Player 2 joined lobby {game_model.id}: {player2_name} ({player2_id})")
            
            return str(game_model.id), game_model.player1_id, game_model.player1_name
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to join lobby: {e}")
            raise
        finally:
            db.close()
    
    def get_lobby_status(self, game_code: str) -> Optional[dict]:
        """
        Get the current status of a lobby.
        
        Args:
            game_code: 6-character game code
            
        Returns:
            Dict with lobby status or None if not found
        """
        from api.game_codes import find_game_by_code
        
        if not self.use_database:
            return None
        
        db = SessionLocal()
        try:
            game_model = find_game_by_code(db, game_code)
            
            if not game_model:
                return None
            
            return {
                "game_id": str(game_model.id),
                "game_code": game_model.game_code,
                "player1_id": game_model.player1_id,
                "player1_name": game_model.player1_name,
                "player2_id": game_model.player2_id,
                "player2_name": game_model.player2_name,
                "status": game_model.status,
                "ready_to_start": (
                    game_model.status == "active" and
                    game_model.player2_id is not None
                )
            }
        finally:
            db.close()
    
    def start_lobby_game(
        self, 
        game_code: str, 
        player_id: str, 
        deck: list[str]
    ) -> dict:
        """
        Submit deck selection for a lobby game.
        
        Args:
            game_code: 6-character game code
            player_id: Actual player ID (Google ID)
            deck: List of 6 card names
            
        Returns:
            Dict with game_id, ready status, and game_state if both players ready
            
        Raises:
            ValueError: If lobby not found or invalid state
        """
        from api.game_codes import find_game_by_code
        
        if not self.use_database:
            raise ValueError("Lobby system requires database to be enabled")
        
        db = SessionLocal()
        try:
            game_model = find_game_by_code(db, game_code)
            
            if not game_model:
                raise ValueError(f"Lobby with code {game_code} not found")
            
            if game_model.status not in ("deck_selection", "active"):
                raise ValueError(f"Lobby {game_code} is not in deck selection phase")
            
            # Store deck in game_state temporarily, keyed by actual player ID
            current_state = game_model.game_state or {}
            decks = current_state.get("decks", {})
            decks[player_id] = deck
            current_state["decks"] = decks
            
            # Check if both players have submitted decks using their actual IDs
            player1_id = game_model.player1_id
            player2_id = game_model.player2_id
            has_both_decks = player1_id in decks and player2_id in decks
            
            if has_both_decks and game_model.status == "deck_selection":
                # Start the game!
                logger.info(f"Both players ready, starting game {game_model.id}")
                
                # Create actual game state using real player IDs
                game_id, engine = self.create_game(
                    player1_id=player1_id,
                    player1_name=game_model.player1_name,
                    player1_deck=decks[player1_id],
                    player2_id=player2_id,
                    player2_name=game_model.player2_name,
                    player2_deck=decks[player2_id],
                )
                
                # Update the existing game model with new state
                game_state_dict = serialize_game_state(engine.game_state)
                metadata = extract_metadata(engine.game_state)
                
                game_model.game_state = game_state_dict
                game_model.status = "active"
                game_model.turn_number = metadata["turn_number"]
                game_model.active_player_id = metadata["active_player_id"]
                game_model.phase = metadata["phase"]
                
                db.commit()
                
                # Cache the engine
                self._cache[str(game_model.id)] = engine
                
                return {
                    "game_id": str(game_model.id),
                    "ready": True,
                    "first_player_id": engine.game_state.first_player_id,
                    "game_state": game_state_dict
                }
            else:
                # Save deck selection, wait for other player
                game_model.game_state = current_state
                db.commit()
                
                return {
                    "game_id": str(game_model.id),
                    "ready": False
                }
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to start lobby game: {e}")
            raise
        finally:
            db.close()
    
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
                effect_definitions=template.effect_definitions,
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
        """Get the number of active games in the database."""
        if not self.use_database:
            return len(self._cache)
        
        db = SessionLocal()
        try:
            count = db.query(GameModel).filter(GameModel.status == "active").count()
            return count
        finally:
            db.close()
    
    def generate_random_deck(self, num_toys: int, num_actions: int) -> list[str]:
        """
        Generate a random deck from the available cards.
        
        Args:
            num_toys: Number of Toy cards to include (0-6)
            num_actions: Number of Action cards to include (0-6)
            
        Returns:
            List of card names
            
        Raises:
            ValueError: If parameters are invalid or not enough cards available
        """
        # Validate parameters
        if num_toys < 0 or num_actions < 0:
            raise ValueError("Card counts must be non-negative")
        
        total_cards = num_toys + num_actions
        if total_cards != 6:
            raise ValueError(f"Total cards must equal 6, got {total_cards}")
        
        # Separate cards by type
        from game_engine.models.card import CardType
        import random
        
        toys = [card.name for card in self.all_cards if card.card_type == CardType.TOY]
        actions = [card.name for card in self.all_cards if card.card_type == CardType.ACTION]
        
        # Validate we have enough cards
        if len(toys) < num_toys:
            raise ValueError(f"Not enough Toy cards available: requested {num_toys}, have {len(toys)}")
        if len(actions) < num_actions:
            raise ValueError(f"Not enough Action cards available: requested {num_actions}, have {len(actions)}")
        
        # Randomly select cards
        selected_toys = random.sample(toys, num_toys) if num_toys > 0 else []
        selected_actions = random.sample(actions, num_actions) if num_actions > 0 else []
        
        # Combine and shuffle
        deck = selected_toys + selected_actions
        random.shuffle(deck)
        
        logger.info(f"Generated random deck: {num_toys} Toys, {num_actions} Actions - {deck}")
        
        return deck


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
