"""
Strategic Selector for AI V4 (Request 2).

Selects the BEST action sequence from validated candidates. This is the second
request in the dual-request architecture:
- Temperature: 0.7 (creative weighing of options)
- Focus: Pick the WINNING sequence using contextual examples
- Output: JSON with selected_index and reasoning

The selector focuses purely on strategy, receiving only pre-validated legal sequences.
"""

import json
import logging
from typing import TYPE_CHECKING

from .examples.loader import get_relevant_examples, get_game_phase, format_examples_for_prompt

logger = logging.getLogger(__name__)
from .sequence_generator import format_sequence_for_display

if TYPE_CHECKING:
    from game_engine.models.game_state import GameState

logger = logging.getLogger(__name__)


# JSON Schema for strategic selector output
STRATEGIC_SELECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "selected_index": {
            "type": "integer",
            "minimum": 0
        },
        "reasoning": {
            "type": "string",
            "maxLength": 180
        },
        "lethal_check": {
            "type": "boolean",
        }
    },
    "required": ["selected_index", "reasoning", "lethal_check"]
}


def generate_strategic_prompt(
    game_state: "GameState",
    player_id: str,
    validated_sequences: list[dict],
) -> str:
    """
    Generate the Request 2 prompt for strategic selection.
    
    This prompt is ~5k chars and includes:
    - Strategic goal and priorities
    - 3 contextual examples from the example library
    - Validated sequences with tactical labels
    
    Args:
        game_state: Current GameState object
        player_id: ID of the AI player
        validated_sequences: List of validated sequence dicts with tactical labels
        
    Returns:
        Prompt string (~5k chars target)
    """
    player = game_state.players[player_id]
    opponent = game_state.get_opponent(player_id)
    
    # Get game phase
    phase = get_game_phase(game_state.turn_number)
    
    # Get contextual examples (exactly 3)
    examples = get_relevant_examples(game_state, player_id)
    examples_text = format_examples_for_prompt(examples)
    
    # Format sequences
    sequences_text = "\n\n".join(
        format_sequence_for_display(seq, i)
        for i, seq in enumerate(validated_sequences)
    )
    
    # Count opponent cards
    opp_remaining = len(opponent.hand) + len(opponent.in_play)
    opp_slept = len(opponent.sleep_zone)
    opener_hint = ""
    if len(opponent.in_play) == 0:
        opener_hint = "With 0 opponent toys, a legal direct_attack line that sleeps a card now usually beats a setup-only line."
    
    prompt = f"""<system>Select the best legal sequence.</system>

<goal>
Priority: lethal > removal > tempo > efficiency.
Lethal means sleeping all {opp_remaining} remaining opponent cards this turn.
{opener_hint}
</goal>

<context>
phase={phase} turn={game_state.turn_number} your_cc={player.cc} your_toys={len(player.in_play)} opponent_toys={len(opponent.in_play)} opponent_remaining={opp_remaining} opponent_slept={opp_slept}
</context>

<examples>
{examples_text}
</examples>

<valid_sequences>
{sequences_text}
</valid_sequences>

<task>
Return the best 0-based index.
Prefer the line that wins now; otherwise remove the most threats and keep the strongest board.
Keep reasoning to 1-2 short sentences.
</task>"""

    return prompt


def get_strategic_selector_temperature() -> float:
    """Return the temperature for strategic selection (Request 2)."""
    return 0.4


def parse_selector_response(response_text: str) -> dict:
    """
    Parse the JSON response from strategic selector.
    
    Args:
        response_text: Raw JSON string from LLM
        
    Returns:
        Dictionary with selected_index, reasoning, lethal_check
    """
    try:
        data = json.loads(response_text)
        reasoning = data.get("reasoning", "")
        if not reasoning:
            logger.warning("Strategic selector returned empty reasoning")
            reasoning = "No reasoning provided"
        return {
            "selected_index": data.get("selected_index", 0),
            "reasoning": reasoning,
            "lethal_check": data.get("lethal_check", False),
        }
    except json.JSONDecodeError as e:
        logger.error(f"Strategic selector JSON parse error: {e}")
        logger.error(f"Response text (first 300 chars): {response_text[:300]}")
        return {"selected_index": 0, "reasoning": "Parse error, defaulting to first", "lethal_check": False}


