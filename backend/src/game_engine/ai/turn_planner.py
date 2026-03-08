"""
Turn Planner for AI planning.

This module implements the Phase 1 planning component of the AI architecture.
The TurnPlanner generates a complete turn plan at the start of each turn.

Planner Modes (set via AI_PLANNER_MODE env var):
- single: Single-request turn planning (default, optimized for Groq)
- dual:   Dual-request architecture (experimental, Gemini)
  - Request 1: Generate LEGAL sequences (temp 0.2)
  - Request 2: Select STRATEGICALLY with examples (temp 0.7)

Legacy: AI_VERSION=4 maps to 'dual'; all other values map to 'single'.
"""

import json
import logging
import os
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
from .prompts.planning_prompt_v3 import (
    get_planning_prompt_v3,
    format_hand_for_planning_v3,
    format_in_play_for_planning_v3,
)
from .validators import TurnPlanValidator
from .quality_metrics import TurnMetrics, record_turn_metrics
from .providers import BaseLLMProvider, build_provider, get_default_provider_name

logger = logging.getLogger(__name__)

PROMPT_TOKEN_ESTIMATE_DIVISOR = 4


def get_planner_mode() -> str:
    """Get the AI planner mode from environment.

    Returns 'single' or 'dual'.  Reads ``AI_PLANNER_MODE`` first;
    falls back to legacy ``AI_VERSION`` for backward compatibility
    (version 4 maps to 'dual', everything else to 'single').
    """
    mode = os.getenv("AI_PLANNER_MODE")
    if mode:
        mode = mode.strip().lower()
        if mode in ("single", "dual"):
            return mode
        logger.warning("Invalid AI_PLANNER_MODE '%s', defaulting to 'single'", mode)
        return "single"

    # Backward compat: derive from legacy AI_VERSION
    ai_version = os.getenv("AI_VERSION", "3")
    if ai_version == "4":
        return "dual"
    return "single"


def ai_version_to_planner_mode(ai_version: int) -> str:
    """Map a legacy ai_version integer to a planner mode string.

    Used by simulation and other callers that still pass version ints.
    """
    return "dual" if ai_version == 4 else "single"


