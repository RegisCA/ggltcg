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
import time
from typing import Optional, Dict, Any, Literal, List
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


# AI Version Configuration
# Set AI_VERSION=3 to enable turn planning (v3)
# Default is v2 (per-action decisions)
def get_default_ai_version() -> int:
    """Get the default AI version from environment."""
    version_str = os.getenv("AI_VERSION", "2")
    try:
        return int(version_str)
    except ValueError:
        logger.warning(f"Invalid AI_VERSION '{version_str}', defaulting to 2")
        return 2


class LLMPlayer:
    """
    AI player powered by Gemini API.
    
    Uses an LLM to analyze game state and select optimal actions.
    Version 2.0: Now supports multi-target selection and Gemini structured output.
    """
    
    def __init__(
        self,
        provider: Literal["gemini"] = "gemini",
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize the AI player.
        
        Args:
            provider: LLM provider to use (only "gemini" supported)
            api_key: API key (reads from env var if not provided)
            model: Model to use (provider-specific defaults if not provided)
        """
        self.provider = "gemini"
        
        # Store last target/alternative cost selections from LLM
        # v2.0: target_ids is now a list for multi-target support (Sun card)
        self._last_target_ids: Optional[List[str]] = None
        self._last_alternative_cost_id: Optional[str] = None
        
        # Store last prompt/response for logging
        self._last_prompt: Optional[str] = None
        self._last_response: Optional[str] = None
        self._last_action_number: Optional[int] = None
        self._last_reasoning: Optional[str] = None
        
        from google import genai
        
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter. Get a free key at: "
                "https://aistudio.google.com/apikey"
            )
        
        # Create explicit client (new SDK pattern)
        self.client = genai.Client(api_key=self.api_key)
        
        # Allow model override via environment variable or parameter
        # Default: gemini-2.0-flash-lite (30 RPM, best free tier quotas)
        # Alternative: gemini-2.0-flash (10 RPM, stable)
        # Default: gemini-2.5-flash-lite (15 RPM, production default)
        default_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        self.model_name = model or default_model
        
        # Fallback model for capacity issues (configurable via env var)
        # Default: gemini-2.5-flash-lite (15 RPM, better capacity availability)
        self.fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")
        
        logger.debug(f"Initializing Gemini with model: {self.model_name}")
        logger.debug(f"Fallback model (for 429 errors): {self.fallback_model}")
    
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
            logger.debug(f"Calling Gemini API ({self.model_name})...")
            
            response_text = self._call_gemini(prompt)
            
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
    
    def _call_gemini(self, prompt: str, retry_count: int = 3, allow_fallback: bool = True) -> str:
        """
        Call Google Gemini API with structured output mode and retry logic.
        
        v2.0: Uses google-genai SDK with native structured output mode
        and Pydantic schema for reliable, type-safe responses.
        
        Args:
            prompt: The prompt to send
            retry_count: Number of retries for 429 errors (default: 3)
            allow_fallback: Whether to fallback to GEMINI_FALLBACK_MODEL on capacity issues (default: True)
            
        Returns:
            The API response text (valid JSON)
            
        Raises:
            Exception if all retries and fallbacks fail
        """
        from google.genai import types
        
        last_exception = None
        current_model = self.model_name
        
        for attempt in range(retry_count):
            try:
                # v2.0: Use google-genai SDK with structured output
                # Combines system instruction + user prompt into contents
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=f"{SYSTEM_PROMPT}\n\n{prompt}")]
                        )
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=4096,
                        response_mime_type="application/json",
                        response_json_schema=AI_DECISION_JSON_SCHEMA,
                    )
                )
                
                # Log response metadata for debugging
                logger.debug(f"Gemini response candidates: {len(response.candidates) if response.candidates else 0}")
                
                # Check if response was blocked or empty
                if not response.candidates or not response.candidates[0].content.parts:
                    finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
                    
                    logger.error(f"Gemini returned empty response")
                    logger.error(f"Finish reason: {finish_reason}")
                    
                    raise ValueError(
                        f"Gemini returned empty response (finish_reason: {finish_reason}). "
                        "This may be due to safety filters. Try again or adjust the prompt."
                    )
                
                result = response.text.strip()
                logger.debug(f"Gemini structured output response length: {len(result)} characters")
                logger.debug(f"Gemini structured output: {result}")
                return result
                
            except Exception as e:
                error_str = str(e)
                last_exception = e
                
                # Check if it's a 429 Resource Exhausted error
                if "429" in error_str or "ResourceExhausted" in error_str or "Resource exhausted" in error_str:
                    if attempt < retry_count - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        wait_time = 2 ** attempt
                        logger.warning(
                            f"Gemini API capacity issue (429 Resource Exhausted). "
                            f"Retry {attempt + 1}/{retry_count} after {wait_time}s..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        # All retries exhausted - try fallback model if enabled
                        if allow_fallback and current_model != self.fallback_model:
                            logger.warning(
                                f"Gemini {current_model} capacity exhausted after {retry_count} retries. "
                                f"Falling back to {self.fallback_model} (more stable, better availability)..."
                            )
                            # Switch to fallback model (just update the model name, client stays same)
                            self.model_name = self.fallback_model
                            current_model = self.fallback_model
                            # Try one more time with fallback model
                            return self._call_gemini(prompt, retry_count=1, allow_fallback=False)
                        else:
                            logger.error(
                                f"Gemini API capacity exhausted after {retry_count} retries. "
                                f"This is a Google infrastructure issue, not a rate limit. "
                                f"Consider trying again in a few minutes."
                            )
                else:
                    # Not a 429 error, don't retry
                    logger.exception(f"Gemini API call failed: {e}")
                
                raise last_exception
        
        # If we get here, all retries failed
        raise last_exception
    
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
        # Map Gemini models to friendly names
        model_map = {
            "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
            "gemini-2.0-flash": "Gemini 2.0 Flash",
            "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
            "gemini-3-flash-preview": "Gemini 3 Flash (Preview)",
            "gemini-1.5-flash": "Gemini 1.5 Flash",
            "gemini-1.5-pro": "Gemini 1.5 Pro",
        }
        return model_map.get(self.model_name, f"Gemini ({self.model_name})")


class LLMPlayerV3(LLMPlayer):
    """
    AI player v3 with two-phase turn planning.
    
    Phase 1: Generate complete turn plan with CC budgeting
    Phase 2: Execute each action from the plan sequentially
    
    Inherits from LLMPlayer for API calls and action execution.
    """
    
    def __init__(self, ai_version: int = None, **kwargs):
        """
        Initialize v3 player with turn planning support.
        
        Args:
            ai_version: AI version to use (3 or 4). If None, reads from AI_VERSION env var.
            **kwargs: Passed to LLMPlayer (provider, api_key, model)
        """
        super().__init__(**kwargs)
        
        # Determine AI version - parameter overrides env var
        import os
        self.ai_version = ai_version if ai_version is not None else int(os.getenv("AI_VERSION", "3"))
        
        # v3: Turn plan state
        self._current_plan: Optional['TurnPlan'] = None
        self._plan_action_index: int = 0
        self._completed_actions: List['PlannedAction'] = []
        self._plan_turn_number: Optional[int] = None  # Track which turn the plan is for
        self._execution_log: List[Dict[str, Any]] = []  # Track execution attempts
        
        # Import turn planner
        from .turn_planner import TurnPlanner
        self.turn_planner = TurnPlanner(
            client=self.client,
            model_name=self.model_name,
            fallback_model=self.fallback_model,
            ai_version=self.ai_version
        )
        
        logger.debug(f"Initialized LLMPlayerV3 (AI v{self.ai_version}, model: {self.model_name})")
    
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
        
        # Heuristic didn't match - use LLM to find action
        logger.debug("   Using LLM to match action...")
        
        # Log that heuristic matching failed
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
    
    def _call_execution_api(self, prompt: str) -> str:
        """Call LLM API for action execution matching."""
        from google.genai import types
        from .prompts import EXECUTION_JSON_SCHEMA
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.3,  # Lower temperature for execution (more deterministic)
                max_output_tokens=1024,
                response_mime_type="application/json",
                response_json_schema=EXECUTION_JSON_SCHEMA,
            )
        )
        
        return response.text.strip()
    
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
        
        # Add turn plan info (v3 or v4)
        if self._current_plan:
            # Determine actual AI version used
            from .turn_planner import get_ai_version
            actual_ai_version = int(get_ai_version())
            
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
                "ai_version": actual_ai_version,  # Track actual version used
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
                "planning_prompt": getattr(self, 'turn_planner', None) and getattr(self.turn_planner, '_last_prompt', None),
                "planning_response": getattr(self, 'turn_planner', None) and getattr(self.turn_planner, '_last_response', None),
                # Execution tracking
                "execution_log": self._execution_log if self._execution_log else None,
            }
        
        return info


# Singleton instances
_ai_player: Optional[LLMPlayer] = None
_ai_player_v3: Optional[LLMPlayerV3] = None


def get_ai_player(provider: str = None, version: int = None) -> LLMPlayer:
    """
    Get the singleton AI player instance.
    
    Args:
        provider: Optional provider override (ignored, always uses "gemini")
        version: AI version to use (2 for classic, 3 for turn planning).
                 If None, reads from AI_VERSION env var (default: 2)
    
    Returns:
        LLMPlayer or LLMPlayerV3 instance
    """
    global _ai_player, _ai_player_v3
    
    # Use environment default if version not specified
    if version is None:
        version = get_default_ai_version()
    
    if version >= 3:
        if _ai_player_v3 is None:
            logger.debug(f"🤖 Initializing AI player v{version} (turn planning)")
            _ai_player_v3 = LLMPlayerV3(provider="gemini")
        return _ai_player_v3
    else:
        if _ai_player is None:
            logger.debug(f"🤖 Initializing AI player v{version} (per-action)")
            _ai_player = LLMPlayer(provider="gemini")
        return _ai_player


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
        provider: Optional provider override (ignored, always uses "gemini")
    
    Returns:
        The LLM response text (parsed from JSON if is_json=True)
    """
    ai_player = get_ai_player(provider)
    
    # Call Gemini
    from google import genai
    from google.genai import types
    # Create a new client for custom prompts (without system instruction in config)
    client = genai.Client(api_key=ai_player.api_key)
    response = client.models.generate_content(
        model=ai_player.model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.8,  # Higher temperature for creativity
            max_output_tokens=2048,  # Allow longer responses
        )
    )
    response_text = response.text.strip()
    
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
