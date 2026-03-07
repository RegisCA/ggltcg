"""
LLM-powered AI player using Gemini API.

This module implements an AI player that uses Google's Gemini
to make strategic decisions in GGLTCG games.

Version 3.0 Changes:
- Two-phase architecture: Plan entire turn first, then execute actions
- CC budgeting and efficiency tracking
- Action ordering optimization (HLK, Surge, VVAJ combos)

Version 2.1 Changes:
- Enhanced decision priority to emphasize direct attacks over board building

Version 2.0 Changes:
- Unified target_id to target_ids (array) for multi-target support (Sun card)
- Implemented Gemini structured output mode with JSON schema
- Better error handling and logging

"""

import json
import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Look for .env in backend directory
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass  # python-dotenv is optional

from .prompts import SYSTEM_PROMPT, get_ai_turn_prompt, PROMPTS_VERSION, AI_DECISION_JSON_SCHEMA
from game_engine.models.game_state import GameState
from api.schemas import ValidAction
from .providers import build_provider, get_default_provider_name


# AI Version Configuration
# Set AI_VERSION=3 to enable turn planning (v3)
# Default is v2 (per-action decisions)
def get_default_ai_version() -> int:
    """Get the default AI version from environment.

    Returns 3 (turn planning) unless explicitly set to 2.
    """
    version_str = os.getenv("AI_VERSION", "3")
    try:
        return int(version_str)
    except ValueError:
        logger.warning(f"Invalid AI_VERSION '{version_str}', defaulting to 3")
        return 3


