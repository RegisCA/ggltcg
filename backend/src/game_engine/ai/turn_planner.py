"""
Turn Planner for AI v3.

This module implements the Phase 1 planning component of the AI v3 architecture.
The TurnPlanner generates a complete turn plan at the start of each turn using
the 4-phase framework from the Strategy Guide.

Key responsibilities:
1. Generate planning prompt with full game state context
2. Call LLM to create a TurnPlan
3. Validate the plan structure and card ID references
4. Return the plan for execution phase
"""

import json
import logging
import time
from typing import Optional, Dict, Any

from game_engine.models.game_state import GameState
from .prompts import (
    TurnPlan,
    PlannedAction,
    TURN_PLAN_JSON_SCHEMA,
    PROMPTS_VERSION,
    format_sleep_zone_for_planning,
    format_game_state_for_ai,
)
from .prompts.planning_prompt_v2 import (
    get_planning_prompt_v2,
    format_hand_for_planning_v2,
    format_in_play_for_planning_v2,
    collect_card_names,
)

logger = logging.getLogger(__name__)


class TurnPlanner:
    """
    Generates turn plans using the 4-phase strategic framework.
    
    Phase 1: Threat Assessment - Evaluate opponent's board
    Phase 2: Resource Inventory - Catalog available tools and sequences  
    Phase 3: Threat Mitigation - Generate and select removal sequences
    Phase 4: Offensive Opportunities - Direct attacks with remaining CC
    """
    
    def __init__(self, client, model_name: str, fallback_model: str):
        """
        Initialize the TurnPlanner.
        
        Args:
            client: google-genai Client instance
            model_name: Primary model to use
            fallback_model: Fallback model for capacity issues
        """
        self.client = client
        self.model_name = model_name
        self.fallback_model = fallback_model
        
        # Store last planning info for debugging
        self._last_prompt: Optional[str] = None
        self._last_response: Optional[str] = None
        self._last_plan: Optional[TurnPlan] = None
    
    def create_plan(
        self,
        game_state: GameState,
        player_id: str,
        game_engine=None
    ) -> Optional[TurnPlan]:
        """
        Generate a complete turn plan for the current game state.
        
        Args:
            game_state: Current GameState object
            player_id: ID of the AI player
            game_engine: Optional GameEngine for calculating effective stats
            
        Returns:
            TurnPlan object if successful, None if planning failed
        """
        logger.info(f"🧠 Creating turn plan for Turn {game_state.turn_number}")
        
        ai_player = game_state.players[player_id]
        opponent = game_state.get_opponent(player_id)
        
        # Format game state for the prompt
        game_state_text = format_game_state_for_ai(game_state, player_id, game_engine)
        
        # Format detailed card information with IDs (v2 compact format)
        hand_details = format_hand_for_planning_v2(ai_player.hand, game_engine, player=ai_player)
        
        # Combine AI's in-play cards with opponent's for context
        ai_in_play = format_in_play_for_planning_v2(ai_player.in_play, game_engine, player=ai_player)
        opp_in_play = format_in_play_for_planning_v2(opponent.in_play, game_engine, player=opponent)
        
        in_play_details = f"""**Your Toys:**
{ai_in_play}

**Opponent's Toys (THREATS):**
{opp_in_play}

**Your Sleep Zone:** {format_sleep_zone_for_planning(ai_player.sleep_zone)}
**Opponent's Sleep Zone:** {format_sleep_zone_for_planning(opponent.sleep_zone)}"""
        
        # Collect card names for dynamic documentation (only include what's relevant)
        card_names_in_game = collect_card_names(
            ai_player.hand,
            ai_player.in_play,
            opponent.in_play,
            opponent.sleep_zone  # Include opponent's sleep zone for context
        )
        
        # Generate the compact v2 planning prompt
        prompt = get_planning_prompt_v2(
            game_state_text, hand_details, in_play_details, card_names_in_game
        )
        self._last_prompt = prompt
        
        logger.debug(f"Planning prompt ({len(prompt)} chars):\n{prompt}")
        
        try:
            # Call LLM to generate plan
            response_text = self._call_planning_api(prompt)
            self._last_response = response_text
            
            logger.debug(f"Raw plan response:\n{response_text}")
            
            # Parse the response
            plan_data = json.loads(response_text)
            
            # Convert to TurnPlan object
            plan = self._parse_plan(plan_data)
            self._last_plan = plan
            
            # Log plan summary
            self._log_plan_summary(plan)
            
            return plan
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan as JSON: {e}")
            logger.error(f"Response was: {self._last_response}")
            return None
        except Exception as e:
            logger.exception(f"Error creating plan: {e}")
            return None
    
    def _call_planning_api(
        self,
        prompt: str,
        retry_count: int = 3,
        allow_fallback: bool = True
    ) -> str:
        """
        Call Gemini API with the planning prompt and TurnPlan schema.
        
        Args:
            prompt: The planning prompt
            retry_count: Number of retries for 429 errors
            allow_fallback: Whether to use fallback model on capacity issues
            
        Returns:
            JSON response text
        """
        from google.genai import types
        
        last_exception = None
        current_model = self.model_name
        
        for attempt in range(retry_count):
            try:
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=prompt)]
                        )
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=8192,  # Larger for detailed plans
                        response_mime_type="application/json",
                        response_json_schema=TURN_PLAN_JSON_SCHEMA,
                    )
                )
                
                # Check for empty response
                if not response.candidates or not response.candidates[0].content.parts:
                    finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
                    raise ValueError(f"Empty response (finish_reason: {finish_reason})")
                
                result = response.text.strip()
                logger.debug(f"Plan response length: {len(result)} characters")
                return result
                
            except Exception as e:
                error_str = str(e)
                last_exception = e
                
                # Handle 429 Resource Exhausted
                if "429" in error_str or "ResourceExhausted" in error_str or "Resource exhausted" in error_str:
                    if attempt < retry_count - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"API capacity issue. Retry {attempt + 1}/{retry_count} after {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    elif allow_fallback:
                        logger.warning(f"Switching to fallback model: {self.fallback_model}")
                        _current_model = self.fallback_model  # noqa: F841 - assigned for potential future use
                        return self._call_planning_api(prompt, retry_count=1, allow_fallback=False)
                
                raise last_exception
        
        raise last_exception
    
    def _parse_plan(self, plan_data: Dict[str, Any]) -> TurnPlan:
        """
        Parse the JSON response into a TurnPlan object.
        
        Args:
            plan_data: Parsed JSON dictionary
            
        Returns:
            TurnPlan object
        """
        # Parse action sequence
        action_sequence = []
        for action_data in plan_data.get("action_sequence", []):
            action = PlannedAction(
                action_type=action_data.get("action_type"),
                card_id=action_data.get("card_id"),
                card_name=action_data.get("card_name"),
                target_ids=action_data.get("target_ids"),
                target_names=action_data.get("target_names"),
                alternative_cost_id=action_data.get("alternative_cost_id"),
                cc_cost=action_data.get("cc_cost", 0),
                cc_after=action_data.get("cc_after", 0),
                reasoning=action_data.get("reasoning", ""),
            )
            action_sequence.append(action)
        
        # Create TurnPlan
        plan = TurnPlan(
            threat_assessment=plan_data.get("threat_assessment", ""),
            resources_summary=plan_data.get("resources_summary", ""),
            sequences_considered=plan_data.get("sequences_considered", []),
            selected_strategy=plan_data.get("selected_strategy", ""),
            action_sequence=action_sequence,
            cc_start=plan_data.get("cc_start", 0),
            cc_after_plan=plan_data.get("cc_after_plan", 0),
            expected_cards_slept=plan_data.get("expected_cards_slept", 0),
            cc_efficiency=plan_data.get("cc_efficiency", "N/A"),
            plan_reasoning=plan_data.get("plan_reasoning", ""),
        )
        
        return plan
    
    def _log_plan_summary(self, plan: TurnPlan) -> None:
        """Log a human-readable summary of the plan."""
        logger.info("=" * 60)
        logger.info("📋 TURN PLAN GENERATED")
        logger.info("=" * 60)
        logger.info(f"Threat Assessment: {plan.threat_assessment[:100]}...")
        logger.info(f"Selected Strategy: {plan.selected_strategy}")
        logger.info(f"CC Budget: {plan.cc_start} → {plan.cc_after_plan}")
        logger.info(f"Expected cards to sleep: {plan.expected_cards_slept}")
        logger.info(f"CC Efficiency: {plan.cc_efficiency}")
        logger.info("-" * 40)
        logger.info("Action Sequence:")
        for i, action in enumerate(plan.action_sequence, 1):
            card_info = f"{action.card_name or 'N/A'}" if action.card_name else action.card_id or "N/A"
            target_info = ""
            if action.target_names:
                target_info = f" → {', '.join(action.target_names)}"
            elif action.target_ids:
                target_info = f" → {', '.join(action.target_ids[:2])}..."
            logger.info(f"  {i}. {action.action_type}: {card_info}{target_info} ({action.cc_cost} CC → {action.cc_after} CC)")
        logger.info("=" * 60)
    
    def get_last_plan_info(self) -> Dict[str, Any]:
        """
        Get information about the last generated plan for debugging.
        
        Returns:
            Dict with prompt, response, and parsed plan
        """
        return {
            "prompt": self._last_prompt,
            "response": self._last_response,
            "plan": self._last_plan.model_dump() if self._last_plan else None,
            "prompts_version": PROMPTS_VERSION,
        }
    
    def validate_plan_actions(
        self,
        plan: TurnPlan,
        game_state: GameState,
        player_id: str
    ) -> list[str]:
        """
        Validate that all card IDs in the plan exist in the game state.
        
        Args:
            plan: The TurnPlan to validate
            game_state: Current game state
            player_id: AI player's ID
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        ai_player = game_state.players[player_id]
        opponent = game_state.get_opponent(player_id)
        
        # Build sets of valid card IDs
        ai_hand_ids = {card.id for card in ai_player.hand}
        ai_in_play_ids = {card.id for card in ai_player.in_play}
        ai_sleep_ids = {card.id for card in ai_player.sleep_zone}
        opp_in_play_ids = {card.id for card in opponent.in_play}
        
        _all_ai_ids = ai_hand_ids | ai_in_play_ids | ai_sleep_ids  # noqa: F841 - reserved for future validation
        all_targetable_ids = ai_in_play_ids | opp_in_play_ids | ai_sleep_ids
        
        for i, action in enumerate(plan.action_sequence):
            # Validate card_id
            if action.card_id:
                if action.action_type == "play_card":
                    if action.card_id not in ai_hand_ids:
                        errors.append(f"Action {i+1}: card_id {action.card_id} not in AI's hand")
                elif action.action_type in ("tussle", "activate_ability"):
                    if action.card_id not in ai_in_play_ids:
                        errors.append(f"Action {i+1}: card_id {action.card_id} not in AI's in-play")
            
            # Validate target_ids
            if action.target_ids:
                for target_id in action.target_ids:
                    if target_id not in all_targetable_ids:
                        errors.append(f"Action {i+1}: target_id {target_id} not found in game")
            
            # Validate alternative_cost_id
            if action.alternative_cost_id:
                if action.alternative_cost_id not in ai_in_play_ids:
                    errors.append(f"Action {i+1}: alternative_cost_id {action.alternative_cost_id} not in AI's in-play")
        
        if errors:
            logger.warning(f"Plan validation found {len(errors)} issue(s):")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return errors
