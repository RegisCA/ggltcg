"""
Turn Plan Validators

Validates AI turn plans for multi-step reasoning errors that the game engine
doesn't catch. Each validator focuses on a specific class of planning errors.

Architecture Philosophy:
- Game Engine: Validates individual actions (turn, phase, Charge, zones, targets)
- These Validators: Validate action sequences (Charge budgeting, mid-plan state, dependencies)
"""

import logging
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from game_engine.ai.prompts import TurnPlan
    from game_engine.models.game_state import GameState

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """A single validation error in a turn plan."""
    action_index: int  # 0-based index of the action that caused the error
    error_type: str  # "charge_budget", "opponent_toys", "suicide_attack", "dependency"
    message: str  # Human-readable error message
    
    def to_llm_feedback(self) -> str:
        """Format error for LLM retry feedback."""
        return f"[Action {self.action_index + 1}] {self.message}"


class ChargeBudgetValidator:
    """
    Validates that the turn plan doesn't exceed the Charge budget.

    The game engine validates individual actions, but the AI must budget
    Charge across the entire sequence, accounting for Charge gains from cards like:
    - Surge: +1 Charge when played
    - Rush: +2 Charge when played
    - Umbruh: +1 Charge when broken (not modeled — happens off the active turn)
    - Belchaletta: +2 Charge at start of turn (continuous effect, not modeled here)
    """

    # Cards that gain Charge when played (mirrors TurnPlanner._CHARGE_GAIN_ON_PLAY).
    # Keys MUST be real card names whose CSV effect is a play-triggered `gain_charge:`
    # — pinned by tests/test_cc_gain_tables.py. Charge gains from other triggers
    # (start-of-turn, when-broken, on-card-played) are intentionally NOT modeled.
    CHARGE_GAIN_ON_PLAY = {
        "Surge": 1,
        "Rush": 2,
        "Cake": 5,
    }

    # Canonical Charge cost for non-play_card actions (fixed by game rules).
    # Use these instead of the LLM's stated charge_cost so charge_budget validation
    # is correct even when the LLM hallucinates a wrong value.
    CANONICAL_ACTION_COSTS = {"direct_attack": 2, "tussle": 2}

    def validate(self, plan: "TurnPlan", starting_charge: int) -> List[ValidationError]:
        """
        Validate Charge budget across the entire action sequence.

        Args:
            plan: The turn plan to validate
            starting_charge: Charge at the start of the turn

        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []
        charge_remaining = starting_charge

        for i, action in enumerate(plan.action_sequence):
            # Track Charge gains from playing cards
            charge_gain = 0

            if action.action_type == "play_card" and action.card_name:
                # Direct Charge gain from playing the card (Surge/Rush)
                charge_gain += self.CHARGE_GAIN_ON_PLAY.get(action.card_name, 0)

            # Apply Charge gains first
            charge_remaining += charge_gain

            # Check if we can afford this action.
            # Use the canonical cost for actions with a fixed game-rule price;
            # fall back to the LLM's stated charge_cost for variable-cost actions (play_card).
            canonical = self.CANONICAL_ACTION_COSTS.get(action.action_type)
            action_cost = canonical if canonical is not None else (action.charge_cost or 0)

            if action_cost > charge_remaining:
                errors.append(ValidationError(
                    action_index=i,
                    error_type="charge_budget",
                    message=f"Cannot afford {action.card_name or action.action_type} "
                           f"(need {action_cost} Charge, have {charge_remaining} Charge)"
                ))

            # Deduct cost
            charge_remaining -= action_cost

            # Check for negative Charge
            if charge_remaining < 0:
                errors.append(ValidationError(
                    action_index=i,
                    error_type="charge_budget",
                    message=f"Charge went negative ({charge_remaining} Charge) after {action.card_name or action.action_type}"
                ))
                # Stop checking - plan is fundamentally broken
                break

        return errors


class OpponentToyTracker:
    """
    Tracks opponent toys remaining during plan execution.

    Prevents "direct attack while opponent has toys" errors by simulating
    which toys get broken by tussles/effects during the plan.
    
    Critical Rule: Direct attacks require EXACTLY 0 opponent toys in play.
    Even 0-STR toys like Archer block direct attacks.
    """
    
    def validate(
        self,
        plan: "TurnPlan",
        game_state: "GameState",
        player_id: str
    ) -> List[ValidationError]:
        """
        Validate direct attacks happen only when opponent has 0 toys.
        
        Args:
            plan: The turn plan to validate
            game_state: Current game state
            player_id: AI player's ID
            
        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []
        player = game_state.players[player_id]
        opponent = game_state.get_opponent(player_id)

        # Track which opponent toys are still in play
        toys_remaining = {card.id for card in opponent.in_play}

        # Track which of the AI's own toys are in play (for direct_attack validation).
        # Only toys (is_toy()) with STR > 0 can attack; action cards never enter play.
        player_toys_in_play = {
            card.id
            for card in player.in_play
            if card.is_toy() and card.get_effective_strength() > 0
        }

        for i, action in enumerate(plan.action_sequence):
            # Remove toys that get broken / track toys entering play
            if action.action_type == "tussle" and action.target_ids:
                # Tussle breaks the target (assuming it dies - we check this in SuicideAttackValidator)
                # Note: This is a simplification - the target might survive
                # But the AI should plan tussles that kill the target
                target_id = action.target_ids[0]
                if target_id in toys_remaining:
                    toys_remaining.discard(target_id)
            
            elif action.action_type == "play_card":
                # Track toys the AI is playing into its own field
                if action.card_id:
                    for card in player.hand:
                        if card.id == action.card_id and card.is_toy() and card.get_effective_strength() > 0:
                            player_toys_in_play.add(card.id)
                            break

                # Some cards break opponent toys
                if action.card_name == "Drop" and action.target_ids:
                    # Drop breaks a target toy
                    for target_id in action.target_ids:
                        toys_remaining.discard(target_id)

                elif action.card_name == "Twist" and action.target_ids:
                    # Twist returns target to hand (not in play)
                    for target_id in action.target_ids:
                        toys_remaining.discard(target_id)

                elif action.card_name == "Clean":
                    # Clean breaks all toys
                    toys_remaining.clear()

            elif action.action_type == "activate_ability":
                # Archer's ability breaks a target
                if action.card_name == "Archer" and action.target_ids:
                    for target_id in action.target_ids:
                        toys_remaining.discard(target_id)
            
            # Check direct attacks
            if action.action_type == "direct_attack":
                if len(toys_remaining) > 0:
                    errors.append(ValidationError(
                        action_index=i,
                        error_type="opponent_toys",
                        message=f"Cannot direct attack: opponent still has {len(toys_remaining)} toy(s) in play"
                    ))
                if not player_toys_in_play:
                    errors.append(ValidationError(
                        action_index=i,
                        error_type="no_attacker",
                        message=(
                            "Cannot direct attack: you have no toys with STR > 0 in play. "
                            "Action cards (Rush, Surge) do not enter play — play a toy first."
                        )
                    ))
                elif action.card_id and action.card_id not in player_toys_in_play:
                    # Specified attacker is not a valid toy in play (e.g. an action card UUID)
                    errors.append(ValidationError(
                        action_index=i,
                        error_type="invalid_attacker",
                        message=(
                            f"Cannot direct attack with {action.card_name or action.card_id}: "
                            f"that card is not a toy currently in your In Play zone. "
                            f"Action cards (Rush, Surge) resolve immediately and do not enter play."
                        )
                    ))

            # Same attacker-validity check for tussle
            if action.action_type == "tussle" and action.card_id:
                if action.card_id not in player_toys_in_play:
                    errors.append(ValidationError(
                        action_index=i,
                        error_type="invalid_attacker",
                        message=(
                            f"Cannot tussle with {action.card_name or action.card_id}: "
                            f"that card is not a toy currently in your In Play zone. "
                            f"Play the toy first, then tussle with it."
                        )
                    ))
        
        return errors


