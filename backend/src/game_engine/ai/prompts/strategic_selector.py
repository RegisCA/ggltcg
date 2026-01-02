"""
Strategic Selector for AI V4 (Request 2).

Selects the BEST action sequence from validated candidates. This is the second
request in the dual-request architecture:
- Temperature: 0.7 (creative weighing of options)
- Focus: Pick the WINNING sequence using contextual examples
- Output: JSON with selected_index and reasoning

The selector focuses purely on strategy, receiving only pre-validated legal sequences.
"""

import logging
from typing import TYPE_CHECKING

from .examples.loader import get_relevant_examples, get_game_phase, format_examples_for_prompt
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
            "description": "0-based index of the best sequence to execute",
            "minimum": 0
        },
        "reasoning": {
            "type": "string",
            "description": "1-3 sentences explaining why this sequence is best. Reference examples if applicable.",
            "maxLength": 300
        },
        "lethal_check": {
            "type": "boolean",
            "description": "True if selected sequence wins the game this turn"
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
    opp_total = len(opponent.hand) + len(opponent.in_play) + len(opponent.sleep_zone)
    opp_remaining = len(opponent.hand) + len(opponent.in_play)
    opp_slept = len(opponent.sleep_zone)
    
    prompt = f"""<system>You select the BEST action sequence to WIN the game efficiently.</system>

<goal>
Select the sequence that maximizes your chance of winning.
Priority order:
1. LETHAL — Can you win THIS turn? Sleep all remaining opponent cards. Always check first!
2. REMOVAL — Sleep opponent's toys to reduce their threats.
3. TEMPO — Build board advantage (more toys than opponent).
4. EFFICIENCY — Spend less CC per card slept. Target: under 3.0 CC/card.
</goal>

<metrics>
<metric name="cc_efficiency">CC spent per card slept. Lower is better. Target: under 3.0</metric>
<metric name="board_advantage">Your toys minus opponent toys. Higher is better.</metric>
<metric name="lethal_check">Can you sleep ALL remaining opponent cards this turn?</metric>
</metrics>

<game_phase>{phase}</game_phase>

<examples>
{examples_text}
</examples>

<current_situation>
<turn>{game_state.turn_number}</turn>
<your_cc>{player.cc}</your_cc>
<your_toys_in_play>{len(player.in_play)}</your_toys_in_play>
<opponent_cards_remaining>{opp_remaining}</opponent_cards_remaining>
<opponent_toys_in_play>{len(opponent.in_play)}</opponent_toys_in_play>
<opponent_cards_slept>{opp_slept}</opponent_cards_slept>
<cards_to_sleep_for_win>{opp_remaining}</cards_to_sleep_for_win>
</current_situation>

<valid_sequences>
{sequences_text}
</valid_sequences>

<task>
Select the best sequence by its index (0-based).
First, check if any sequence achieves LETHAL (sleeps all {opp_remaining} remaining opponent cards).
If no lethal, prioritize REMOVAL over TEMPO over EFFICIENCY.
Explain your reasoning in 1-3 sentences, referencing the examples if relevant.
</task>"""

    return prompt


def get_strategic_selector_temperature() -> float:
    """Return the temperature for strategic selection (Request 2)."""
    return 0.7


def parse_selector_response(response_text: str) -> dict:
    """
    Parse the JSON response from strategic selector.
    
    Args:
        response_text: Raw JSON string from LLM
        
    Returns:
        Dictionary with selected_index, reasoning, lethal_check
    """
    import json
    import logging
    
    logger = logging.getLogger("game_engine.ai.strategic_selector")
    
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
            cc_cost = hand_costs.get(card_name, 0)
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
        
        action_sequence.append({
            "action_type": action_type,
            "card_id": action.get("card_id"),
            "card_name": card_name,
            "target_ids": action.get("target_ids"),
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
    
    # Calculate efficiency
    if cards_slept > 0:
        efficiency = f"{total_cc_spent} CC / {cards_slept} cards = {total_cc_spent/cards_slept:.2f} CC/card"
    else:
        efficiency = f"{total_cc_spent} CC / 0 cards = N/A (no cards slept)"
    
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
        "cc_efficiency": efficiency,
        "plan_reasoning": reasoning,
        "residual_cc_justification": None if cc_remaining < 2 else "CC remaining but no valid attacks available",
    }