class LLMPlayer:
    """
    AI player powered by Gemini API.
    
    Uses an LLM to analyze game state and select optimal actions.
    Version 2.0: Now supports multi-target selection and Gemini structured output.
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize the AI player.
        
        Args:
            provider: LLM provider to use
            api_key: API key (reads from env var if not provided)
            model: Model to use (provider-specific defaults if not provided)
        """
        resolved_provider = provider or get_default_provider_name()
        self.provider_client, config = build_provider(
            provider_name=resolved_provider,
            api_key=api_key,
            model=model,
        )
        self.provider = config.provider
        self.api_key = config.api_key
        self.model_name = config.model
        self.fallback_model = config.fallback_model
        self.client = getattr(self.provider_client, "client", None)
        
        # Store last target/alternative cost selections from LLM
        # v2.0: target_ids is now a list for multi-target support (Sun card)
        self._last_target_ids: Optional[List[str]] = None
        self._last_alternative_cost_id: Optional[str] = None
        
        # Store last prompt/response for logging
        self._last_prompt: Optional[str] = None
        self._last_response: Optional[str] = None
        self._last_action_number: Optional[int] = None
        self._last_reasoning: Optional[str] = None

        logger.debug("Initializing %s with model: %s", self.provider, self.model_name)
        logger.debug("Fallback model: %s", self.fallback_model)
    
    def select_action(
        self,
        game_state: GameState,
        ai_player_id: str,
        valid_actions: list[ValidAction],
        game_engine=None
    ) -> Optional[tuple[int, str]]:
        """
        Use LLM to select the best action from valid options.
        
        Args:
            game_state: Current game state
            ai_player_id: ID of the AI player
            valid_actions: List of valid actions the AI can take
            game_engine: Optional GameEngine for calculating effective stats
            
        Returns:
            Tuple of (action_index, reasoning) where action_index is 0-based,
            or None if selection failed
        """
        if not valid_actions:
            logger.warning("No valid actions available for AI")
            return None
        
        logger.debug(f"🤖 AI Turn {game_state.turn_number} - {len(valid_actions)} actions available")
        
        # Build the prompt
        prompt = get_ai_turn_prompt(game_state, ai_player_id, valid_actions, game_engine)
        
        # Store prompt for logging
        self._last_prompt = prompt
        self._last_response = None
        self._last_action_number = None
        self._last_reasoning = None
        
        logger.debug(f"AI Prompt:\n{prompt}")
        
        try:
            # Call LLM API based on provider
            logger.debug("Calling %s API (%s)...", self.provider, self.model_name)

            response_text = self._call_json_api(prompt)
            
            # Store raw response for logging
            self._last_response = response_text
            
            logger.debug(f"Raw API Response:\n{response_text}")
            
            # Parse JSON response
            # Handle markdown code blocks if present (for non-structured output mode)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            response_data = json.loads(response_text)
            logger.debug(f"Parsed JSON: {response_data}")
            
            # Extract action number (1-based from prompt, convert to 0-based index)
            action_number = response_data.get("action_number")
            reasoning = response_data.get("reasoning", "No reasoning provided")
            
            # v2.0: Support both target_ids (array, new) and target_id (string, legacy)
            target_ids = response_data.get("target_ids")
            target_id_legacy = response_data.get("target_id")  # Backwards compatibility
            alternative_cost_id = response_data.get("alternative_cost_id")
            
            # Normalize target_ids
            # Handle: null, "null", "None", empty array, single string (legacy)
            if target_ids is None or target_ids == "null" or target_ids == "None":
                target_ids = None
            elif isinstance(target_ids, str):
                # Single string provided instead of array
                if target_ids and target_ids not in ("null", "None"):
                    target_ids = [target_ids]
                else:
                    target_ids = None
            elif isinstance(target_ids, list):
                # Filter out null/None strings from array
                target_ids = [t for t in target_ids if t and t not in ("null", "None")]
                if not target_ids:
                    target_ids = None
            
            # Backwards compatibility: if target_id was provided instead of target_ids
            if target_ids is None and target_id_legacy:
                if target_id_legacy not in ("null", "None"):
                    target_ids = [target_id_legacy]
                    logger.debug("Using legacy target_id field (migrating to target_ids)")
            
            # Normalize alternative_cost_id
            if alternative_cost_id == "null" or alternative_cost_id == "None":
                alternative_cost_id = None
            
            # DEBUG: Log all actions with their numbers
            logger.debug("=" * 60)
            logger.debug("DEBUG - Valid Actions List:")
            for i, action in enumerate(valid_actions):
                logger.debug(f"  Prompt number {i+1} -> Index {i}: {action.description}")
            logger.debug("=" * 60)
            
            if action_number is None:
                logger.error(f"AI response missing action_number: {response_data}")
                return None
            
            logger.debug(f"DEBUG - AI returned action_number: {action_number} (type: {type(action_number)})")
            
            # Convert to 0-based index
            action_index = action_number - 1
            logger.debug(f"DEBUG - Converted to action_index: {action_index}")
            
            # Validate index
            if action_index < 0 or action_index >= len(valid_actions):
                logger.error(f"AI selected invalid action number {action_number} (max {len(valid_actions)})")
                return None
            
            # Log the decision
            selected_action = valid_actions[action_index]
            logger.debug(f"✅ AI Decision: {selected_action.description}")
            logger.debug(f"💭 Reasoning: {reasoning}")
            if target_ids:
                logger.debug(f"🎯 Targets ({len(target_ids)}): {target_ids}")
            if alternative_cost_id:
                logger.debug(f"💰 Alternative Cost: {alternative_cost_id}")
            logger.debug(f"DEBUG - Returning action_index: {action_index}")
            logger.debug("=" * 60)
            
            # Store target and alternative cost selections
            self._last_target_ids = target_ids
            self._last_alternative_cost_id = alternative_cost_id
            
            # Store parsed action data for logging
            self._last_action_number = action_number
            self._last_reasoning = reasoning
            
            return (action_index, reasoning)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response was: {response_text}")
            return None
        
        except Exception as e:
            logger.exception(f"Error getting AI decision: {e}")
            return None
    
    def get_last_decision_info(self) -> Dict[str, Any]:
        """
        Get information about the last AI decision for logging.
        
        Returns:
            Dict containing prompt, response, model info, and parsed action data
        """
        return {
            "prompt": self._last_prompt,
            "response": self._last_response,
            "model_name": self.model_name,
            "prompts_version": PROMPTS_VERSION,
            "action_number": self._last_action_number,
            "reasoning": self._last_reasoning,
        }
    
    def _call_json_api(self, prompt: str, retry_count: int = 3, allow_fallback: bool = True) -> str:
        """
        Call the configured provider with structured JSON output.
        
        Args:
            prompt: The prompt to send
            retry_count: Number of retries for transient errors
            allow_fallback: Whether to fall back to the configured fallback model
            
        Returns:
            The API response text (valid JSON)
        """
        response_text = self.provider_client.generate_json(
            prompt,
            AI_DECISION_JSON_SCHEMA,
            temperature=0.7,
            max_output_tokens=4096,
            retry_count=retry_count,
            allow_fallback=allow_fallback,
            model=self.model_name,
            fallback_model=self.fallback_model,
            system_instruction=SYSTEM_PROMPT,
        )
        logger.debug("Structured output response length: %s characters", len(response_text))
        logger.debug("Structured output: %s", response_text)
        return response_text
    
    def get_action_details(
        self,
        selected_action: ValidAction
    ) -> Dict[str, Any]:
        """
        Convert a ValidAction into the request parameters needed for the API.
        Uses target_id and alternative_cost_id from the last LLM response.
        
        Args:
            selected_action: The action selected by the AI
            
        Returns:
            Dictionary with request parameters for the API endpoint
        """
        result: Dict[str, Any] = {}
        
        if selected_action.action_type == "play_card":
            result["action_type"] = "play_card"
            result["card_id"] = selected_action.card_id
            
            # v2.0: Handle target selection with target_ids (array) for multi-target support
            # This enables Sun card to select 2 targets
            if self._last_target_ids:
                result["target_ids"] = self._last_target_ids
                logger.debug(f"Using AI-selected targets ({len(self._last_target_ids)}): {self._last_target_ids}")
            elif selected_action.target_options:
                # Fallback: Use first available target if AI didn't specify
                result["target_ids"] = [selected_action.target_options[0]]
                logger.warning(f"AI didn't specify target, using first option: {result['target_ids']}")
            
            # Handle alternative cost (for Ballaber)
            if self._last_alternative_cost_id:
                result["alternative_cost_card_id"] = self._last_alternative_cost_id
                logger.debug(f"Using AI-selected alternative cost: {self._last_alternative_cost_id}")
            elif selected_action.alternative_cost_options and len(selected_action.alternative_cost_options) > 0:
                # Fallback: Use first available alternative cost card if AI didn't specify
                result["alternative_cost_card_id"] = selected_action.alternative_cost_options[0]
                logger.warning(f"AI didn't specify alternative cost, using first option: {result['alternative_cost_card_id']}")
        
        elif selected_action.action_type == "tussle":
            result["action_type"] = "tussle"
            result["attacker_id"] = selected_action.card_id
            
            # Handle target selection for tussles (still single target)
            if self._last_target_ids and len(self._last_target_ids) > 0:
                result["defender_id"] = self._last_target_ids[0]  # Use first target for tussle
                logger.debug(f"Using AI-selected tussle target: {self._last_target_ids[0]}")
            elif selected_action.target_options:
                # Check if this is a direct attack or targeted tussle
                if selected_action.target_options[0] == "direct_attack":
                    result["defender_id"] = None  # Direct attack
                else:
                    result["defender_id"] = selected_action.target_options[0]
                    logger.warning(f"AI didn't specify tussle target, using first option: {result['defender_id']}")
            else:
                result["defender_id"] = None  # Direct attack
        
        elif selected_action.action_type == "activate_ability":
            result["action_type"] = "activate_ability"
            result["card_id"] = selected_action.card_id
            result["amount"] = 1  # Always use 1 for now (can be repeated)
            
            # Handle target selection for activated abilities (still single target)
            if self._last_target_ids and len(self._last_target_ids) > 0:
                result["target_id"] = self._last_target_ids[0]  # Use first target for ability
                logger.debug(f"Using AI-selected ability target: {self._last_target_ids[0]}")
            elif selected_action.target_options:
                # Fallback: Use first available target if AI didn't specify
                result["target_id"] = selected_action.target_options[0]
                logger.warning(f"AI didn't specify ability target, using first option: {result['target_id']}")
        
        elif selected_action.action_type == "end_turn":
            result["action_type"] = "end_turn"
        
        # Clear stored selections after use
        self._last_target_ids = None
        self._last_alternative_cost_id = None
        
        return result
    
    def get_endpoint_name(self) -> str:
        """
        Get a human-readable name for the AI endpoint being used.
        
        Returns:
            String like "Gemini 2.0 Flash Lite"
        """
        return self.provider_client.get_display_name(self.model_name)