class SuicideAttackValidator:
    """
    Prevents guaranteed-loss tussles ("suicide attacks").
    
    A tussle is a suicide attack if:
    1. Defender is faster (higher SPD + attacker bonus)
    2. Defender's STR >= Attacker's STA (attacker dies in first strike)
    3. Result: Attacker broken, defender survives = 2 Charge wasted
    
    Uses the game engine's predict_tussle_winner() method for accuracy.
    """
    
    def __init__(self, game_engine):
        """
        Initialize with a game engine for tussle prediction.
        
        Args:
            game_engine: GameEngine instance for predict_tussle_winner()
        """
        self.game_engine = game_engine
    
    def validate(
        self,
        plan: "TurnPlan",
        game_state: "GameState",
        player_id: str
    ) -> List[ValidationError]:
        """
        Validate tussles are winnable or at least trade favorably.
        
        Args:
            plan: The turn plan to validate
            game_state: Current game state
            player_id: AI player's ID
            
        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []
        
        for i, action in enumerate(plan.action_sequence):
            if action.action_type != "tussle" or not action.target_ids:
                continue
            
            # Find attacker and defender cards
            attacker = game_state.find_card_by_id(action.card_id)
            defender = game_state.find_card_by_id(action.target_ids[0])
            
            if not attacker or not defender:
                # Card IDs invalid - will be caught by turn_planner validation
                continue
            
            # Use engine's prediction method
            winner = self.game_engine.predict_tussle_winner(attacker, defender)
            
            if winner == "defender":
                # Attacker dies, deals 0 damage = waste of Charge
                errors.append(ValidationError(
                    action_index=i,
                    error_type="suicide_attack",
                    message=f"Suicide attack: {attacker.name} will die before damaging {defender.name} "
                           f"(SPD: {attacker.speed} vs {defender.speed}, "
                           f"STR: {attacker.strength} vs {attacker.current_stamina} STA)"
                ))
        
        return errors


class DependencyValidator:
    """
    Validates action sequence dependencies.
    
    Certain cards must be played before their effects are used:
    - Surge: Must play before spending the +1 Charge it grants
    - Wake: Must play before using the woken card
    - VeryVeryAppleJuice: Should play before tussling (stat boost)
    """
    
    def validate(
        self,
        plan: "TurnPlan",
        game_state: "GameState",
        player_id: str
    ) -> List[ValidationError]:
        """
        Validate action ordering makes sense.
        
        Args:
            plan: The turn plan to validate
            game_state: Current game state
            player_id: AI player's ID
            
        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []
        
        # Track which cards have been played and their effects
        surge_played = False
        hlk_played = False
        woken_card_ids = set()
        ai_player = game_state.players[player_id]

        # Track starting hand and break zone for dependency checks
        starting_hand_ids = {card.id for card in ai_player.hand}
        starting_hand_names = {card.name for card in ai_player.hand}
        break_zone_ids = {card.id for card in ai_player.break_zone}
        break_zone_names = {card.name for card in ai_player.break_zone}

        for i, action in enumerate(plan.action_sequence):
            # Track Wake targets - Wake is a play_card action (played from hand with target)
            # The target is the card to fix from your break zone
            if action.card_name == "Wake" and action.action_type == "play_card" and action.target_ids:
                woken_card_ids.update(action.target_ids)

            # Check if playing a card that wasn't in the starting hand
            if action.action_type == "play_card":
                if action.card_id:
                    if action.card_id not in starting_hand_ids and action.card_id not in woken_card_ids:
                        if action.card_id in break_zone_ids:
                            # Break zone card played without Wake — most common hallucination
                            errors.append(ValidationError(
                                action_index=i,
                                error_type="break_zone_play",
                                message=(
                                    f"Cannot play {action.card_name} (ID {action.card_id}): "
                                    f"it is in your break zone, not your hand. "
                                    f"Play Wake first (1 Charge, target this card) to return it to hand."
                                ),
                            ))
                        else:
                            errors.append(ValidationError(
                                action_index=i,
                                error_type="dependency",
                                message=f"Playing {action.card_name} (ID {action.card_id}) that wasn't in hand or woken by Wake"
                            ))
                elif action.card_name:
                    # No card_id — fall back to name-based check
                    if action.card_name in break_zone_names and action.card_name not in starting_hand_names:
                        woken_names = {
                            c.name
                            for wid in woken_card_ids
                            if (c := game_state.find_card_by_id(wid)) is not None
                        }
                        if action.card_name not in woken_names:
                            errors.append(ValidationError(
                                action_index=i,
                                error_type="break_zone_play",
                                message=(
                                    f"Cannot play {action.card_name}: it is in your break zone, "
                                    f"not your hand. Play Wake first (1 Charge) to return it to hand."
                                ),
                            ))

        # Note: We can't easily detect "spending Surge Charge before playing Surge"
        # without detailed Charge tracking per action, which ChargeBudgetValidator handles

        return errors


