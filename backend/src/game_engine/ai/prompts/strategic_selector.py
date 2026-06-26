"""
Strategic Selector for AI V4 (Request 2).

Selects the BEST action sequence from validated candidates. This is the second
request in the dual-request architecture:
- Temperature: 0.4 (see get_strategic_selector_temperature)
- Focus: Pick the WINNING sequence using contextual examples
- Output: JSON with selected_index and reasoning

The selector focuses purely on strategy, receiving only pre-validated legal sequences.
"""

import json
import logging
from typing import Any, Optional, TYPE_CHECKING

from .examples.loader import get_relevant_examples, get_game_phase, format_examples_for_prompt
from .sequence_generator import format_sequence_for_display
from .card_loader import format_card_guidance_compact, format_board_legend

if TYPE_CHECKING:
    from game_engine.models.game_state import GameState

logger = logging.getLogger(__name__)


# Request-2-specific system framing. Deliberately NOT system_prompt.py's
# SYSTEM_PROMPT verbatim: that prompt's "CRITICAL OUTPUT RULES" section is
# written for V2's action_number + [ID: xxx]-extraction schema, which doesn't
# apply here (Request 2 just picks a 0-based index into already-legal,
# already-built sequences) and would be actively confusing if included as-is.
# Prompt size is not a real constraint for this project (see issue #338) -
# this is written for clarity, not minimality.
STRATEGIC_SELECTOR_SYSTEM_INSTRUCTION = """You are selecting the best candidate action sequence for one turn of GGLTCG (Googooland Trading Card Game), a fully deterministic 2-player card game with no hidden information and no randomness.

## Win condition
You win when ALL of the opponent's cards are in their Sleep Zone. A sequence that sleeps the opponent's last remaining card this turn is lethal - always select it over any non-lethal alternative.

## CC and tussle basics
- Command Counters (CC) pay for playing cards, tussling, direct attacks, and activated abilities. Standard tussle/direct_attack cost is 2 CC and activate_ability is 1 CC, but some cards override this (e.g. Raggy's tussles cost 0, Wizard reduces tussles to 1 CC while it's in play).
- Tussle resolution: the active player's attacking Toy gets a +1 Speed bonus for ordering. Whichever card is faster strikes first, dealing its Strength as damage to the other's current Stamina. If that drops the target to 0 Stamina or below, it sleeps immediately. If it survives, it strikes back the same way before the exchange ends.
- Knight auto-wins any tussle it enters on your turn, ignoring stats entirely.
- A tussle being offered in a candidate sequence only means it is LEGAL, not that it is a good trade. Judge each one: with the attacker's turn-bonus Speed and Strength vs the defender's current Stamina, does the attacker sleep the defender before (or without) being struck back? If not, that tussle trades your card's health for nothing and should count against the sequence, not for it.
- Direct attack only works when the opponent has zero Toys in play, and sleeps a random card from their hand.

## How to judge a candidate sequence
Every sequence shown to you already passed legality validation - your job is purely strategic ranking, not legality checking. Use the board legend below to resolve each sequence's target labels (e.g. Y1, O2) to the actual cards involved, and weigh whether the tussles/abilities in it are good trades by the rule above. Prefer, in this order: a lethal sequence > one that actually sleeps the most real opponent threats > one that improves your board position or tempo without giving up cards for nothing > one that wastes the least CC.

Respond with only the JSON object the schema requires - no prose outside it."""


def get_strategic_selector_system_instruction() -> str:
    """Return the Request-2-specific system_instruction (see module docstring above)."""
    return STRATEGIC_SELECTOR_SYSTEM_INSTRUCTION


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
    game_engine: Optional[Any] = None,
) -> str:
    """
    Generate the Request 2 prompt for strategic selection.

    Includes:
    - Strategic goal and priorities
    - A board-state legend (short label, name, cost, stats, effect for every
      card in hand/in-play on both sides) so the model can resolve the
      sequences' Y1/O2-style target labels to actual cards
    - Card-specific guidance (traps/reminders/threats) for cards in this game
    - 3 contextual examples from the example library
    - Validated sequences with tactical labels

    Args:
        game_state: Current GameState object
        player_id: ID of the AI player
        validated_sequences: List of validated sequence dicts with tactical labels
        game_engine: Optional GameEngine, used so the legend's in-play stats
            reflect continuous effects (Ka's aura, Gibbers' cost tax, etc).

    Returns:
        Prompt string
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

    legend_text = format_board_legend(game_state, player_id, game_engine)
    guidance_text = format_card_guidance_compact(game_state, player_id)

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

<board_legend>
{legend_text}
</board_legend>

<card_guidance>
{guidance_text}
</card_guidance>

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
    reasoning: str,
    trust_action_costs: bool = False,
) -> dict:
    """
    Convert a validated sequence to TurnPlan format for execution.

    Args:
        sequence: Selected sequence dictionary
        game_state: Current GameState
        player_id: AI player ID
        reasoning: Strategic reasoning from selector
        trust_action_costs: When True, use each action's own ``cc_cost`` instead
            of re-deriving from canonical game-rule costs. Set by the enum
            planner, whose costs are engine-derived and exact (including
            discounted tussles like Raggy=0 / Wizard=1). Left False for LLM
            (dual) sequences, where a hallucinated cc_cost must not be trusted.

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
        
        # Determine actual CC cost based on action type.
        provided_cost = action.get("cc_cost")
        if trust_action_costs and provided_cost is not None:
            # Enum: the action carries the real engine-derived cost.
            cc_cost = max(0, provided_cost)
        elif action_type == "play_card":
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
