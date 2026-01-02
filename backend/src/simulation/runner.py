"""
Simulation runner for executing AI vs AI games.

This module runs individual games between two AI players with configurable
models and deck compositions, tracking CC usage per turn for analysis.
"""

import logging
import os
import time
from copy import deepcopy
from typing import Optional
import uuid

from game_engine.game_engine import GameEngine
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Card, Zone
from game_engine.data.card_loader import load_cards_dict
from game_engine.ai.llm_player import LLMPlayer, LLMPlayerV3
from game_engine.ai.turn_planner import TurnPlanner
from game_engine.validation.action_validator import ActionValidator
from api.schemas import ValidAction

from .config import (
    DeckConfig,
    GameResult,
    GameOutcome,
    TurnCC,
)

logger = logging.getLogger(__name__)


class SimulationRunner:
    """
    Runs individual AI vs AI games for simulation.
    
    This class handles:
    - Game state initialization with specified decks
    - AI player instantiation with configurable models
    - Turn execution with CC tracking
    - Game completion detection and result generation
    """
    
    def __init__(
        self,
        player1_model: str = "gemini-2.0-flash",
        player2_model: str = "gemini-2.5-flash",
        max_turns: int = 40,
    ):
        """
        Initialize the simulation runner.
        
        Args:
            player1_model: Gemini model for player 1
            player2_model: Gemini model for player 2
            max_turns: Maximum turns before declaring draw
        """
        self.player1_model = player1_model
        self.player2_model = player2_model
        self.max_turns = max_turns
        
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
            GameResult with outcome, turn count, CC tracking, and action log
        """
        start_time = time.time()
        cc_tracking: list[TurnCC] = []
        action_log: list[dict] = []
        error_message: Optional[str] = None
        game_initialized = False  # Track successful game initialization
        
        # Get AI version and reset V4 metrics if using V4
        ai_version = os.getenv("AI_VERSION", "3")
        if ai_version == "4":
            TurnPlanner.reset_v4_metrics()
        
        try:
            # Create game state
            game_state = self._create_game_state(deck1, deck2)
            engine = GameEngine(game_state)
            
            # Create AI players with specified models
            # Use LLMPlayerV3 for AI versions 3 and 4 (turn planning)
            PlayerClass = LLMPlayerV3 if ai_version in ("3", "4") else LLMPlayer
            self._player1_ai = PlayerClass(provider="gemini", model=self.player1_model)
            self._player2_ai = PlayerClass(provider="gemini", model=self.player2_model)
            
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
                
                # CC tracking - capture BOTH players' CC after start_turn
                active_cc_start = active_player.cc
                inactive_cc_start = inactive_player.cc
                active_cc_spent = 0
                inactive_cc_end_of_turn = inactive_cc_start  # Initialize in case loop doesn't run
                
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
                    cc_before = active_player.cc
                    inactive_cc_before_action = inactive_player.cc
                    action_ended_turn = self._execute_action(
                        engine, game_state, ai_player, selected_action
                    )
                    cc_after = active_player.cc
                    active_cc_spent += max(0, cc_before - cc_after)
                    
                    # Capture inactive player's CC BEFORE end_turn gives them their turn-start CC
                    # (end_turn internally calls start_turn for the next player)
                    if action_ended_turn:
                        # Use the CC value right before end_turn was processed
                        inactive_cc_end_of_turn = inactive_cc_before_action
                        break
                    
                    # Check victory after each action
                    engine.check_state_based_actions()
                    if game_state.winner_id is not None:
                        break
                else:
                    # Loop ended without break - no end_turn action was taken
                    inactive_cc_end_of_turn = inactive_player.cc
                
                # Track CC for BOTH players at end of this turn
                active_cc_end = active_player.cc
                
                # Active player: gained = end - start + spent (clamped at 0)
                active_cc_gained = max(0, active_cc_end - active_cc_start + active_cc_spent)
                
                # Inactive player: may have gained CC from effects (e.g., Umbruh sleeped)
                # They don't spend CC during opponent's turn, so gained = end - start
                # Use inactive_cc_end_of_turn which was captured BEFORE end_turn/start_turn
                inactive_cc_gained = max(0, inactive_cc_end_of_turn - inactive_cc_start)
                
                # Record active player's turn
                cc_tracking.append(TurnCC(
                    turn=current_turn,
                    player_id=current_player_id,
                    cc_start=active_cc_start,
                    cc_gained=active_cc_gained,
                    cc_spent=active_cc_spent,
                    cc_end=active_cc_end,
                ))
                
                # Record inactive player's CC changes during this turn (if any)
                if inactive_cc_gained > 0:
                    cc_tracking.append(TurnCC(
                        turn=current_turn,
                        player_id=inactive_player_id,
                        cc_start=inactive_cc_start,
                        cc_gained=inactive_cc_gained,
                        cc_spent=0,  # Inactive player can't spend during opponent's turn
                        cc_end=inactive_cc_end_of_turn,
                    ))
                
                # If turn didn't end from action, check state
                if game_state.winner_id is None:
                    engine.check_state_based_actions()
            
            # Mark successful initialization
            game_initialized = True
        
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
        
        # Capture V4 metrics if using V4
        v2_fallback_count = 0
        illegal_action_count = 0
        if ai_version == "4":
            v4_metrics = TurnPlanner.get_v4_metrics()
            v2_fallback_count = v4_metrics.get("v2_fallback", 0)
            illegal_action_count = v4_metrics.get("validation_rejections", 0)
            logger.info(
                f"V4 Metrics: v4_success={v4_metrics.get('v4_success', 0)}, "
                f"v2_fallback={v2_fallback_count}, "
                f"fallback_rate={v4_metrics.get('v2_fallback_rate', 'N/A')}"
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
            cc_tracking=cc_tracking,
            action_log=action_log,
            error_message=error_message,
            v2_fallback_count=v2_fallback_count,
            illegal_action_count=illegal_action_count,
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
                
                # Find the activated ability by name
                if action.ability_name:
                    engine.activate_ability(
                        player, card, action.ability_name,
                        target_ids=target_ids
                    )
        
        return False
    
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