class TurnPlanValidator:
    """
    Main validator that runs all sub-validators.
    
    Usage:
        validator = TurnPlanValidator(game_engine)
        errors = validator.validate(plan, game_state, player_id, starting_charge)
        if errors:
            feedback = validator.format_feedback_for_llm(errors)
            # Send feedback to LLM for retry
    """

    def __init__(self, game_engine):
        """
        Initialize with a game engine.

        Args:
            game_engine: GameEngine instance for tussle prediction
        """
        self.charge_validator = ChargeBudgetValidator()
        self.toy_tracker = OpponentToyTracker()
        self.suicide_validator = SuicideAttackValidator(game_engine)
        self.dependency_validator = DependencyValidator()

    def validate(
        self,
        plan: "TurnPlan",
        game_state: "GameState",
        player_id: str,
        starting_charge: int
    ) -> List[ValidationError]:
        """
        Run all validators on a turn plan.

        Args:
            plan: The turn plan to validate
            game_state: Current game state
            player_id: AI player's ID
            starting_charge: Charge at the start of the turn

        Returns:
            List of all validation errors (empty if valid)
        """
        all_errors = []

        # Run Charge budget validator
        charge_errors = self.charge_validator.validate(plan, starting_charge)
        all_errors.extend(charge_errors)
        
        # Run opponent toy tracker
        toy_errors = self.toy_tracker.validate(plan, game_state, player_id)
        all_errors.extend(toy_errors)
        
        # Run suicide attack validator
        suicide_errors = self.suicide_validator.validate(plan, game_state, player_id)
        all_errors.extend(suicide_errors)
        
        # Run dependency validator
        dep_errors = self.dependency_validator.validate(plan, game_state, player_id)
        all_errors.extend(dep_errors)
        
        # Log validation results
        if all_errors:
            logger.debug(f"Plan validation found {len(all_errors)} error(s)")
            for error in all_errors:
                logger.debug(f"  {error.to_llm_feedback()}")
        else:
            logger.debug("✅ Plan passed all validators")
        
        return all_errors
    
    def format_feedback_for_llm(self, errors: List[ValidationError]) -> str:
        """
        Format validation errors as feedback for LLM retry.
        
        Args:
            errors: List of validation errors
            
        Returns:
            Formatted string for LLM prompt
        """
        if not errors:
            return ""
        
        feedback_lines = ["Your plan failed validation:"]
        for i, error in enumerate(errors, 1):
            feedback_lines.append(f"{i}. {error.to_llm_feedback()}")
        feedback_lines.append("\nPlease revise your plan to fix these issues.")
        
        return "\n".join(feedback_lines)
