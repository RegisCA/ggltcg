"""
LLM-powered AI player using Gemini.

Two-phase turn planning:
Phase 1: TurnPlanner generates a complete turn plan (deterministic action-sequence
enumeration + one Gemini strategic-selection call).
Phase 2: Each planned action is matched to an available action — a heuristic
match first, falling back to a small LLM execution call only when ambiguous.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Look for .env in backend directory
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass  # python-dotenv is optional

from game_engine.models.game_state import GameState
from api.schemas import ValidAction
from .providers import build_provider


class LLMPlayer:
    """
    AI player powered by Gemini, using two-phase turn planning (see module docstring).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the AI player.

        Args:
            api_key: Gemini API key (reads from GOOGLE_API_KEY if not provided)
            model: Model to use (defaults to GEMINI_MODEL / providers.DEFAULT_MODEL)
        """
        self.provider_client, config = build_provider(api_key=api_key, model=model)
        self.api_key = config.api_key
        self.model_name = config.model
        self.fallback_model = config.fallback_model
        self.client = getattr(self.provider_client, "client", None)

        from .turn_planner import TurnPlanner

        # Turn plan state
        self._current_plan: Optional['TurnPlan'] = None
        self._plan_action_index: int = 0
        self._completed_actions: List['PlannedAction'] = []
        self._plan_turn_number: Optional[int] = None  # Track which turn the plan is for
        self._execution_log: List[Dict[str, Any]] = []  # Track execution attempts
        self._midturn_replan_count: int = 0  # Re-plans within a single turn (capped at 2)

        # Store last target/alternative cost selections from LLM
        self._last_target_ids: Optional[List[str]] = None
        self._last_alternative_cost_id: Optional[str] = None

        self.turn_planner = TurnPlanner(
            client=self.client,
            provider_client=self.provider_client,
            model_name=self.model_name,
            fallback_model=self.fallback_model,
        )

        logger.debug("Initialized LLMPlayer (model: %s)", self.model_name)
        logger.debug("Fallback model: %s", self.fallback_model)

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

        logger.debug(f"🤖 AI Turn {game_state.turn_number} - {len(valid_actions)} actions available")

        # Check if we need a new plan
        if self._needs_new_plan(game_state):
            self._create_turn_plan(game_state, ai_player_id, game_engine)

        # Execute next action from plan
        if self._current_plan and self._plan_action_index < len(self._current_plan.action_sequence):
            return self._execute_planned_action(valid_actions, game_state, ai_player_id, game_engine)
        else:
            # Plan was exhausted (not absent) — check if a mid-turn re-plan is warranted
            if self._current_plan is not None:
                result = self._maybe_replan(game_state, ai_player_id, valid_actions, game_engine)
                if result is not None:
                    return result
            # No plan, or no re-plan warranted — the enumerator always includes
            # "pass" as a legal sequence, so a missing/exhausted plan just means
            # ending the turn. Find end_turn directly rather than falling back
            # to a second selection path.
            logger.debug("Plan exhausted or absent, ending turn")
            for i, action in enumerate(valid_actions):
                if action.action_type == "end_turn" or "end turn" in action.description.lower():
                    return (i, "[fallback] Plan exhausted, ending turn")
            return None

    def _needs_new_plan(self, game_state: 'GameState') -> bool:
        """Check if we need to create a new turn plan.

        Note: a plan being exhausted mid-turn is NOT a trigger for re-planning.
        When all planned actions have been selected, the caller falls through to
        end_turn.  Re-planning mid-turn would reset _execution_log and produce
        duplicate plan DB entries for the same turn.
        """
        # No plan yet
        if self._current_plan is None:
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
        # Reset mid-turn re-plan counter only for a genuinely new turn
        if self._plan_turn_number is None or self._plan_turn_number != game_state.turn_number:
            self._midturn_replan_count = 0
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
                logger.debug(f"📊 Charge: {plan.charge_start} → {plan.charge_after_plan}")
                logger.debug(f"🎯 Expected cards broken: {plan.expected_cards_broken}")
                logger.debug(f"💡 Strategy: {plan.selected_strategy[:100]}...")

                for i, action in enumerate(plan.action_sequence):
                    logger.debug(f"  {i+1}. {action.action_type}: {action.card_name or 'N/A'} ({action.charge_cost} Charge)")
            else:
                logger.warning("Failed to create plan, will use fallback")
                self._current_plan = None

        except Exception as e:
            logger.exception(f"Error creating turn plan: {e}")
            self._current_plan = None

    def _maybe_replan(
        self,
        game_state: 'GameState',
        ai_player_id: str,
        valid_actions: list['ValidAction'],
        game_engine,
    ) -> Optional[tuple[int, str]]:
        """Trigger a mid-turn re-plan when combat options remain but the plan is exhausted.

        Only re-plans when ALL of:
        - Player has > 1 Charge remaining (minimum for tussle/direct_attack)
        - At least one tussle or direct_attack is in valid_actions
        - Re-plan count for this turn is < 2 (prevents infinite loops)
        """
        ai_player = game_state.players[ai_player_id]

        if self._midturn_replan_count >= 2:
            logger.debug(
                "⏭️ Mid-turn re-plan limit reached (%d/2), skipping",
                self._midturn_replan_count,
            )
            return None

        has_combat = any(
            a.action_type in ("tussle", "direct_attack") for a in valid_actions
        )
        if ai_player.charge <= 1 or not has_combat:
            logger.debug(
                "⏭️ No re-plan warranted: Charge=%d, combat_available=%s",
                ai_player.charge,
                has_combat,
            )
            return None

        self._midturn_replan_count += 1
        logger.debug(
            "🔄 Mid-turn re-plan #%d (Charge=%d, combat actions available)",
            self._midturn_replan_count,
            ai_player.charge,
        )

        self._create_turn_plan(game_state, ai_player_id, game_engine)

        if self._current_plan and self._plan_action_index < len(self._current_plan.action_sequence):
            return self._execute_planned_action(valid_actions, game_state, ai_player_id, game_engine)

        return None

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
            reasoning = f"[plan] {planned_action.reasoning}"

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
                desc = action.description.lower()
                if action.action_type == "end_turn" or "end turn" in desc:
                    logger.debug("   Plan exhausted by skipping, falling back to end_turn")
                    return (i, "[fallback] Plan exhausted, ending turn")
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
            current_charge=ai_player.charge,
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
            return (action_index, f"[plan] {reasoning}")

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
            if action_type == "end_turn" and (
                action.action_type == "end_turn" or "end turn" in desc
            ):
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
            if action.action_type == "end_turn":
                logger.debug("Falling back to end_turn")
                self._current_plan = None  # Invalidate plan
                return (i, f"[fallback] Plan failed: {failure_reason}")

        self._current_plan = None
        return None

    def reset_plan(self) -> None:
        """Reset the current plan (call at start of turn if needed)."""
        self._current_plan = None
        self._plan_action_index = 0
        self._completed_actions = []
        self._plan_turn_number = None

    def get_last_decision_info(self) -> Dict[str, Any]:
        """Get information about the last AI decision, including the turn plan."""
        from .prompts import PROMPTS_VERSION

        info: Dict[str, Any] = {
            "model_name": self.model_name,
            "prompts_version": PROMPTS_VERSION,
            "action_number": None,
            "reasoning": None,
            "prompt": None,
            "response": None,
        }

        plan_info: Dict[str, Any] | None = None
        if getattr(self, "turn_planner", None) and hasattr(self.turn_planner, "get_last_plan_info"):
            plan_info = self.turn_planner.get_last_plan_info()

        if plan_info:
            info["prompt"] = plan_info.get("prompt")
            info["response"] = plan_info.get("response")

        if self._current_plan:
            # Format action sequence for logging
            action_sequence = [
                {
                    "action_type": action.action_type,
                    "card_name": action.card_name,
                    "target_names": action.target_names,
                    "charge_cost": action.charge_cost,
                    "reasoning": action.reasoning,
                }
                for action in self._current_plan.action_sequence
            ]

            info["plan"] = {
                "planner": "enum",
                "strategy": self._current_plan.selected_strategy,
                "total_actions": len(self._current_plan.action_sequence),
                "current_action": self._plan_action_index,
                "charge_start": self._current_plan.charge_start,
                "charge_after_plan": self._current_plan.charge_after_plan,
                "expected_cards_broken": self._current_plan.expected_cards_broken,
                "action_sequence": action_sequence,
                "planning_prompt": plan_info.get("prompt") if plan_info else None,
                "planning_response": plan_info.get("response") if plan_info else None,
                "selection_prompt": plan_info.get("selection_prompt") if plan_info else None,
                "selection_response": plan_info.get("selection_response") if plan_info else None,
                "selection_system_instruction": plan_info.get("selection_system_instruction") if plan_info else None,
                "enum_debug": plan_info.get("enum_debug") if plan_info else None,
                "execution_log": self._execution_log if self._execution_log else None,
            }
        else:
            # Plan failed or not yet generated — still surface a plan dict so
            # the admin UI groups this log under the planner view.
            info["plan"] = {
                "planner": "enum",
                "total_actions": 0,
                "current_action": None,
                "planning_prompt": plan_info.get("prompt") if plan_info else None,
                "planning_response": plan_info.get("response") if plan_info else None,
            }

        return info

    def _filter_to_valid_targets(
        self,
        requested_ids: Optional[List[str]],
        valid_options: Optional[List[str]],
    ) -> List[str]:
        """
        Drop any AI-requested target IDs that aren't in the validated option list.

        The LLM picks an action by number from a menu whose target_options is
        already restricted to legal targets (e.g. Copy can only ever list the
        player's own cards), but the model's free-form JSON can still name a
        different ID it saw elsewhere in the prompt (e.g. an opponent's card).
        Without this check that hallucinated ID would be sent straight to the
        API, where it's rejected and the AI's turn is wasted instead of
        silently falling back to a legal target.
        """
        if not requested_ids or not valid_options:
            return requested_ids or []

        valid_set = set(valid_options)
        filtered = [t for t in requested_ids if t in valid_set]
        if filtered != requested_ids:
            logger.warning(
                f"AI selected target(s) outside the valid option list (likely "
                f"hallucination); dropping invalid ones. Requested: {requested_ids}, "
                f"valid: {valid_options}, kept: {filtered}"
            )
        return filtered

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

            # target_ids is a list to support multi-target cards (e.g. Sun)
            valid_ids = self._filter_to_valid_targets(self._last_target_ids, selected_action.target_options)
            if valid_ids:
                result["target_ids"] = valid_ids
                logger.debug(f"Using AI-selected targets ({len(valid_ids)}): {valid_ids}")
            elif selected_action.target_options:
                # Fallback: Use first available target if AI didn't specify (or specified
                # only invalid ones)
                result["target_ids"] = [selected_action.target_options[0]]
                logger.warning(f"AI didn't specify a valid target, using first option: {result['target_ids']}")

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
            valid_defender_ids = self._filter_to_valid_targets(self._last_target_ids, selected_action.target_options)
            if valid_defender_ids:
                result["defender_id"] = valid_defender_ids[0]  # Use first target for tussle
                logger.debug(f"Using AI-selected tussle target: {valid_defender_ids[0]}")
            elif selected_action.target_options:
                # Check if this is a direct attack or targeted tussle
                if selected_action.target_options[0] == "direct_attack":
                    result["defender_id"] = None  # Direct attack
                else:
                    result["defender_id"] = selected_action.target_options[0]
                    logger.warning(f"AI didn't specify a valid tussle target, using first option: {result['defender_id']}")
            else:
                result["defender_id"] = None  # Direct attack

        elif selected_action.action_type == "activate_ability":
            result["action_type"] = "activate_ability"
            result["card_id"] = selected_action.card_id
            result["amount"] = 1  # Always use 1 for now (can be repeated)

            # Handle target selection for activated abilities (still single target)
            valid_ability_target_ids = self._filter_to_valid_targets(self._last_target_ids, selected_action.target_options)
            if valid_ability_target_ids:
                result["target_id"] = valid_ability_target_ids[0]  # Use first target for ability
                logger.debug(f"Using AI-selected ability target: {valid_ability_target_ids[0]}")
            elif selected_action.target_options:
                # Fallback: Use first available target if AI didn't specify (or specified
                # only invalid ones)
                result["target_id"] = selected_action.target_options[0]
                logger.warning(f"AI didn't specify a valid ability target, using first option: {result['target_id']}")

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
            String like "Gemini Flash Lite (Latest)"
        """
        return self.provider_client.get_display_name(self.model_name)


# Singleton instance
_ai_player: Optional[LLMPlayer] = None


def get_ai_player() -> LLMPlayer:
    """
    Get the singleton AI player instance (Gemini, enum-based planning).
    """
    global _ai_player

    if _ai_player is None:
        logger.debug("🤖 Initializing AI player")
        _ai_player = LLMPlayer()
    return _ai_player


def get_llm_response(prompt: str, is_json: bool = True) -> str:
    """
    Get a response from the LLM for a custom prompt.

    This is a utility function for getting LLM responses outside of game action selection,
    such as generating narratives or other creative text.

    Args:
        prompt: The prompt to send to the LLM
        is_json: Whether to expect and parse JSON response (default: True)

    Returns:
        The LLM response text (parsed from JSON if is_json=True)
    """
    ai_player = get_ai_player()

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