def convert_sequence_to_turn_plan(
    sequence: dict,
    game_state: "GameState",
    player_id: str,
    reasoning: str
) -> dict:
    """
    Convert a validated sequence to TurnPlan format for execution.
    
    Args:
        sequence: Selected sequence dictionary
        game_state: Current GameState
        player_id: AI player ID
        reasoning: Strategic reasoning from selector
        
    Returns:
        Dictionary matching TurnPlan schema
    """
    player = game_state.players[player_id]
    opponent = game_state.get_opponent(player_id)
    
    # Build a lookup of card costs from hand
    hand_costs = {card.name: card.cost for card in player.hand}
    
    # Convert actions to PlannedAction format
    action_sequence = []
    cc_remaining = player.cc
    
    for action in sequence.get("actions", []):
        card_name = action.get("card_name", "")
        action_type = action.get("action_type")
        
        # Determine actual CC cost based on action type
        if action_type == "play_card":
            # Look up actual card cost from hand
            # Note: -1 means "copy target's cost" for Copy card, treat as 0 for planning
            cc_cost = max(0, hand_costs.get(card_name, 0))
        elif action_type in ("tussle", "direct_attack"):
            cc_cost = 2
        elif action_type == "activate_ability":
            cc_cost = 1
        else:
            cc_cost = 0
        
        # Calculate CC gains from Surge/Rush
        cc_gain = 0
        if action_type == "play_card":
            if card_name == "Surge":
                cc_gain = 1
            elif card_name == "Rush":
                cc_gain = 2
        
        cc_after = cc_remaining - cc_cost + cc_gain
        
        # Safety check: CC should never go negative
        # If it does, this sequence is invalid - cap at 0 to avoid Pydantic error
        # The validator should catch this, but we need to handle gracefully
        if cc_after < 0:
            logger.warning(f"CC went negative ({cc_after}) after {action_type} {card_name} - capping at 0")
            cc_after = 0
        
        # Convert target_name (singular) to target_names (list) if needed
        target_name = action.get("target_name")
        target_names = action.get("target_names") or ([target_name] if target_name else None)
        
        # Convert target_id (singular) to target_ids (list) if needed
        target_id = action.get("target_id")
        target_ids = action.get("target_ids") or ([target_id] if target_id else None)
        
        action_sequence.append({
            "action_type": action_type,
            "card_id": action.get("card_id"),
            "card_name": card_name,
            "target_ids": target_ids,
            "target_names": target_names,
            "alternative_cost_id": action.get("alternative_cost_id"),
            "cc_cost": cc_cost,
            "cc_after": cc_after,
            "reasoning": action.get("reasoning", ""),
        })
        
        cc_remaining = cc_after
    
    # Build TurnPlan
    total_cc_spent = sequence.get("total_cc_spent", 0)
    cards_slept = sequence.get("cards_slept", 0)
    
    # Threat assessment based on opponent board
    threat_summary = ", ".join(c.name for c in opponent.in_play) if opponent.in_play else "None"
    
    return {
        "threat_assessment": f"Opponent toys: {threat_summary}",
        "resources_summary": f"CC: {player.cc}, Hand: {len(player.hand)} cards, In Play: {len(player.in_play)} toys",
        "sequences_considered": [sequence.get("tactical_label", "Unknown")],
        "selected_strategy": reasoning,
        "action_sequence": action_sequence,
        "cc_start": player.cc,
        "cc_after_plan": cc_remaining,
        "expected_cards_slept": cards_slept,
        "plan_reasoning": reasoning,
        "residual_cc_justification": None if cc_remaining < 2 else "CC remaining but no valid attacks available",
    }