class TurnPlanner:
    """
    Generates turn plans using the 4-phase strategic framework.
    
    Phase 1: Threat Assessment - Evaluate opponent's board
    Phase 2: Resource Inventory - Catalog available tools and sequences  
    Phase 3: Threat Mitigation - Generate and select removal sequences
    Phase 4: Offensive Opportunities - Direct attacks with remaining CC
    """
    
    # Class-level V4 metrics (shared across instances)
    _v4_metrics = {
        "total_turns": 0,
        "v4_success": 0,
        "v2_fallback": 0,
        "request1_success": 0,
        "request1_fail": 0,
        "request2_success": 0,
        "request2_fail": 0,
        "validation_rejections": 0,
    }
    
    @classmethod
    def get_v4_metrics(cls) -> dict:
        """Get V4 performance metrics."""
        m = cls._v4_metrics
        total = m["total_turns"] or 1  # Avoid division by zero
        return {
            **m,
            "v2_fallback_rate": f"{m['v2_fallback'] / total * 100:.1f}%",
            "request1_success_rate": f"{m['request1_success'] / (m['request1_success'] + m['request1_fail'] or 1) * 100:.1f}%",
            "request2_success_rate": f"{m['request2_success'] / (m['request2_success'] + m['request2_fail'] or 1) * 100:.1f}%",
        }
    
    @classmethod
    def reset_v4_metrics(cls):
        """Reset V4 metrics (useful for testing)."""
        for key in cls._v4_metrics:
            cls._v4_metrics[key] = 0
    
    def __init__(
        self,
        client,
        model_name: str,
        fallback_model: str,
        ai_version: int = None,
        planner_mode: str = None,
        provider_client: Optional[BaseLLMProvider] = None,
        provider: Optional[str] = None,
    ):
        """
        Initialize the TurnPlanner.
        
        Args:
            client: google-genai Client instance
            model_name: Primary model to use
            fallback_model: Fallback model for capacity issues
            ai_version: Deprecated. Use planner_mode instead.
            planner_mode: 'single' or 'dual'. If None, reads from AI_PLANNER_MODE env var.
        """
        self.client = client
        self.provider = provider or get_default_provider_name()
        self.provider_client = provider_client
        if self.provider_client is None:
            self.provider_client, resolved = build_provider(
                provider_name=self.provider,
                model=model_name,
                fallback_model=fallback_model,
                client=client,
            )
            self.model_name = resolved.model
            self.fallback_model = resolved.fallback_model
        else:
            self.model_name = model_name
            self.fallback_model = fallback_model
        
        # Determine planner mode: explicit arg > legacy ai_version arg > env var.
        if planner_mode:
            self.planner_mode = planner_mode
        elif ai_version is not None:
            self.planner_mode = ai_version_to_planner_mode(ai_version)
        else:
            self.planner_mode = get_planner_mode()
        
        # Store last planning info for debugging
        self._last_prompt: Optional[str] = None
        self._last_response: Optional[str] = None
        self._last_plan: Optional[TurnPlan] = None
        
        # V4 dual-request tracking for admin UI
        self._v4_request1_prompt: Optional[str] = None
        self._v4_request1_response: Optional[str] = None
        self._v4_request2_prompt: Optional[str] = None
        self._v4_request2_response: Optional[str] = None

        # V4 per-turn diagnostics for admin UI (counts/rejections/attempts)
        self._v4_turn_debug: Optional[Dict[str, Any]] = None
        
        # Initialize plan validator (will be set when game_engine available)
        self._validator: Optional[TurnPlanValidator] = None
    
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
        
        # Initialize validator if we have game_engine
        if game_engine and not self._validator:
            self._validator = TurnPlanValidator(game_engine)
        
        ai_player = game_state.players[player_id]
        opponent = game_state.get_opponent(player_id)
        
        logger.debug(f"📋 Planner mode: {self.planner_mode}")
        
        # Dual-request architecture
        if self.planner_mode == "dual":
            logger.debug("✅ Using dual-request planning")
            result = self._create_plan_v4(game_state, player_id, game_engine)
            # Log V4 metrics summary (DEBUG - summary logged at game end)
            m = TurnPlanner._v4_metrics
            if m["total_turns"] > 0:
                logger.debug(f"📊 V4 metrics: {m['v4_success']}/{m['total_turns']} success, "
                           f"{m['v2_fallback']} v2_fallback ({m['v2_fallback']/m['total_turns']*100:.0f}%), "
                           f"{m['request2_fail']} parse_errors")
            return result
        
        # Single-request turn planning (default)
        logger.debug("✅ Using single-request planning")
        
        # Format game state for the prompt
        game_state_text = format_game_state_for_ai(game_state, player_id, game_engine)
        
        # Format detailed card information with IDs (v3 compact format)
        hand_details = format_hand_for_planning_v3(ai_player.hand, game_engine, player=ai_player)
        
        # Combine AI's in-play cards with opponent's for context
        ai_in_play = format_in_play_for_planning_v3(ai_player.in_play, game_engine, player=ai_player)
        opp_in_play = format_in_play_for_planning_v3(opponent.in_play, game_engine, player=opponent)
        
        in_play_details = f"""**Your Toys:**
{ai_in_play}

**Opponent's Toys (THREATS):**
{opp_in_play}

**Your Sleep Zone:** {format_sleep_zone_for_planning(ai_player.sleep_zone)}
**Opponent's Sleep Zone:** {format_sleep_zone_for_planning(opponent.sleep_zone)}"""
        
        # Generate the compressed v3 planning prompt with dynamic card guidance
        base_prompt = get_planning_prompt_v3(
            game_state_text, hand_details, in_play_details, game_state, player_id
        )
        
        # Retry loop with validation feedback
        # Single-request mode: no retries — each call consumes Groq's entire per-minute token
        # budget.  Return the first plan regardless; the execution layer handles bad actions
        # gracefully by skipping them.
        max_retries = 1
        validation_feedback = ""
        
        for attempt in range(max_retries):
            # Add validation feedback to prompt if retrying
            if validation_feedback:
                prompt = f"{base_prompt}\n\n⚠️ VALIDATION FEEDBACK:\n{validation_feedback}"
                logger.debug(f"🔄 Retry {attempt + 1}/{max_retries} with validation feedback")
            else:
                prompt = base_prompt
            
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
                # Ground cc_start to actual player CC — LLMs frequently output the wrong
                # value (e.g. 0 instead of 2 on turn 1), which corrupts every cc_after
                # figure shown in admin logs and makes the plan look impossible.
                plan.cc_start = ai_player.cc
                self._reground_cc_chain(plan)
                self._last_plan = plan
                
                # Validate card IDs exist in game state
                id_errors = self.validate_plan_actions(plan, game_state, player_id)
                if id_errors:
                    logger.warning(f"Plan has card ID errors: {id_errors}")
                    # Continue with validation - these might be recoverable
                
                # Run turn plan validators if available
                if self._validator:
                    validation_errors = self._validator.validate(
                        plan, game_state, player_id, ai_player.cc
                    )
                    
                    if validation_errors:
                        # Single-request mode: no LLM retry, but prune any
                        # actions that failed critical checks so the execution
                        # layer never encounters them.  This turns a broken
                        # plan like [play Rush (T1), direct_attack, end_turn]
                        # into [end_turn], which at least doesn't waste CC and
                        # keeps mid-turn-replan logic from being cheated.
                        if self.planner_mode == "single":
                            critical_types = {
                                "cc_budget",
                                "no_attacker",
                                "opponent_toys",
                                "sleep_zone_play",
                                "invalid_attacker",
                                "dependency",
                            }
                            bad_indices = {
                                e.action_index
                                for e in validation_errors
                                if e.error_type in critical_types
                            }
                            if bad_indices:
                                original_len = len(plan.action_sequence)
                                plan.action_sequence = [
                                    a for i, a in enumerate(plan.action_sequence)
                                    if i not in bad_indices
                                ]
                                logger.warning(
                                    "Single-mode plan pruned %d invalid action(s) "
                                    "(%d → %d steps). Errors: %s",
                                    len(bad_indices),
                                    original_len,
                                    len(plan.action_sequence),
                                    [e.to_llm_feedback() for e in validation_errors
                                     if e.error_type in critical_types],
                                )
                            else:
                                logger.debug(
                                    "Plan has %d non-critical validation issue(s) — proceeding",
                                    len(validation_errors),
                                )
                            self._log_plan_summary(plan)
                            metrics = TurnMetrics.from_plan(plan, game_state, player_id)
                            record_turn_metrics(metrics)
                            logger.info(f"Turn {metrics.turn_number} metrics: {metrics.to_log_dict()}")
                            return plan

                        # Dual-request mode: format feedback and retry
                        validation_feedback = self._validator.format_feedback_for_llm(validation_errors)
                        logger.warning(f"Plan validation failed (attempt {attempt + 1}/{max_retries})")

                        if attempt == max_retries - 1:
                            logger.error("Max retries reached. Returning plan despite validation errors.")
                            self._log_plan_summary(plan)
                            metrics = TurnMetrics.from_plan(plan, game_state, player_id)
                            record_turn_metrics(metrics)
                            logger.info(f"Turn {metrics.turn_number} metrics: {metrics.to_log_dict()}")
                            return plan

                        # Retry with feedback
                        continue
                
                # Plan passed validation
                logger.debug("✅ Plan passed validation")
                self._log_plan_summary(plan)
                
                # Record quality metrics
                metrics = TurnMetrics.from_plan(plan, game_state, player_id)
                record_turn_metrics(metrics)
                logger.info(f"Turn {metrics.turn_number} metrics: {metrics.to_log_dict()}")
                
                return plan
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse plan as JSON: {e}")
                logger.error(f"Response was: {self._last_response}")
                
                # Last attempt - give up
                if attempt == max_retries - 1:
                    return None
                
                # Retry with feedback
                validation_feedback = f"Your previous response was not valid JSON. Error: {e}\nPlease return a valid JSON response following the schema."
                continue
                
            except Exception as e:
                logger.exception(f"Error creating plan: {e}")
                return None
        
        # Should not reach here, but just in case
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
        result = self.provider_client.generate_json(
            prompt,
            TURN_PLAN_JSON_SCHEMA,
            temperature=0.7,
            max_output_tokens=self._get_planning_output_budget(),
            retry_count=retry_count,
            allow_fallback=allow_fallback,
            model=self.model_name,
            fallback_model=self.fallback_model,
        )
        logger.debug(f"Plan response length: {len(result)} characters")
        return result
    
    def _create_plan_v4(
        self,
        game_state: GameState,
        player_id: str,
        game_engine=None
    ) -> Optional[TurnPlan]:
        """
        V4 dual-request planning architecture.
        
        Request 1 (temp 0.2): Generate LEGAL sequences
        Request 2 (temp 0.7): Select STRATEGICALLY with examples
        
        Fallback: If no valid sequences, retry with temp 1.0, then V2 single-action.
        
        Args:
            game_state: Current GameState object
            player_id: ID of the AI player
            game_engine: Optional GameEngine for validation
            
        Returns:
            TurnPlan object if successful, None if failed
        """
        from .prompts.sequence_generator import (
            generate_sequence_prompt,
            get_sequence_generator_temperature,
            SEQUENCE_GENERATOR_SCHEMA,
            parse_sequences_response,
            add_tactical_labels,
        )
        from .prompts.strategic_selector import (
            generate_strategic_prompt,
            get_strategic_selector_temperature,
            STRATEGIC_SELECTOR_SCHEMA,
            parse_selector_response,
            convert_sequence_to_turn_plan,
        )
        
        ai_player = game_state.players[player_id]
        
        # Track V4 metrics - increment total turns
        TurnPlanner._v4_metrics["total_turns"] += 1
        
        # Reset V4 tracking
        self._v4_request1_prompt = None
        self._v4_request1_response = None
        self._v4_request2_prompt = None
        self._v4_request2_response = None
        self._v4_turn_debug = {
            "request1_attempts": 0,
            "request1_temps_tried": [],
            "sequences_generated": 0,
            "sequences_after_validation": 0,
            "sequences_rejected": 0,
            "sequence_rejection_messages": [],
            "request2_parse_error": False,
            "request2_invalid_index": False,
            "request2_selected_index": None,
            "request2_selected_index_used": None,
            "request2_exception": None,
            "request2_fallback_used": False,
        }
        
        # === REQUEST 1: Generate sequences (low temperature) ===
        logger.debug("📝 V4 Request 1: Generating action sequences...")
        
        seq_prompt = generate_sequence_prompt(game_state, player_id, game_engine)
        self._last_prompt = seq_prompt
        self._v4_request1_prompt = seq_prompt
        logger.debug(
            "Sequence generator prompt (%s chars, ~%s tokens)",
            len(seq_prompt),
            self._estimate_prompt_tokens(seq_prompt),
        )
        
        sequences = []
        for temp in [get_sequence_generator_temperature(), 1.0]:  # Retry with higher temp
            if self._v4_turn_debug is not None:
                self._v4_turn_debug["request1_attempts"] += 1
                self._v4_turn_debug["request1_temps_tried"].append(temp)
            try:
                response_text = self.provider_client.generate_json(
                    seq_prompt,
                    SEQUENCE_GENERATOR_SCHEMA,
                    temperature=temp,
                    max_output_tokens=self._get_sequence_output_budget(),
                    retry_count=3,
                    allow_fallback=True,
                    model=self.model_name,
                    fallback_model=self.fallback_model,
                )
                self._last_response = response_text
                self._v4_request1_response = response_text
                sequences = parse_sequences_response(response_text)
                if self._v4_turn_debug is not None:
                    self._v4_turn_debug["sequences_generated"] = len(sequences)
                logger.debug(f"   Generated {len(sequences)} sequences (temp={temp})")

                if sequences:
                    break
                        
            except Exception as e:
                logger.warning(f"Request 1 failed (temp={temp}): {e}")
                continue
        
        # Validate sequences with TurnPlanValidator
        if sequences and self._validator:
            valid_sequences = []
            for i, seq in enumerate(sequences):
                # Convert sequence to TurnPlan for validation
                temp_plan = self._sequence_to_temp_plan(seq, ai_player.cc)
                errors = self._validator.validate(
                    temp_plan, game_state, player_id, ai_player.cc
                )
                if not errors:
                    valid_sequences.append(seq)
                else:
                    logger.warning(f"   Sequence {i} rejected: {errors[0].message}")
                    TurnPlanner._v4_metrics["validation_rejections"] += 1
                    if self._v4_turn_debug is not None:
                        self._v4_turn_debug["sequences_rejected"] += 1
                        # Keep only a handful of messages to avoid very large payloads
                        msgs: list[str] = self._v4_turn_debug.get("sequence_rejection_messages", [])
                        if len(msgs) < 8:
                            msgs.append(f"rejected: {errors[0].message}")
                            self._v4_turn_debug["sequence_rejection_messages"] = msgs
            
            sequences = valid_sequences
            if self._v4_turn_debug is not None:
                self._v4_turn_debug["sequences_after_validation"] = len(sequences)
            logger.debug(f"   {len(sequences)} sequences passed validation")
        elif not sequences:
            logger.warning("   No sequences returned from LLM")
        
        # Track Request 1 outcome
        if sequences:
            TurnPlanner._v4_metrics["request1_success"] += 1
        else:
            TurnPlanner._v4_metrics["request1_fail"] += 1
        
        # If no valid sequences, fall back to V2 single-action mode
        if not sequences:
            logger.warning("⚠️ V4: No valid sequences, falling back to V2 single-action mode")
            TurnPlanner._v4_metrics["v2_fallback"] += 1
            # Return None to trigger V2 fallback in llm_player
            return None
        
        # Add tactical labels
        sequences = add_tactical_labels(sequences)
        
        # === REQUEST 2: Strategic selection (higher temperature) ===
        logger.debug("🎯 V4 Request 2: Selecting best sequence...")
        
        select_prompt = generate_strategic_prompt(game_state, player_id, sequences)
        self._v4_request2_prompt = select_prompt
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
            )
            self._v4_request2_response = select_response
            selection = parse_selector_response(select_response)

            selected_index = selection.get("selected_index", 0)
            reasoning = selection.get("reasoning", "No reasoning provided")

            if self._v4_turn_debug is not None:
                self._v4_turn_debug["request2_selected_index"] = selected_index

            if "Parse error" in reasoning:
                TurnPlanner._v4_metrics["request2_fail"] += 1
                if self._v4_turn_debug is not None:
                    self._v4_turn_debug["request2_parse_error"] = True
            else:
                TurnPlanner._v4_metrics["request2_success"] += 1

            if selected_index >= len(sequences):
                selected_index = 0
                logger.warning(f"Invalid sequence index, using 0")
                if self._v4_turn_debug is not None:
                    self._v4_turn_debug["request2_invalid_index"] = True

            if self._v4_turn_debug is not None:
                self._v4_turn_debug["request2_selected_index_used"] = selected_index

            selected_sequence = sequences[selected_index]
            logger.debug(f"   Selected sequence {selected_index}: {selected_sequence.get('tactical_label', '?')}")
            logger.debug(f"   Reasoning: {reasoning[:100]}...")

            plan_data = convert_sequence_to_turn_plan(
                selected_sequence, game_state, player_id, reasoning
            )
            plan = self._parse_plan(plan_data)
            plan.cc_start = ai_player.cc
            self._reground_cc_chain(plan)
            self._last_plan = plan

            TurnPlanner._v4_metrics["v4_success"] += 1

            self._log_plan_summary(plan)

            metrics = TurnMetrics.from_plan(plan, game_state, player_id)
            record_turn_metrics(metrics)
            logger.info(f"Turn {metrics.turn_number} metrics: {metrics.to_log_dict()}")

            return plan
                
        except Exception as e:
            logger.error(f"Request 2 failed: {e}")
            TurnPlanner._v4_metrics["request2_fail"] += 1
            if self._v4_turn_debug is not None:
                self._v4_turn_debug["request2_exception"] = str(e)
            # Fall back to first sequence if selection fails
            if sequences:
                if self._v4_turn_debug is not None:
                    self._v4_turn_debug["request2_fallback_used"] = True
                plan_data = convert_sequence_to_turn_plan(
                    sequences[0], game_state, player_id, "Selection failed, using first sequence"
                )
                plan = self._parse_plan(plan_data)
                plan.cc_start = ai_player.cc
                self._reground_cc_chain(plan)
                self._last_plan = plan
                TurnPlanner._v4_metrics["v4_success"] += 1  # Still V4 success, just with fallback selection
                
                # Record quality metrics
                metrics = TurnMetrics.from_plan(plan, game_state, player_id)
                record_turn_metrics(metrics)
                logger.info(f"Turn {metrics.turn_number} metrics: {metrics.to_log_dict()}")
                
                return plan
        
        return None

    def _estimate_prompt_tokens(self, prompt: str) -> int:
        return max(1, len(prompt) // PROMPT_TOKEN_ESTIMATE_DIVISOR)

    def _get_planning_output_budget(self) -> int:
        if self.provider == "groq":
            return 2048
        return 4096

    def _get_sequence_output_budget(self) -> int:
        if self.provider == "groq":
            return 1024
        return 1024

    def _get_selector_output_budget(self) -> int:
        if self.provider == "groq":
            return 256
        return 384
    
    def _sequence_to_temp_plan(self, sequence: dict, starting_cc: int) -> TurnPlan:
        """
        Convert a sequence dict to a temporary TurnPlan for validation.
        
        Args:
            sequence: Sequence dictionary from generator
            starting_cc: CC at turn start
            
        Returns:
            TurnPlan object for validation
        """
        actions = []
        cc = starting_cc
        
        for action in sequence.get("actions", []):
            cc_cost = action.get("cc_cost", 0)
            card_name = action.get("card_name", "")
            
            # Calculate CC gain
            cc_gain = 0
            if action.get("action_type") == "play_card":
                if card_name == "Surge":
                    cc_gain = 1
                elif card_name == "Rush":
                    cc_gain = 2
            
            cc_after = cc - cc_cost + cc_gain
            
            # Convert target_name (singular) to target_names (list) if needed
            target_name = action.get("target_name")
            target_names = action.get("target_names") or ([target_name] if target_name else None)
            
            actions.append(PlannedAction(
                action_type=action.get("action_type", "end_turn"),
                card_id=action.get("card_id"),
                card_name=card_name,
                target_ids=action.get("target_ids"),
                target_names=target_names,
                cc_cost=cc_cost,
                cc_after=max(0, cc_after),
                reasoning="",
            ))
            
            cc = cc_after
        
        return TurnPlan(
            threat_assessment="",
            resources_summary="",
            sequences_considered=[],
            selected_strategy="",
            action_sequence=actions,
            cc_start=starting_cc,
            cc_after_plan=max(0, cc),
            expected_cards_slept=sequence.get("cards_slept", 0),
            plan_reasoning="",
        )
    
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
                cc_cost=_safe_nonneg_int(action_data.get("cc_cost")),
                cc_after=_safe_nonneg_int(action_data.get("cc_after")),
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
                    cc_cost=0,
                    cc_after=action_sequence[-1].cc_after if action_sequence else plan_data.get("cc_start", 0),
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
            cc_start=plan_data.get("cc_start", 0),
            cc_after_plan=plan_data.get("cc_after_plan", 0),
            expected_cards_slept=plan_data.get("expected_cards_slept", 0),
            plan_reasoning=_str(plan_data.get("plan_reasoning", "")),
        )
        
        return plan
    
    # Cards that gain CC when played (mirrors TurnPlanValidator.CC_GAIN_ON_PLAY)
    _CC_GAIN_ON_PLAY = {"Surge": 1, "Rush": 2, "HLK": 1}

    # Canonical CC cost for non-play_card actions — these are fixed by game rules.
    # Override whatever the LLM stated so regrounding is correct even if the LLM
    # hallucinates cc_cost=0 (which would prevent pruning an unaffordable step).
    _CANONICAL_ACTION_COSTS = {"direct_attack": 2, "tussle": 2}

    def _reground_cc_chain(self, plan: TurnPlan) -> None:
        """
        Recompute cc_after for each planned action from the grounded cc_start,
        and prune any action that would require more CC than is available at
        that point in the sequence.

        The LLM sometimes builds a mathematically consistent chain from a wrong
        cc_start, or miscalculates steps, or includes cards the player cannot
        afford.  After we override plan.cc_start with the actual player CC, this
        method walks the sequence, drops impossible actions (logging a warning),
        and patches each remaining action's cc_after so the chain is consistent.

        cc_after is informational (shown in admin) — execution uses live game
        state CC — but wrong values mislead human reviewers and make the plan
        look impossible when the test suite checks it.
        """
        running_cc = plan.cc_start
        grounded: list = []
        for action in plan.action_sequence:
            if action.action_type == "end_turn":
                action.cc_after = max(0, running_cc)
                grounded.append(action)
                continue
            # Enforce canonical cost for actions whose CC cost is fixed by game rules.
            # This prevents a hallucinated cc_cost=0 from bypassing the affordability
            # check and producing a plan that fails silently at execution time.
            canonical = self._CANONICAL_ACTION_COSTS.get(action.action_type)
            if canonical is not None and action.cc_cost != canonical:
                logger.warning(
                    "Plan grounding: correcting cc_cost for %s from %d to %d (game rule)",
                    action.action_type, action.cc_cost, canonical,
                )
                action.cc_cost = canonical
            gain = self._CC_GAIN_ON_PLAY.get(action.card_name or "", 0)
            net_cost = action.cc_cost - gain
            if net_cost > running_cc:
                logger.warning(
                    "Plan grounding: dropping unaffordable action "
                    "%s %s (costs %d, gain %d, available %d)",
                    action.action_type,
                    action.card_name or action.card_id or "",
                    action.cc_cost,
                    gain,
                    running_cc,
                )
                continue
            running_cc = max(0, running_cc - action.cc_cost + gain)
            action.cc_after = running_cc
            grounded.append(action)
        plan.action_sequence = grounded
        # Also patch the plan-level cc_after_plan to match
        plan.cc_after_plan = running_cc

    def _log_plan_summary(self, plan: TurnPlan) -> None:
        """Log a human-readable summary of the plan."""
        logger.debug("=" * 60)
        logger.debug("📋 TURN PLAN GENERATED")
        logger.debug("=" * 60)
        logger.debug(f"Threat Assessment: {plan.threat_assessment[:100]}...")
        logger.debug(f"Selected Strategy: {plan.selected_strategy}")
        logger.debug(f"CC Budget: {plan.cc_start} → {plan.cc_after_plan}")
        logger.debug(f"Expected cards to sleep: {plan.expected_cards_slept}")
        logger.debug("-" * 40)
        logger.debug("Action Sequence:")
        for i, action in enumerate(plan.action_sequence, 1):
            card_info = f"{action.card_name or 'N/A'}" if action.card_name else action.card_id or "N/A"
            target_info = ""
            if action.target_names:
                target_info = f" → {', '.join(action.target_names)}"
            elif action.target_ids:
                target_info = f" → {', '.join(action.target_ids[:2])}..."
            logger.debug(f"  {i}. {action.action_type}: {card_info}{target_info} ({action.cc_cost} CC → {action.cc_after} CC)")
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
        
        # Include V4 dual-request details if available
        if self._v4_request1_prompt:
            info["v4_request1_prompt"] = self._v4_request1_prompt
            info["v4_request1_response"] = self._v4_request1_response
        if self._v4_request2_prompt:
            info["v4_request2_prompt"] = self._v4_request2_prompt
            info["v4_request2_response"] = self._v4_request2_response
        
        # Include V4 metrics
        info["v4_metrics"] = TurnPlanner.get_v4_metrics()

        # Include V4 per-turn diagnostics
        if self._v4_turn_debug is not None:
            info["v4_turn_debug"] = self._v4_turn_debug
        
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
