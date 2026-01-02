"""
Turn Plan Validators

Validates AI turn plans for multi-step reasoning errors that the game engine
doesn't catch. Each validator focuses on a specific class of planning errors.

Architecture Philosophy:
- Game Engine: Validates individual actions (turn, phase, CC, zones, targets)
- These Validators: Validate action sequences (CC budgeting, mid-plan state, dependencies)
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_engine.ai.prompts import TurnPlan
    from game_engine.models.game_state import GameState

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """A single validation error in a turn plan."""
    action_index: int  # 0-based index of the action that caused the error
    error_type: str  # "cc_budget", "opponent_toys", "suicide_attack", "dependency"
    message: str  # Human-readable error message
    
    def to_llm_feedback(self) -> str:
        """Format error for LLM retry feedback."""
        return f"[Action {self.action_index + 1}] {self.message}"


class CCBudgetValidator:
    """
    Validates that the turn plan doesn't exceed the CC budget.
    
    The game engine validates individual actions, but the AI must budget
    CC across the entire sequence, accounting for CC gains from cards like:
    - Surge: +1 CC when played
    - Rush: +2 CC when played  
    - HLK: +1 CC when played (can't play turn 1)
    - Umbruh: +1 CC when it tussles or is tussled
    - Belchaletta: +2 CC at start of turn (continuous effect)
    - Red Solo Cup: +1 CC when you play another card
    """
    
    # Cards that gain CC when played
    CC_GAIN_ON_PLAY = {
        "Surge": 1,
        "Rush": 2,
        "HLK": 1,
    }
    
    # Cards that gain CC from other triggers (requires plan analysis)
    CC_GAIN_TRIGGERS = {
        "Umbruh": "tussle",  # Gains 1 CC when it tussles
        "Red Solo Cup": "play_card",  # Gains 1 CC when you play another card
    }
    
    def validate(self, plan: "TurnPlan", starting_cc: int) -> List[ValidationError]:
        """
        Validate CC budget across the entire action sequence.
        
        Args:
            plan: The turn plan to validate
            starting_cc: CC at the start of the turn
            
        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []
        cc_remaining = starting_cc
        
        # Track which CC-generating cards are in play
        red_solo_cup_in_play = False
        umbruh_in_play = False
        
        for i, action in enumerate(plan.action_sequence):
            # Track CC gains from playing cards
            cc_gain = 0
            
            if action.action_type == "play_card" and action.card_name:
                # Direct CC gain from playing the card
                cc_gain += self.CC_GAIN_ON_PLAY.get(action.card_name, 0)
                
                # Red Solo Cup triggers when you play other cards
                if red_solo_cup_in_play and action.card_name != "Red Solo Cup":
                    cc_gain += 1
                
                # Track if we just played Red Solo Cup or Umbruh
                if action.card_name == "Red Solo Cup":
                    red_solo_cup_in_play = True
                elif action.card_name == "Umbruh":
                    umbruh_in_play = True
            
            # Umbruh gains CC when it tussles
            if action.action_type == "tussle" and action.card_name == "Umbruh":
                cc_gain += 1
            
            # Apply CC gains first
            cc_remaining += cc_gain
            
            # Check if we can afford this action
            action_cost = action.cc_cost or 0
            
            if action_cost > cc_remaining:
                errors.append(ValidationError(
                    action_index=i,
                    error_type="cc_budget",
                    message=f"Cannot afford {action.card_name or action.action_type} "
                           f"(need {action_cost} CC, have {cc_remaining} CC)"
                ))
            
            # Deduct cost
            cc_remaining -= action_cost
            
            # Check for negative CC
            if cc_remaining < 0:
                errors.append(ValidationError(
                    action_index=i,
                    error_type="cc_budget",
                    message=f"CC went negative ({cc_remaining} CC) after {action.card_name or action.action_type}"
                ))
                # Stop checking - plan is fundamentally broken
                break
        
        return errors


class OpponentToyTracker:
    """
    Tracks opponent toys remaining during plan execution.
    
    Prevents "direct attack while opponent has toys" errors by simulating
    which toys get sleeped by tussles/effects during the plan.
    
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
        opponent = game_state.get_opponent(player_id)
        
        # Track which opponent toys are still in play
        toys_remaining = {card.id for card in opponent.in_play}
        
        for i, action in enumerate(plan.action_sequence):
            # Remove toys that get sleeped
            if action.action_type == "tussle" and action.target_ids:
                # Tussle sleeps the target (assuming it dies - we check this in SuicideAttackValidator)
                # Note: This is a simplification - the target might survive
                # But the AI should plan tussles that kill the target
                target_id = action.target_ids[0]
                if target_id in toys_remaining:
                    toys_remaining.discard(target_id)
            
            elif action.action_type == "play_card":
                # Some cards sleep opponent toys
                if action.card_name == "Drop" and action.target_ids:
                    # Drop sleeps a target toy
                    for target_id in action.target_ids:
                        toys_remaining.discard(target_id)
                
                elif action.card_name == "Twist" and action.target_ids:
                    # Twist returns target to hand (not in play)
                    for target_id in action.target_ids:
                        toys_remaining.discard(target_id)
                
                elif action.card_name == "Clean":
                    # Clean sleeps all toys
                    toys_remaining.clear()
            
            elif action.action_type == "activate_ability":
                # Archer's ability sleeps a target
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
        
        return errors


class SuicideAttackValidator:
    """
    Prevents guaranteed-loss tussles ("suicide attacks").
    
    A tussle is a suicide attack if:
    1. Defender is faster (higher SPD + attacker bonus)
    2. Defender's STR >= Attacker's STA (attacker dies in first strike)
    3. Result: Attacker sleeped, defender survives = 2 CC wasted
    
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
                # Attacker dies, deals 0 damage = waste of CC
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
    - Surge: Must play before spending the +1 CC it grants
    - Wake: Must play before using the woken card
    - HLK: Must play before spending the +1 CC it grants
    - VeryVeryAppleJuice: Should play before tussling (stat boost)
    - Red Solo Cup: Should play before other cards (triggers CC gain)
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
        
        # Track starting hand card IDs
        starting_hand_ids = {card.id for card in ai_player.hand}
        
        for i, action in enumerate(plan.action_sequence):
            # Detect incorrect Wake usage (trying to play_card Wake instead of activate_ability)
            if action.card_name == "Wake" and action.action_type == "play_card":
                errors.append(ValidationError(
                    action_index=i,
                    error_type="dependency",
                    message="Wake is an ACTIVATED ABILITY, not a play_card action. Use action_type='activate_ability' with target_ids=[card_to_wake]"
                ))
            
            # Track Wake targets (Wake is an activate_ability, not play_card)
            if action.card_name == "Wake" and action.action_type == "activate_ability" and action.target_ids:
                woken_card_ids.update(action.target_ids)
            
            # Check if playing a card that wasn't in starting hand
            if action.action_type == "play_card" and action.card_id:
                if action.card_id not in starting_hand_ids:
                    # This card came from somewhere else
                    if action.card_id not in woken_card_ids:
                        # Not woken by Wake - this is likely an error
                        # (Could also be from Twist returning own card, but rare)
                        errors.append(ValidationError(
                            action_index=i,
                            error_type="dependency",
                            message=f"Playing {action.card_name} (ID {action.card_id}) that wasn't in hand or woken by Wake"
                        ))
            
            # Track Surge/HLK
            if action.card_name == "Surge":
                surge_played = True
            elif action.card_name == "HLK":
                hlk_played = True
        
        # Note: We can't easily detect "spending Surge CC before playing Surge"
        # without detailed CC tracking per action, which CCBudgetValidator handles
        
        return errors


class TurnPlanValidator:
    """
    Main validator that runs all sub-validators.
    
    Usage:
        validator = TurnPlanValidator(game_engine)
        errors = validator.validate(plan, game_state, player_id, starting_cc)
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
        self.cc_validator = CCBudgetValidator()
        self.toy_tracker = OpponentToyTracker()
        self.suicide_validator = SuicideAttackValidator(game_engine)
        self.dependency_validator = DependencyValidator()
    
    def validate(
        self,
        plan: "TurnPlan",
        game_state: "GameState",
        player_id: str,
        starting_cc: int
    ) -> List[ValidationError]:
        """
        Run all validators on a turn plan.
        
        Args:
            plan: The turn plan to validate
            game_state: Current game state
            player_id: AI player's ID
            starting_cc: CC at the start of the turn
            
        Returns:
            List of all validation errors (empty if valid)
        """
        all_errors = []
        
        # Run CC budget validator
        cc_errors = self.cc_validator.validate(plan, starting_cc)
        all_errors.extend(cc_errors)
        
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
            logger.warning(f"Plan validation found {len(all_errors)} error(s)")
            for error in all_errors:
                logger.warning(f"  {error.to_llm_feedback()}")
        else:
            logger.info("✅ Plan passed all validators")
        
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
