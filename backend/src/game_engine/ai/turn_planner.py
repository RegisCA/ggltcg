"""
Turn Planner for the AI player.

Generates a complete turn plan each turn:
- Request 1: enumerate every engine-legal action sequence deterministically
  (``enumerator.enumerate_sequences`` — no LLM call, no illegal actions possible).
- Request 2: one Gemini call picks the best sequence strategically
  (``prompts.strategic_selector``).
"""

import json
import logging
from typing import Optional, Dict, Any

from game_engine.models.game_state import GameState
from .prompts import TurnPlan, PlannedAction, PROMPTS_VERSION
from .prompts.sequence_format import add_tactical_labels
from .prompts.strategic_selector import (
    generate_strategic_prompt,
    get_strategic_selector_temperature,
    get_strategic_selector_system_instruction,
    STRATEGIC_SELECTOR_SCHEMA,
    parse_selector_response,
    convert_sequence_to_turn_plan,
)
from .quality_metrics import TurnMetrics, record_turn_metrics
from .providers import GeminiProvider, build_provider
from .enumerator import enumerate_sequences

logger = logging.getLogger(__name__)

PROMPT_TOKEN_ESTIMATE_DIVISOR = 4


class TurnPlanner:
    """
    Generates turn plans via deterministic enumeration + one strategic-selection
    LLM call (see module docstring).
    """

    # Class-level metrics (shared across instances)
    _metrics = {
        "total_turns": 0,
        "success": 0,
        "no_sequences": 0,
        "selection_parse_error": 0,
        "selection_invalid_index": 0,
    }

    @classmethod
    def get_metrics(cls) -> dict:
        """Get planner performance metrics."""
        m = cls._metrics
        total = m["total_turns"] or 1  # Avoid division by zero
        return {
            **m,
            "no_sequences_rate": f"{m['no_sequences'] / total * 100:.1f}%",
        }

    @classmethod
    def reset_metrics(cls):
        """Reset metrics (useful for testing)."""
        for key in cls._metrics:
            cls._metrics[key] = 0

    def __init__(
        self,
        client,
        model_name: str,
        fallback_model: str,
        provider_client: Optional[GeminiProvider] = None,
    ):
        """
        Initialize the TurnPlanner.

        Args:
            client: google-genai Client instance
            model_name: Primary model to use
            fallback_model: Fallback model for capacity issues
            provider_client: Optional pre-built GeminiProvider (tests construct
                this directly to avoid requiring a real API key)
        """
        self.client = client
        self.provider_client = provider_client
        if self.provider_client is None:
            self.provider_client, resolved = build_provider(
                model=model_name,
                fallback_model=fallback_model,
                client=client,
            )
            self.model_name = resolved.model
            self.fallback_model = resolved.fallback_model
        else:
            self.model_name = model_name
            self.fallback_model = fallback_model

        # Store last planning info for debugging
        self._last_prompt: Optional[str] = None
        self._last_response: Optional[str] = None
        self._last_plan: Optional[TurnPlan] = None

        # Strategic-selection request tracking for admin UI
        self._selection_prompt: Optional[str] = None
        self._selection_response: Optional[str] = None
        self._selection_system_instruction: Optional[str] = None

        # Per-turn enumerator/selection diagnostics for admin UI
        self._enum_debug: Optional[Dict[str, Any]] = None

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
            game_engine: Optional GameEngine for calculating effective stats and validation

        Returns:
            TurnPlan object if successful, None if planning failed
        """
        logger.debug(f"🧠 Creating turn plan for Turn {game_state.turn_number}")

        ai_player = game_state.players[player_id]

        TurnPlanner._metrics["total_turns"] += 1

        # Reset per-turn tracking. _last_prompt/_last_response are cleared too
        # (not just the _selection_* mirrors) so that a turn which fails before
        # reaching Request 2 surfaces as "no prompt", not the previous turn's
        # stale prompt/response leaking through get_last_plan_info().
        self._last_prompt = None
        self._last_response = None
        self._selection_prompt = None
        self._selection_response = None
        self._selection_system_instruction = None
        self._enum_debug = {
            "sequences_generated": 0,
            "enumeration_exception": None,
            "selection_parse_error": False,
            "selection_invalid_index": False,
            "selection_index_used": None,
            "selection_exception": None,
            "selection_fallback_used": False,
        }

        # === Request 1: deterministic enumeration ===
        logger.debug("🧮 Enumerating action sequences (deterministic)...")
        try:
            sequences = enumerate_sequences(game_state, player_id)
        except Exception as e:
            logger.error(f"Enumeration failed: {e}", exc_info=True)
            self._enum_debug["enumeration_exception"] = str(e)
            sequences = []
        self._enum_debug["sequences_generated"] = len(sequences)
        logger.debug(f"   Enumerated {len(sequences)} sequences")

        if not sequences:
            logger.warning("⚠️ No sequences enumerated for this turn")
            TurnPlanner._metrics["no_sequences"] += 1
            return None

        sequences = add_tactical_labels(sequences)

        # === Request 2: strategic selection ===
        logger.debug("🎯 Selecting best sequence...")

        select_prompt = generate_strategic_prompt(game_state, player_id, sequences, game_engine)
        select_system_instruction = get_strategic_selector_system_instruction()
        self._last_prompt = select_prompt
        self._selection_prompt = select_prompt
        self._selection_system_instruction = select_system_instruction
        logger.debug(
            "Strategic selector prompt (%s chars, ~%s tokens)",
            len(select_prompt),
            self._estimate_prompt_tokens(select_prompt),
        )

        try:
            select_response = self.provider_client.generate_json(
                select_prompt,
                STRATEGIC_SELECTOR_SCHEMA,
                temperature=get_strategic_selector_temperature(),
                max_output_tokens=self._get_selector_output_budget(),
                retry_count=3,
                allow_fallback=True,
                model=self.model_name,
                fallback_model=self.fallback_model,
                system_instruction=select_system_instruction,
            )
            self._last_response = select_response
            self._selection_response = select_response
            selection = parse_selector_response(select_response)

            selected_index = selection.get("selected_index", 0)
            reasoning = selection.get("reasoning", "No reasoning provided")

            if "Parse error" in reasoning:
                TurnPlanner._metrics["selection_parse_error"] += 1
                self._enum_debug["selection_parse_error"] = True

            if selected_index >= len(sequences):
                selected_index = 0
                logger.warning("Invalid sequence index, using 0")
                self._enum_debug["selection_invalid_index"] = True
                TurnPlanner._metrics["selection_invalid_index"] += 1

            self._enum_debug["selection_index_used"] = selected_index

            selected_sequence = sequences[selected_index]
            logger.debug(f"   Selected sequence {selected_index}: {selected_sequence.get('tactical_label', '?')}")
            logger.debug(f"   Reasoning: {reasoning[:100]}...")

            plan_data = convert_sequence_to_turn_plan(
                selected_sequence, game_state, player_id, reasoning,
                trust_action_costs=True,
            )
            plan = self._parse_plan(plan_data)
            # Enumerated sequences already carry exact, engine-derived Charge
            # (including discounted tussles like Raggy=0 / Wizard=1) — no
            # regrounding pass needed, unlike LLM-generated plans.
            plan.charge_start = ai_player.charge
            self._last_plan = plan

            TurnPlanner._metrics["success"] += 1

            self._log_plan_summary(plan)

            metrics = TurnMetrics.from_plan(plan, game_state, player_id)
            record_turn_metrics(metrics)
            logger.info(f"Turn {metrics.turn_number} metrics: {metrics.to_log_dict()}")

            return plan

        except Exception as e:
            logger.error(f"Strategic selection failed: {e}")
            TurnPlanner._metrics["selection_parse_error"] += 1
            self._enum_debug["selection_exception"] = str(e)
            # Fall back to the first sequence if selection fails
            if sequences:
                self._enum_debug["selection_fallback_used"] = True
                plan_data = convert_sequence_to_turn_plan(
                    sequences[0], game_state, player_id, "Selection failed, using first sequence",
                    trust_action_costs=True,
                )
                plan = self._parse_plan(plan_data)
                plan.charge_start = ai_player.charge
                self._last_plan = plan
                TurnPlanner._metrics["success"] += 1

                metrics = TurnMetrics.from_plan(plan, game_state, player_id)
                record_turn_metrics(metrics)
                logger.info(f"Turn {metrics.turn_number} metrics: {metrics.to_log_dict()}")

                return plan

        return None

    def _estimate_prompt_tokens(self, prompt: str) -> int:
        return max(1, len(prompt) // PROMPT_TOKEN_ESTIMATE_DIVISOR)

    def _get_selector_output_budget(self) -> int:
        return 384

    def _parse_plan(self, plan_data: Dict[str, Any]) -> TurnPlan:
        """
        Parse the JSON response into a TurnPlan object.

        Args:
            plan_data: Parsed JSON dictionary

        Returns:
            TurnPlan object
        """
        # Parse action sequence
        _VALID_ACTION_TYPES = {"play_card", "tussle", "activate_ability", "direct_attack", "end_turn"}

        def _safe_nonneg_int(val, default: int = 0) -> int:
            """Convert to int >= 0. Handles LLM outputting null/None or negative values."""
            try:
                return max(0, int(val)) if val is not None else default
            except (TypeError, ValueError):
                return default

        action_sequence = []
        for action_data in plan_data.get("action_sequence", []):
            # Sanitise action_type — LLMs sometimes output "play" or "attack" instead
            # of the exact Literal values, which causes a Pydantic ValidationError and
            # kills the entire plan.  Default to "end_turn" so the AI at least passes.
            raw_type = action_data.get("action_type", "end_turn")
            action_type = raw_type if raw_type in _VALID_ACTION_TYPES else "end_turn"
            if action_type != raw_type:
                logger.warning(
                    "Invalid action_type from LLM: %r — defaulting to end_turn", raw_type
                )

            # _safe_nonneg_int handles: negative values, JSON null → Python None,
            # and missing keys; all of which would crash Pydantic's ge=0 validator
            # or Python's max() with a TypeError.
            action = PlannedAction(
                action_type=action_type,
                card_id=action_data.get("card_id"),
                card_name=action_data.get("card_name"),
                target_ids=action_data.get("target_ids"),
                target_names=action_data.get("target_names"),
                alternative_cost_id=action_data.get("alternative_cost_id"),
                charge_cost=_safe_nonneg_int(action_data.get("charge_cost")),
                charge_after=_safe_nonneg_int(action_data.get("charge_after")),
                reasoning=action_data.get("reasoning") or "No reasoning provided",
            )
            action_sequence.append(action)

        if not action_sequence or action_sequence[-1].action_type != "end_turn":
            action_sequence.append(
                PlannedAction(
                    action_type="end_turn",
                    card_id=None,
                    card_name=None,
                    target_ids=None,
                    target_names=None,
                    alternative_cost_id=None,
                    charge_cost=0,
                    charge_after=action_sequence[-1].charge_after if action_sequence else plan_data.get("charge_start", 0),
                    reasoning="End turn after planned actions.",
                )
            )

        def _str(val) -> str:
            """Coerce a value to str — guards against the LLM returning a dict/int."""
            if isinstance(val, str):
                return val
            if val is None:
                return ""
            return json.dumps(val)

        # Create TurnPlan
        plan = TurnPlan(
            threat_assessment=_str(plan_data.get("threat_assessment", "")),
            resources_summary=_str(plan_data.get("resources_summary", "")),
            sequences_considered=plan_data.get("sequences_considered", []),
            selected_strategy=_str(plan_data.get("selected_strategy", "")),
            action_sequence=action_sequence,
            charge_start=plan_data.get("charge_start", 0),
            charge_after_plan=plan_data.get("charge_after_plan", 0),
            expected_cards_broken=plan_data.get("expected_cards_broken", 0),
            plan_reasoning=_str(plan_data.get("plan_reasoning", "")),
        )

        return plan

    def _log_plan_summary(self, plan: TurnPlan) -> None:
        """Log a human-readable summary of the plan."""
        logger.debug("=" * 60)
        logger.debug("📋 TURN PLAN GENERATED")
        logger.debug("=" * 60)
        logger.debug(f"Threat Assessment: {plan.threat_assessment[:100]}...")
        logger.debug(f"Selected Strategy: {plan.selected_strategy}")
        logger.debug(f"Charge Budget: {plan.charge_start} → {plan.charge_after_plan}")
        logger.debug(f"Expected cards to break: {plan.expected_cards_broken}")
        logger.debug("-" * 40)
        logger.debug("Action Sequence:")
        for i, action in enumerate(plan.action_sequence, 1):
            card_info = f"{action.card_name or 'N/A'}" if action.card_name else action.card_id or "N/A"
            target_info = ""
            if action.target_names:
                target_info = f" → {', '.join(action.target_names)}"
            elif action.target_ids:
                target_info = f" → {', '.join(action.target_ids[:2])}..."
            logger.debug(f"  {i}. {action.action_type}: {card_info}{target_info} ({action.charge_cost} Charge → {action.charge_after} Charge)")
        logger.debug("=" * 60)

    def get_last_plan_info(self) -> Dict[str, Any]:
        """
        Get information about the last generated plan for debugging.

        Returns:
            Dict with prompt, response, and parsed plan
        """
        info = {
            "prompt": self._last_prompt,
            "response": self._last_response,
            "plan": self._last_plan.model_dump() if self._last_plan else None,
            "prompts_version": PROMPTS_VERSION,
        }

        if self._selection_prompt:
            info["selection_prompt"] = self._selection_prompt
            info["selection_response"] = self._selection_response
            info["selection_system_instruction"] = self._selection_system_instruction

        if self._enum_debug is not None:
            info["enum_debug"] = self._enum_debug

        return info

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
        ai_break_ids = {card.id for card in ai_player.break_zone}
        opp_in_play_ids = {card.id for card in opponent.in_play}

        all_targetable_ids = ai_in_play_ids | opp_in_play_ids | ai_break_ids

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