class LLMPlayerV3(LLMPlayer):
    """
    AI player v3 with two-phase turn planning.
    
    Phase 1: Generate complete turn plan with CC budgeting
    Phase 2: Execute each action from the plan sequentially
    
    Inherits from LLMPlayer for API calls and action execution.
    """
    
    def __init__(self, ai_version: int = None, planner_mode: str = None, **kwargs):
        """
        Initialize v3 player with turn planning support.
        
        Args:
            ai_version: Deprecated. Use planner_mode instead.
            planner_mode: 'single' or 'dual'. If None, derived from ai_version or env.
            **kwargs: Passed to LLMPlayer (provider, api_key, model)
        """
        super().__init__(**kwargs)
        
        from .turn_planner import TurnPlanner, ai_version_to_planner_mode, get_planner_mode

        # Determine planner mode: explicit arg > legacy ai_version > env var.
        if planner_mode:
            self.planner_mode = planner_mode
        elif ai_version is not None:
            self.planner_mode = ai_version_to_planner_mode(ai_version)
        else:
            self.planner_mode = get_planner_mode()
        
        # v3: Turn plan state
        self._current_plan: Optional['TurnPlan'] = None
        self._plan_action_index: int = 0
        self._completed_actions: List['PlannedAction'] = []
        self._plan_turn_number: Optional[int] = None  # Track which turn the plan is for
        self._execution_log: List[Dict[str, Any]] = []  # Track execution attempts
        
        self.turn_planner = TurnPlanner(
            client=self.client,
            provider_client=self.provider_client,
            provider=self.provider,
            model_name=self.model_name,
            fallback_model=self.fallback_model,
            planner_mode=self.planner_mode,
        )
        
        logger.debug(
            "Initialized LLMPlayerV3 (planner_mode=%s, model: %s)",
            self.planner_mode,
            self.model_name,
        )
    
    def select_action(
        self,
        game_state: 'GameState',
        ai_player_id: str,
        valid_actions: list['ValidAction'],
        game_engine=None
    ) -> Optional[tuple[int, str]]:
        """
        Select the best action using two-phase planning.
        
        Phase 1: If no plan exists for this turn, create one
        Phase 2: Execute the next action from the plan
        
        Args:
            game_state: Current game state
            ai_player_id: ID of the AI player
            valid_actions: List of valid actions
            game_engine: Optional GameEngine for stats
            
        Returns:
            Tuple of (action_index, reasoning) or None
        """
        if not valid_actions:
            logger.warning("No valid actions available for AI")
            return None
        
        logger.debug(f"🤖 AI v3 Turn {game_state.turn_number} - {len(valid_actions)} actions available")
        
        # Check if we need a new plan
        if self._needs_new_plan(game_state):
            self._create_turn_plan(game_state, ai_player_id, game_engine)
        
        # Execute next action from plan
        if self._current_plan and self._plan_action_index < len(self._current_plan.action_sequence):
            return self._execute_planned_action(valid_actions, game_state, ai_player_id, game_engine)
        else:
            # Plan exhausted or no plan - fall back to v2 behavior
            logger.warning("No plan available, falling back to v2 action selection")
            return super().select_action(game_state, ai_player_id, valid_actions, game_engine)
    
    def _needs_new_plan(self, game_state: 'GameState') -> bool:
        """Check if we need to create a new turn plan."""
        # No plan yet
        if self._current_plan is None:
            return True
        
        # Plan is exhausted
        if self._plan_action_index >= len(self._current_plan.action_sequence):
            return True
        
        # Turn number changed (new turn started)
        if self._plan_turn_number != game_state.turn_number:
            logger.debug(f"🔄 New turn detected ({self._plan_turn_number} → {game_state.turn_number}), creating new plan")
            return True
        
        return False
    
    def _create_turn_plan(
        self,
        game_state: 'GameState',
        ai_player_id: str,
        game_engine
    ) -> None:
        """Create a new turn plan."""
        logger.debug("📋 Creating new turn plan...")
        
        try:
            plan = self.turn_planner.create_plan(
                game_state=game_state,
                player_id=ai_player_id,
                game_engine=game_engine
            )
            
            if plan:
                self._current_plan = plan
                self._plan_action_index = 0
                self._completed_actions = []
                self._plan_turn_number = game_state.turn_number
                self._execution_log = []  # Reset execution log for new plan
                
                # Log plan summary
                logger.debug(f"✅ Plan created: {len(plan.action_sequence)} actions")
                logger.debug(f"📊 CC: {plan.cc_start} → {plan.cc_after_plan}")
                logger.debug(f"🎯 Expected cards slept: {plan.expected_cards_slept}")
                logger.debug(f"💡 Strategy: {plan.selected_strategy[:100]}...")
                
                for i, action in enumerate(plan.action_sequence):
                    logger.debug(f"  {i+1}. {action.action_type}: {action.card_name or 'N/A'} ({action.cc_cost} CC)")
            else:
                logger.warning("Failed to create plan, will use fallback")
                self._current_plan = None
                
        except Exception as e:
            logger.exception(f"Error creating turn plan: {e}")
            self._current_plan = None
    
    def _execute_planned_action(
        self,
        valid_actions: list['ValidAction'],
        game_state: 'GameState',
        ai_player_id: str,
        game_engine
    ) -> Optional[tuple[int, str]]:
        """Execute the next action from the current plan."""
        from .prompts import (
            find_matching_action_index,
            get_execution_prompt,
            format_valid_actions_for_ai,
            EXECUTION_JSON_SCHEMA,
        )
        
        planned_action = self._current_plan.action_sequence[self._plan_action_index]
        
        logger.debug(f"🎬 Executing plan step {self._plan_action_index + 1}/{len(self._current_plan.action_sequence)}")
        logger.debug(f"   Planned: {planned_action.action_type} {planned_action.card_name or ''}")
        
        # First, try heuristic matching (no LLM call needed)
        action_index = find_matching_action_index(planned_action, valid_actions)
        
        if action_index is not None:
            # Found match without LLM
            selected_action = valid_actions[action_index]
            reasoning = f"[v3 Plan] {planned_action.reasoning}"
            
            # Handle targets from plan
            if planned_action.target_ids:
                self._last_target_ids = planned_action.target_ids
            
            self._advance_plan(planned_action)
            
            # Log successful execution
            # For end_turn, mark as confirmed immediately since there's no execution step that can fail
            execution_confirmed = planned_action.action_type == "end_turn"
            self._execution_log.append({
                "action_index": self._plan_action_index - 1,  # Already advanced
                "planned_action": f"{planned_action.action_type} {planned_action.card_name or ''}",
                "status": "success",
                "method": "heuristic",
                "execution_confirmed": execution_confirmed,
            })
            
            logger.debug(f"✅ Matched action (heuristic): {selected_action.description}")
            return (action_index, reasoning)
        
        # Heuristic didn't match — check if the action is even possible before
        # burning an LLM execution call on something that can't be done.
        if not self._is_action_available(planned_action, valid_actions):
            logger.debug(
                f"   Skipping unavailable planned action: "
                f"{planned_action.action_type} {planned_action.card_name or ''}"
            )
            self._advance_plan(planned_action)
            # Try the next step in the plan without a new LLM call
            if self._plan_action_index < len(self._current_plan.action_sequence):
                return self._execute_planned_action(valid_actions, game_state, ai_player_id, game_engine)
            # Plan exhausted by skipping — find end_turn as the guaranteed safe fallback.
            # This prevents a None return that cascades to "AI failed to select action".
            for i, action in enumerate(valid_actions):
                if "end turn" in action.description.lower():
                    logger.debug("   Plan exhausted by skipping, falling back to end_turn")
                    return (i, "[v3] Plan exhausted, ending turn")
            return None

        # Heuristic didn't match but action type IS available - use LLM to resolve
        logger.debug("   Using LLM to match action...")

        # Log that heuristic matching fell back to LLM
        self._execution_log.append({
            "action_index": self._plan_action_index,
            "planned_action": f"{planned_action.action_type} {planned_action.card_name or ''}",
            "status": "fallback_to_llm",
            "reason": "Action not available (heuristic match failed)",
        })
        
        ai_player = game_state.players[ai_player_id]
        valid_actions_text = format_valid_actions_for_ai(
            valid_actions, game_state, ai_player_id, game_engine
        )
        
        execution_prompt = get_execution_prompt(
            planned_action=planned_action,
            action_index=self._plan_action_index,
            total_actions=len(self._current_plan.action_sequence),
            valid_actions_text=valid_actions_text,
            current_cc=ai_player.cc,
            num_valid_actions=len(valid_actions),
        )
        
        try:
            response_text = self._call_execution_api(execution_prompt)
            response_data = json.loads(response_text)
            
            action_number = response_data.get("action_number")
            reasoning = response_data.get("reasoning", "No reasoning")
            target_ids = response_data.get("target_ids")
            alternative_cost_id = response_data.get("alternative_cost_id")
            
            if action_number is None or action_number < 1 or action_number > len(valid_actions):
                logger.error(f"Invalid action number from LLM: {action_number}")
                return self._handle_plan_failure(valid_actions, planned_action, "Invalid action number")
            
            action_index = action_number - 1
            selected_action = valid_actions[action_index]
            
            # Store target selections
            if target_ids:
                self._last_target_ids = target_ids
            if alternative_cost_id:
                self._last_alternative_cost_id = alternative_cost_id
            
            self._advance_plan(planned_action)
            
            # Update execution log with LLM success
            # For end_turn, mark as confirmed immediately since there's no execution step that can fail
            update_data = {
                "status": "success",
                "method": "llm",
            }
            if planned_action.action_type == "end_turn":
                update_data["execution_confirmed"] = True
            self._execution_log[-1].update(update_data)
            
            logger.debug(f"✅ Matched action (LLM): {selected_action.description}")
            return (action_index, f"[v3 Plan] {reasoning}")
            
        except Exception as e:
            logger.exception(f"Error executing planned action: {e}")
            # Update execution log with failure
            if self._execution_log and self._execution_log[-1]["action_index"] == self._plan_action_index:
                self._execution_log[-1].update({
                    "status": "failed",
                    "reason": f"Action not available: {str(e)}",
                })
            return self._handle_plan_failure(valid_actions, planned_action, str(e))
    
    def _is_action_available(self, planned_action: 'PlannedAction', valid_actions: list) -> bool:
        """
        Loose availability check: does any valid action correspond to the planned one?

        Returns False when the action is provably impossible right now (e.g., the card
        can't be afforded, opponent has toys blocking a direct attack that was already
        cleared in the plan, etc.).  When False, execution skips the step instead of
        calling the LLM with a request it cannot fulfill.
        """
        action_type = planned_action.action_type
        card_name = (planned_action.card_name or "").lower()
        for action in valid_actions:
            desc = action.description.lower()
            if action_type == "end_turn" and "end turn" in desc:
                return True
            if action_type == "play_card" and card_name and f"play {card_name}" in desc:
                return True
            if action_type == "tussle" and "tussle" in desc:
                return True
            if action_type == "direct_attack" and "direct attack" in desc:
                return True
            if action_type == "activate_ability" and card_name and card_name in desc:
                return True
        return False

    def _call_execution_api(self, prompt: str) -> str:
        """Call LLM API for action execution matching."""
        from .prompts import EXECUTION_JSON_SCHEMA

        return self.provider_client.generate_json(
            prompt,
            EXECUTION_JSON_SCHEMA,
            temperature=0.3,
            max_output_tokens=1024,
            retry_count=3,
            allow_fallback=True,
            model=self.model_name,
            fallback_model=self.fallback_model,
        )
    
    def _advance_plan(self, completed_action: 'PlannedAction') -> None:
        """Move to the next action in the plan."""
        self._completed_actions.append(completed_action)
        self._plan_action_index += 1
        
        if self._plan_action_index >= len(self._current_plan.action_sequence):
            logger.debug("📋 Plan completed!")
    
    def record_execution_result(self, success: bool, error_message: str = None) -> None:
        """Record the actual execution result for the last attempted action."""
        if not self._execution_log:
            return
        
        # Find the most recent log entry that was attempted (not 'not attempted')
        last_attempted_idx = None
        for i in range(len(self._execution_log) - 1, -1, -1):
            if self._execution_log[i].get("status") in ("success", "failed", "fallback_to_llm"):
                last_attempted_idx = i
                break
        
        if last_attempted_idx is not None:
            if success:
                # Keep success status, but add confirmation
                self._execution_log[last_attempted_idx]["execution_confirmed"] = True
            else:
                # Update to show execution failure
                self._execution_log[last_attempted_idx]["status"] = "execution_failed"
                self._execution_log[last_attempted_idx]["reason"] = error_message or "Action execution failed"
                logger.warning(f"Action execution failed: {error_message}")
    
    def _handle_plan_failure(
        self,
        valid_actions: list['ValidAction'],
        failed_action: 'PlannedAction',
        failure_reason: str
    ) -> Optional[tuple[int, str]]:
        """Handle when a planned action can't be executed."""
        logger.warning(f"Plan deviation: {failure_reason}")
        
        # Skip to end_turn if available
        for i, action in enumerate(valid_actions):
            if "end turn" in action.description.lower():
                logger.debug("Falling back to end_turn")
                self._current_plan = None  # Invalidate plan
                return (i, f"[v3 Fallback] Plan failed: {failure_reason}")
        
        # Fall back to v2 selection
        logger.debug("Falling back to v2 action selection")
        self._current_plan = None
        return None
    
    def reset_plan(self) -> None:
        """Reset the current plan (call at start of turn if needed)."""
        self._current_plan = None
        self._plan_action_index = 0
        self._completed_actions = []
        self._plan_turn_number = None
    
    def get_last_decision_info(self) -> Dict[str, Any]:
        """Get information about the last AI decision including plan info."""
        info = super().get_last_decision_info()
        
        # Add turn plan info
        if self._current_plan:
            planner_mode = getattr(self.turn_planner, "planner_mode", "single") if self.turn_planner else "single"

            plan_info: Dict[str, Any] | None = None
            if getattr(self, "turn_planner", None) and hasattr(self.turn_planner, "get_last_plan_info"):
                plan_info = self.turn_planner.get_last_plan_info()
            
            # Format action sequence for logging
            action_sequence = []
            for action in self._current_plan.action_sequence:
                action_sequence.append({
                    "action_type": action.action_type,
                    "card_name": action.card_name,
                    "target_names": action.target_names,
                    "cc_cost": action.cc_cost,
                    "reasoning": action.reasoning,
                })
            
            info["v3_plan"] = {
                "planner_mode": planner_mode,
                # Backward compat: map planner_mode back to version ints for DB/admin
                "ai_version": 4 if planner_mode == "dual" else 3,
                "strategy": self._current_plan.selected_strategy,
                "total_actions": len(self._current_plan.action_sequence),
                "current_action": self._plan_action_index,
                "cc_start": self._current_plan.cc_start,
                "cc_after_plan": self._current_plan.cc_after_plan,
                "expected_cards_slept": self._current_plan.expected_cards_slept,
                "cc_efficiency": self._current_plan.cc_efficiency,
                # Full action sequence for debugging
                "action_sequence": action_sequence,
                # Planning prompt and response (from turn planner, if available)
                "planning_prompt": (
                    plan_info.get("prompt")
                    if plan_info
                    else (getattr(self, "turn_planner", None) and getattr(self.turn_planner, "_last_prompt", None))
                ),
                "planning_response": (
                    plan_info.get("response")
                    if plan_info
                    else (getattr(self, "turn_planner", None) and getattr(self.turn_planner, "_last_response", None))
                ),
                # V4 dual-request visibility (when AI_VERSION=4)
                "v4_request1_prompt": plan_info.get("v4_request1_prompt") if plan_info else None,
                "v4_request1_response": plan_info.get("v4_request1_response") if plan_info else None,
                "v4_request2_prompt": plan_info.get("v4_request2_prompt") if plan_info else None,
                "v4_request2_response": plan_info.get("v4_request2_response") if plan_info else None,
                "v4_metrics": plan_info.get("v4_metrics") if plan_info else None,
                "v4_turn_debug": plan_info.get("v4_turn_debug") if plan_info else None,
                # Execution tracking
                "execution_log": self._execution_log if self._execution_log else None,
            }
        else:
            # Plan failed or not yet generated — still identify as v3 so admin UI
            # shows the correct AI version instead of falling back to "v2".
            planner_mode = getattr(self.turn_planner, "planner_mode", "single") if self.turn_planner else "single"
            info["v3_plan"] = {
                "planner_mode": planner_mode,
                "ai_version": 4 if planner_mode == "dual" else 3,
                "total_actions": 0,
                "current_action": None,
                "planning_prompt": getattr(self.turn_planner, "_last_prompt", None) if self.turn_planner else None,
                "planning_response": getattr(self.turn_planner, "_last_response", None) if self.turn_planner else None,
            }
        
        return info


