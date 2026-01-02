"""
Turn Planner for AI v3/v4.

This module implements the Phase 1 planning component of the AI architecture.
The TurnPlanner generates a complete turn plan at the start of each turn.

AI Versions (set via AI_VERSION env var):
- V3: Single request turn planning (default)
- V4: Dual-request architecture
  - Request 1: Generate LEGAL sequences (temp 0.2)
  - Request 2: Select STRATEGICALLY with examples (temp 0.7)
"""

import json
import logging
import time
import os
from typing import Optional, Dict, Any, List

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

logger = logging.getLogger(__name__)


def get_ai_version() -> str:
    """Get the AI version from environment (3 or 4)."""
    return os.getenv("AI_VERSION", "3")


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
        
        # V4 dual-request tracking for admin UI
        self._v4_request1_prompt: Optional[str] = None
        self._v4_request1_response: Optional[str] = None
        self._v4_request2_prompt: Optional[str] = None
        self._v4_request2_response: Optional[str] = None
        
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
        logger.info(f"🧠 Creating turn plan for Turn {game_state.turn_number}")
        
        # Initialize validator if we have game_engine
        if game_engine and not self._validator:
            self._validator = TurnPlanValidator(game_engine)
        
        ai_player = game_state.players[player_id]
        opponent = game_state.get_opponent(player_id)
        
        # Check which AI version to use
        ai_version = get_ai_version()
        logger.info(f"📋 AI version: {ai_version}")
        
        # V4: Dual-request architecture
        if ai_version == "4":
            logger.info("✅ Using AI V4 (dual-request architecture)")
            result = self._create_plan_v4(game_state, player_id, game_engine)
            # Log V4 metrics summary
            m = TurnPlanner._v4_metrics
            if m["total_turns"] > 0:
                logger.info(f"📊 V4 metrics: {m['v4_success']}/{m['total_turns']} success, "
                           f"{m['v2_fallback']} v2_fallback ({m['v2_fallback']/m['total_turns']*100:.0f}%), "
                           f"{m['request2_fail']} parse_errors")
            return result
        
        # V3: Single-request turn planning (default)
        logger.info("✅ Using AI V3 (single-request planning)")
        
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
        max_retries = 3
        validation_feedback = ""
        
        for attempt in range(max_retries):
            # Add validation feedback to prompt if retrying
            if validation_feedback:
                prompt = f"{base_prompt}\n\n⚠️ VALIDATION FEEDBACK:\n{validation_feedback}"
                logger.info(f"🔄 Retry {attempt + 1}/{max_retries} with validation feedback")
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
                        # Format feedback for retry
                        validation_feedback = self._validator.format_feedback_for_llm(validation_errors)
                        logger.warning(f"Plan validation failed (attempt {attempt + 1}/{max_retries})")
                        
                        # Last attempt - return plan anyway with warning
                        if attempt == max_retries - 1:
                            logger.error("Max retries reached. Returning plan despite validation errors.")
                            self._log_plan_summary(plan)
                            return plan
                        
                        # Retry with feedback
                        continue
                
                # Plan passed validation
                logger.info("✅ Plan passed validation")
                self._log_plan_summary(plan)
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
        from google.genai import types
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
        
        # === REQUEST 1: Generate sequences (low temperature) ===
        logger.info("📝 V4 Request 1: Generating action sequences...")
        
        seq_prompt = generate_sequence_prompt(game_state, player_id, game_engine)
        self._last_prompt = seq_prompt
        self._v4_request1_prompt = seq_prompt
        logger.debug(f"Sequence generator prompt ({len(seq_prompt)} chars)")
        
        sequences = []
        for temp in [get_sequence_generator_temperature(), 1.0]:  # Retry with higher temp
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=seq_prompt)]
                        )
                    ],
                    config=types.GenerateContentConfig(
                        temperature=temp,
                        max_output_tokens=4096,
                        response_mime_type="application/json",
                        response_json_schema=SEQUENCE_GENERATOR_SCHEMA,
                    )
                )
                
                if response.candidates and response.candidates[0].content.parts:
                    response_text = response.text.strip()
                    self._last_response = response_text
                    self._v4_request1_response = response_text
                    sequences = parse_sequences_response(response_text)
                    logger.info(f"   Generated {len(sequences)} sequences (temp={temp})")
                    
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
            
            sequences = valid_sequences
            logger.info(f"   {len(sequences)} sequences passed validation")
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
        logger.info("🎯 V4 Request 2: Selecting best sequence...")
        
        select_prompt = generate_strategic_prompt(game_state, player_id, sequences)
        self._v4_request2_prompt = select_prompt
        logger.debug(f"Strategic selector prompt ({len(select_prompt)} chars)")
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=select_prompt)]
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=get_strategic_selector_temperature(),
                    max_output_tokens=1024,
                    response_mime_type="application/json",
                    response_json_schema=STRATEGIC_SELECTOR_SCHEMA,
                )
            )
            
            if response.candidates and response.candidates[0].content.parts:
                select_response = response.text.strip()
                self._v4_request2_response = select_response
                selection = parse_selector_response(select_response)
                
                selected_index = selection.get("selected_index", 0)
                reasoning = selection.get("reasoning", "No reasoning provided")
                
                # Check if this was a parse error (strategic selector failed)
                if "Parse error" in reasoning:
                    TurnPlanner._v4_metrics["request2_fail"] += 1
                else:
                    TurnPlanner._v4_metrics["request2_success"] += 1
                
                # Ensure index is valid
                if selected_index >= len(sequences):
                    selected_index = 0
                    logger.warning(f"Invalid sequence index, using 0")
                
                selected_sequence = sequences[selected_index]
                logger.info(f"   Selected sequence {selected_index}: {selected_sequence.get('tactical_label', '?')}")
                logger.info(f"   Reasoning: {reasoning[:100]}...")
                
                # Convert to TurnPlan
                plan_data = convert_sequence_to_turn_plan(
                    selected_sequence, game_state, player_id, reasoning
                )
                plan = self._parse_plan(plan_data)
                self._last_plan = plan
                
                # Track V4 success
                TurnPlanner._v4_metrics["v4_success"] += 1
                
                self._log_plan_summary(plan)
                return plan
                
        except Exception as e:
            logger.error(f"Request 2 failed: {e}")
            TurnPlanner._v4_metrics["request2_fail"] += 1
            # Fall back to first sequence if selection fails
            if sequences:
                plan_data = convert_sequence_to_turn_plan(
                    sequences[0], game_state, player_id, "Selection failed, using first sequence"
                )
                plan = self._parse_plan(plan_data)
                self._last_plan = plan
                TurnPlanner._v4_metrics["v4_success"] += 1  # Still V4 success, just with fallback selection
                return plan
        
        return None
    
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
            cc_efficiency="",
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
