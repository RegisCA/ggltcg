"""
Simulation runner for executing AI vs AI games.

This module runs individual games between two AI players with configurable
models and deck compositions, tracking Charge usage per turn for analysis.
"""

import logging
import time
from copy import deepcopy
from typing import Optional
import uuid

from game_engine.game_engine import GameEngine
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Card, Zone
from game_engine.data.card_loader import load_cards_dict
from game_engine.ai.llm_player import LLMPlayer
from game_engine.ai.turn_planner import TurnPlanner
from game_engine.validation.action_validator import ActionValidator
from api.schemas import ValidAction

from .config import (
    DeckConfig,
    GameResult,
    GameOutcome,
    TurnCharge,
)
from .rate_limiter import BudgetExhaustedError

logger = logging.getLogger(__name__)


class SimulationRunner:
    """
    Runs individual AI vs AI games for simulation.

    This class handles:
    - Game state initialization with specified decks
    - AI player instantiation with configurable models
    - Turn execution with Charge tracking
    - Game completion detection and result generation
    """

    def __init__(
        self,
        player1_model: str = "gemini-2.5-flash-lite",
        player2_model: str = "gemini-2.5-flash-lite",
        max_turns: int = 20,
        log_level: str = "WARNING",
        rate_limiter: Optional[object] = None,
    ):
        """
        Initialize the simulation runner.

        Args:
            player1_model: Gemini model for player 1
            player2_model: Gemini model for player 2
            max_turns: Maximum turns before declaring draw
            log_level: Logging level for simulation-related loggers (default: WARNING)
            rate_limiter: Optional rate/budget limiter forwarded to both AI
                players' Gemini provider. Defaults to a no-op limiter (no
                behavior change).
        """
        self.player1_model = player1_model
        self.player2_model = player2_model
        self.max_turns = max_turns
        self.rate_limiter = rate_limiter

        # Configure logging for simulation
        self._configure_simulation_logging(log_level)

        # Load all card templates
        self.card_templates = load_cards_dict()

        # AI players will be created per-game
        self._player1_ai: Optional[LLMPlayer] = None
        self._player2_ai: Optional[LLMPlayer] = None
    
    def run_game(
        self,
        deck1: DeckConfig,
        deck2: DeckConfig,
        game_number: int = 1,
    ) -> GameResult:
        """
        Run a single game between two decks.
        
        Args:
            deck1: Deck configuration for player 1
            deck2: Deck configuration for player 2
            game_number: Game number within the simulation run
            
        Returns:
            GameResult with outcome, turn count, Charge tracking, and action log
        """
        start_time = time.time()
        charge_tracking: list[TurnCharge] = []
        action_log: list[dict] = []
        error_message: Optional[str] = None
        game_initialized = False  # Track successful game initialization

        TurnPlanner.reset_metrics()

        try:
            # Create game state
            game_state = self._create_game_state(deck1, deck2)
            engine = GameEngine(game_state)

            # Create AI players with specified models (enum-based turn planning)
            self._player1_ai = LLMPlayer(model=self.player1_model, rate_limiter=self.rate_limiter)
            self._player2_ai = LLMPlayer(model=self.player2_model, rate_limiter=self.rate_limiter)

            logger.info(
                f"Starting game {game_number}: {deck1.name} ({self.player1_model}) vs "
                f"{deck2.name} ({self.player2_model})"
            )
            
            # Start first turn
            engine.start_turn()
            
            # Main game loop
            while game_state.winner_id is None:
                # Check turn limit
                if game_state.turn_number > self.max_turns:
                    logger.warning(
                        f"Game {game_number} hit turn limit ({self.max_turns} turns)"
                    )
                    break
                
                # Capture turn info at START of turn (before any state changes)
                current_turn = game_state.turn_number
                current_player_id = game_state.active_player_id
                active_player = game_state.get_active_player()
                inactive_player_id = "player2" if current_player_id == "player1" else "player1"
                inactive_player = game_state.players[inactive_player_id]
                
                # Charge tracking - capture BOTH players' Charge after start_turn
                active_charge_start = active_player.charge
                inactive_charge_start = inactive_player.charge
                active_charge_spent = 0
                inactive_charge_end_of_turn = inactive_charge_start  # Initialize in case loop doesn't run
                
                # Determine which AI is playing
                if current_player_id == "player1":
                    ai_player = self._player1_ai
                else:
                    ai_player = self._player2_ai
                
                # Execute turn actions
                turn_actions = 0
                max_actions_per_turn = 50  # Safety limit
                
                while turn_actions < max_actions_per_turn:
                    turn_actions += 1
                    
                    # Get valid actions
                    validator = ActionValidator(engine)
                    valid_actions = validator.get_valid_actions(
                        current_player_id,
                        filter_for_ai=True
                    )
                    
                    if not valid_actions:
                        logger.error(f"No valid actions for {current_player_id}")
                        break
                    
                    # If only end turn available, take it
                    if len(valid_actions) == 1 and valid_actions[0].action_type == "end_turn":
                        self._execute_end_turn(engine, game_state)
                        break
                    
                    # AI selects action
                    result = ai_player.select_action(
                        game_state,
                        current_player_id,
                        valid_actions,
                        engine
                    )
                    
                    if result is None:
                        # AI failed to select, end turn
                        logger.warning(f"AI failed to select action, ending turn")
                        self._execute_end_turn(engine, game_state)
                        break
                    
                    action_index, reasoning = result
                    selected_action = valid_actions[action_index]
                    
                    # Log action with full description
                    action_entry = {
                        "turn": current_turn,
                        "player": current_player_id,
                        "action": selected_action.action_type,
                        "card": selected_action.card_name,
                        "description": selected_action.description,
                        "reasoning": reasoning,
                    }
                    action_log.append(action_entry)
                    
                    # Execute action
                    charge_before = active_player.charge
                    inactive_charge_before_action = inactive_player.charge
                    action_ended_turn = self._execute_action(
                        engine, game_state, ai_player, selected_action
                    )
                    charge_after = active_player.charge
                    active_charge_spent += max(0, charge_before - charge_after)

                    # Capture inactive player's Charge BEFORE end_turn gives them their turn-start Charge
                    # (end_turn internally calls start_turn for the next player)
                    if action_ended_turn:
                        # Use the Charge value right before end_turn was processed
                        inactive_charge_end_of_turn = inactive_charge_before_action
                        break

                    # Check victory after each action
                    engine.check_state_based_actions()
                    if game_state.winner_id is not None:
                        break
                else:
                    # Loop ended without break - no end_turn action was taken
                    inactive_charge_end_of_turn = inactive_player.charge

                # Track Charge for BOTH players at end of this turn
                active_charge_end = active_player.charge

                # Active player: gained = end - start + spent (clamped at 0)
                active_charge_gained = max(0, active_charge_end - active_charge_start + active_charge_spent)

                # Inactive player: may have gained Charge from effects (e.g., Umbruh broken)
                # They don't spend Charge during opponent's turn, so gained = end - start
                # Use inactive_charge_end_of_turn which was captured BEFORE end_turn/start_turn
                inactive_charge_gained = max(0, inactive_charge_end_of_turn - inactive_charge_start)

                # Record active player's turn
                charge_tracking.append(TurnCharge(
                    turn=current_turn,
                    player_id=current_player_id,
                    charge_start=active_charge_start,
                    charge_gained=active_charge_gained,
                    charge_spent=active_charge_spent,
                    charge_end=active_charge_end,
                ))

                # Record inactive player's Charge changes during this turn (if any)
                if inactive_charge_gained > 0:
                    charge_tracking.append(TurnCharge(
                        turn=current_turn,
                        player_id=inactive_player_id,
                        charge_start=inactive_charge_start,
                        charge_gained=inactive_charge_gained,
                        charge_spent=0,  # Inactive player can't spend during opponent's turn
                        charge_end=inactive_charge_end_of_turn,
                    ))
                
                # If turn didn't end from action, check state
                if game_state.winner_id is None:
                    engine.check_state_based_actions()
            
            # Mark successful initialization
            game_initialized = True

        except BudgetExhaustedError:
            raise

        except Exception as e:
            logger.exception(f"Error in game {game_number}: {e}")
            error_message = str(e)
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Determine outcome
        outcome: GameOutcome
        winner_deck: Optional[str] = None
        
        if error_message:
            # Game errored - treat as draw
            outcome = GameOutcome.DRAW
            turn_count = game_state.turn_number if game_initialized else 0
        elif not game_initialized or game_state.winner_id is None:
            # Hit turn limit or other issue - draw
            outcome = GameOutcome.DRAW
            turn_count = self.max_turns
        else:
            turn_count = game_state.turn_number
            if game_state.winner_id == "player1":
                outcome = GameOutcome.PLAYER1_WIN
                winner_deck = deck1.name
            else:
                outcome = GameOutcome.PLAYER2_WIN
                winner_deck = deck2.name
        
        logger.info(
            f"Game {game_number} completed: {outcome.value} in {turn_count} turns "
            f"({duration_ms}ms)"
        )
        
        planner_metrics = TurnPlanner.get_metrics()
        no_sequences_count = planner_metrics.get("no_sequences", 0)
        logger.debug(
            f"Planner metrics: success={planner_metrics.get('success', 0)}, "
            f"no_sequences={no_sequences_count}, "
            f"no_sequences_rate={planner_metrics.get('no_sequences_rate', 'N/A')}"
        )

        return GameResult(
            game_number=game_number,
            deck1_name=deck1.name,
            deck2_name=deck2.name,
            player1_model=self.player1_model,
            player2_model=self.player2_model,
            outcome=outcome,
            winner_deck=winner_deck,
            turn_count=turn_count,
            duration_ms=duration_ms,
            charge_tracking=charge_tracking,
            action_log=action_log,
            error_message=error_message,
            no_sequences_count=no_sequences_count,
        )
    
    def _create_game_state(
        self,
        deck1: DeckConfig,
        deck2: DeckConfig,
    ) -> GameState:
        """
        Create a game state with the specified decks.
        
        Args:
            deck1: Deck for player 1
            deck2: Deck for player 2
            
        Returns:
            Initialized GameState
        """
        # Create player 1's cards
        p1_cards = []
        for card_name in deck1.cards:
            template = self.card_templates.get(card_name)
            if template is None:
                raise ValueError(f"Card not found in templates: {card_name}")
            card = deepcopy(template)
            card.id = str(uuid.uuid4())  # Unique ID for this instance
            card.owner = "player1"
            card.controller = "player1"
            card.zone = Zone.HAND
            p1_cards.append(card)
        
        # Create player 2's cards
        p2_cards = []
        for card_name in deck2.cards:
            template = self.card_templates.get(card_name)
            if template is None:
                raise ValueError(f"Card not found in templates: {card_name}")
            card = deepcopy(template)
            card.id = str(uuid.uuid4())
            card.owner = "player2"
            card.controller = "player2"
            card.zone = Zone.HAND
            p2_cards.append(card)
        
        # Create players
        player1 = Player(
            player_id="player1",
            name=f"{deck1.name} (P1)",
            hand=p1_cards,
        )
        
        player2 = Player(
            player_id="player2",
            name=f"{deck2.name} (P2)",
            hand=p2_cards,
        )
        
        # Create game state with player1 going first
        game_state = GameState(
            game_id=f"sim-{uuid.uuid4()}",
            players={"player1": player1, "player2": player2},
            active_player_id="player1",
            first_player_id="player1",
            turn_number=1,
            phase=Phase.START,
            starting_decks={
                "player1": [c.name for c in p1_cards],
                "player2": [c.name for c in p2_cards],
            },
        )
        
        return game_state
    
    def _execute_action(
        self,
        engine: GameEngine,
        game_state: GameState,
        ai_player: LLMPlayer,
        action: ValidAction,
    ) -> bool:
        """
        Execute a single action.
        
        Args:
            engine: Game engine
            game_state: Current game state
            ai_player: AI player (for getting action details)
            action: Action to execute
            
        Returns:
            True if the action ended the turn
        """
        player = game_state.get_active_player()
        
        if action.action_type == "end_turn":
            self._execute_end_turn(engine, game_state)
            return True
        
        elif action.action_type == "play_card":
            card = next(
                (c for c in player.hand if c.id == action.card_id),
                None
            )
            if card:
                # Get target and alternative cost from AI
                details = ai_player.get_action_details(action)
                target_ids = details.get("target_ids") or []
                alt_cost_card_id = details.get("alternative_cost_card_id")
                
                # Handle alternative cost
                if alt_cost_card_id:
                    alt_card = self._find_card_by_id(player, alt_cost_card_id)
                    if alt_card:
                        engine.play_card(
                            player, card,
                            alternative_cost_card=alt_card,
                            target_ids=target_ids
                        )
                    else:
                        engine.play_card(player, card, target_ids=target_ids)
                else:
                    engine.play_card(player, card, target_ids=target_ids)
        
        elif action.action_type == "tussle":
            attacker = next(
                (c for c in player.in_play if c.id == action.card_id),
                None
            )
            if attacker:
                # Get target from AI
                details = ai_player.get_action_details(action)
                defender_id = details.get("defender_id")
                
                defender = None
                if defender_id and defender_id != "direct_attack":
                    opponent = game_state.get_opponent(player.player_id)
                    defender = next(
                        (c for c in opponent.in_play if c.id == defender_id),
                        None
                    )
                
                engine.initiate_tussle(attacker, defender, player)
        
        elif action.action_type == "activate_ability":
            card = next(
                (c for c in player.in_play if c.id == action.card_id),
                None
            )
            if card:
                details = ai_player.get_action_details(action)
                target_ids = details.get("target_ids") or []
                
                # Get the activated effect from the card
                from game_engine.rules.effects import EffectRegistry
                from game_engine.rules.effects.base_effect import ActivatedEffect
                
                effects = EffectRegistry.get_effects(card)
                activated_effect = None
                for effect in effects:
                    if isinstance(effect, ActivatedEffect):
                        activated_effect = effect
                        break
                
                if activated_effect:
                    # Find target card if specified
                    target_card = None
                    if target_ids:
                        all_cards = game_state.get_all_cards_in_play()
                        for c in all_cards:
                            if c.id == target_ids[0]:
                                target_card = c
                                break
                    
                    # Pay the cost (default amount is 1)
                    amount = 1
                    cost = activated_effect.cost_charge * amount
                    if player.charge >= cost:
                        player.spend_charge(cost)
                        
                        # Apply the ability
                        activated_effect.apply(
                            game_state,
                            target=target_card,
                            amount=amount,
                            game_engine=engine
                        )
        
        return False
    
    def _configure_simulation_logging(self, log_level: str) -> None:
        """
        Configure logging levels for simulation-related modules.
        
        This suppresses DEBUG logs from game engine internals while preserving
        ERROR and WARNING messages.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        # Convert string to logging level
        numeric_level = getattr(logging, log_level.upper(), logging.WARNING)
        
        # Configure loggers for modules that generate verbose output during simulation
        logger_names = [
            "game_engine",
            "game_engine.ai",
            "game_engine.ai.turn_planner",
            "game_engine.ai.llm_player",
            "game_engine.game_engine",
            "simulation",
        ]
        
        for logger_name in logger_names:
            logging.getLogger(logger_name).setLevel(numeric_level)
    
    def _execute_end_turn(self, engine: GameEngine, game_state: GameState) -> None:
        """End the current turn and start the next.
        
        Note: engine.end_turn() already handles switching players, 
        incrementing turn number, and calling start_turn() internally.
        """
        engine.end_turn()
        
        # Check victory condition
        engine.check_state_based_actions()
        # Note: We removed the redundant engine.start_turn() call here
        # because engine.end_turn() already calls it internally
    
    def _find_card_by_id(self, player: Player, card_id: str) -> Optional[Card]:
        """Find a card in player's hand or in-play by ID."""
        for card in player.hand:
            if card.id == card_id:
                return card
        for card in player.in_play:
            if card.id == card_id:
                return card
        return None