# Singleton instances
_ai_players: Dict[tuple, LLMPlayer] = {}


def get_ai_player(provider: str = None, version: int = None, planner_mode: str = None) -> LLMPlayer:
    """
    Get the singleton AI player instance.
    
    Args:
        provider: Optional provider override
        version: AI version (2 for per-action, >= 3 for turn planning).
                 If None, reads from AI_VERSION env var (default: 3)
        planner_mode: 'single' or 'dual'. Overrides version-based derivation.
    
    Returns:
        LLMPlayer or LLMPlayerV3 instance
    """
    global _ai_players
    
    # Use environment default if version not specified
    if version is None:
        version = get_default_ai_version()
    provider_name = provider or get_default_provider_name()

    # Derive planner_mode from version when not explicitly given.
    effective_mode = planner_mode
    if effective_mode is None and version >= 3:
        from .turn_planner import ai_version_to_planner_mode
        effective_mode = ai_version_to_planner_mode(version)

    cache_key = (provider_name, effective_mode or "v2")
    
    if version >= 3:
        if cache_key not in _ai_players:
            logger.debug("🤖 Initializing AI player (planner_mode=%s)", effective_mode)
            _ai_players[cache_key] = LLMPlayerV3(provider=provider_name, planner_mode=effective_mode)
        return _ai_players[cache_key]
    else:
        if cache_key not in _ai_players:
            logger.debug("🤖 Initializing AI player v2 (per-action)")
            _ai_players[cache_key] = LLMPlayer(provider=provider_name)
        return _ai_players[cache_key]


def get_ai_player_v3(provider: str = None) -> LLMPlayerV3:
    """
    Get the singleton v3 AI player instance.
    
    Convenience function for getting the two-phase planning AI.
    
    Returns:
        LLMPlayerV3 instance
    """
    return get_ai_player(provider=provider, version=3)


def get_llm_response(prompt: str, is_json: bool = True, provider: str = None) -> str:
    """
    Get a response from the LLM for a custom prompt.
    
    This is a utility function for getting LLM responses outside of game action selection,
    such as generating narratives or other creative text.
    
    Args:
        prompt: The prompt to send to the LLM
        is_json: Whether to expect and parse JSON response (default: True)
        provider: Optional provider override
    
    Returns:
        The LLM response text (parsed from JSON if is_json=True)
    """
    ai_player = get_ai_player(provider)

    response_text = ai_player.provider_client.generate_text(
        prompt,
        temperature=0.8,
        max_output_tokens=2048,
        retry_count=3,
        allow_fallback=True,
        model=ai_player.model_name,
        fallback_model=ai_player.fallback_model,
    )
    
    if is_json:
        # Parse JSON response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        return json.loads(response_text)
    
    return response_text
