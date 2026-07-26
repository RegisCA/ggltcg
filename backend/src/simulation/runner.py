"""
Simulation runner for executing AI vs AI games.

This module runs individual games between two AI players with configurable
models and deck compositions, tracking Charge usage per turn for analysis.
"""

import logging
import random
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
from game_engine.validation.action_executor import ActionExecutor
from api.schemas import ValidAction

from .config import (
    DeckConfig,
    GameResult,
    GameOutcome,
    TurnCharge,
    default_simulation_model,
)
from game_engine.ai.rate_limiter import BudgetExhaustedError

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
        player1_model: Optional[str] = None,
        player2_model: Optional[str] = None,
        max_turns: int = 20,
        log_level: str = "WARNING",
        rate_limiter: Optional[object] = None,
        player1_policy: Optional[str] = None,
        player2_policy: Optional[str] = None,
        policy_max_actions: Optional[int] = None,
        policy_max_sequences: Optional[int] = None,
    ):
        """
        Initialize the simulation runner.

        Args:
            player1_model: Gemini model for player 1 (default: GEMINI_MODEL
                env var, then the provider default — same as live games)
            player2_model: Gemini model for player 2 (same default)
            max_turns: Maximum turns before declaring draw
            log_level: Logging level for simulation-related loggers (default: WARNING)
            rate_limiter: Optional rate/budget limiter forwarded to both AI
                players' Gemini provider. Defaults to a no-op limiter (no
                behavior change).
            player1_policy: If set, player 1 is a ``ScriptedPlayer`` running this
                selection policy instead of an ``LLMPlayer`` — no API calls, no
                key required. See ``simulation.policies``.
            player2_policy: Same, for player 2. The two are independent so a
                policy can be benchmarked against another one.
            policy_max_actions: Enumerator action ceiling for scripted players.
                None keeps the engine default (8), which is what live games use.
                Combo analysis raises it because real turns run longer, and a turn
                that is never enumerated can never be played.
            policy_max_sequences: Enumerator sequence ceiling, same convention.
        """
        self.player1_model = player1_model or default_simulation_model()
        self.player2_model = player2_model or default_simulation_model()
        self.max_turns = max_turns
        self.rate_limiter = rate_limiter
        self.player1_policy = player1_policy
        self.player2_policy = player2_policy
        self.policy_max_actions = policy_max_actions
        self.policy_max_sequences = policy_max_sequences

        # Actions the engine refused (insufficient Charge, invalid target).
        # ActionExecutor reports these via ExecutionResult.success rather than
        # raising, so without an explicit counter a rejected action leaves no
        # trace at all — no log (workers disable logging), no row, no column.
        # That is the same silent-failure mode the ActionExecutor fix removed.
        self.rejected_actions = 0

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
        seed: Optional[int] = None,
    ) -> GameResult:
        """
        Run a single game between two decks.

        Args:
            deck1: Deck configuration for player 1
            deck2: Deck configuration for player 2
            game_number: Game number within the simulation run
            seed: Seeds both the scripted players' RNGs and the engine's global
                ``random`` (direct attack picks a random card from the defender's
                hand — the only nondeterminism in the engine). Pass and record a
                distinct seed per game to make a run exactly replayable.

                Note this reseeds the *process-global* ``random``, so concurrent
                calls within one process would interleave streams and break
                replay. Sweep workers are single-threaded, which is what makes it
                safe; parallelism comes from processes, not threads.

        Returns:
            GameResult with outcome, turn count, Charge tracking, and action log
        """
        if seed is not None:
            random.seed(seed)
        self.rejected_actions = 0  # per-game: workers reuse one runner
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
            self._player1_ai = self._make_player(1, seed)
            self._player2_ai = self._make_player(2, seed)

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
                        logger.warning("AI failed to select action, ending turn")
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
    
    def _note_rejection(self, result, what: str) -> None:
        """Record an action the engine declined.

        ``ActionExecutor`` signals "legal-looking but refused" (not enough Charge,
        target no longer valid) through ``ExecutionResult.success``, not an
        exception. Dropping that return value on the floor is how a sweep ends up
        reporting clean runs while quietly playing fewer actions than it planned.
        """
        if result is not None and not getattr(result, "success", True):
            self.rejected_actions += 1
            logger.warning("%s rejected: %s", what, getattr(result, "message", ""))

    def _make_player(self, seat: int, seed: Optional[int]):
        """Build the AI for one seat: scripted if a policy was configured, else LLM."""
        policy = self.player1_policy if seat == 1 else self.player2_policy
        if policy is None:
            model = self.player1_model if seat == 1 else self.player2_model
            return LLMPlayer(model=model, rate_limiter=self.rate_limiter)

        from .scripted_player import ScriptedPlayer

        # Offset per seat so the two players don't draw an identical stream in a
        # mirror match, which would correlate their choices under random policies.
        player_seed = 0 if seed is None else seed * 2 + seat
        return ScriptedPlayer(
            policy=policy,
            seed=player_seed,
            max_actions=self.policy_max_actions,
            max_sequences=self.policy_max_sequences,
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

        # play_card and tussle go through ActionExecutor, which is what
        # api/routes_actions.py uses for live games AND what the enumerator uses
        # to build plans. Calling engine.play_card/initiate_tussle directly here
        # skipped ActionExecutor._handle_targets, so every targeted effect (Copy,
        # Glue, Stomp, Drop, Twist, Sun, Jumpscare...) silently resolved with no
        # target: the card was paid for, did nothing, and went to the break zone.
        # That made plans built by the enumerator undeliverable — the desync that
        # showed up as "LLM execution fallbacks" in scripted sweeps.
        executor = ActionExecutor(engine)

        if action.action_type == "play_card":
            details = ai_player.get_action_details(action)
            try:
                result = executor.execute_play_card(
                    player.player_id,
                    action.card_id,
                    target_card_ids=details.get("target_ids") or None,
                    alternative_cost_card_id=details.get("alternative_cost_card_id"),
                )
                self._note_rejection(result, "play_card")
            except ValueError as e:
                self.rejected_actions += 1
                logger.warning(f"play_card raised: {e}")

        elif action.action_type == "tussle":
            details = ai_player.get_action_details(action)
            defender_id = details.get("defender_id")
            if defender_id == "direct_attack":
                defender_id = None
            try:
                result = executor.execute_tussle(
                    player.player_id, action.card_id, defender_id=defender_id
                )
                self._note_rejection(result, "tussle")
            except ValueError as e:
                self.rejected_actions += 1
                logger.warning(f"tussle raised: {e}")

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
