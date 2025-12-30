"""
Execution Prompt for AI v3.

This module contains the prompt for executing planned actions.
Given a TurnPlan and the current available actions, the AI selects
the matching action from the valid_actions list.

The execution prompt is simpler than planning - it just needs to:
1. Match the planned action to an available action number
2. Select appropriate targets when required
3. Handle edge cases (plan invalid, action not available)
"""

from typing import List, Optional
from .schemas import PlannedAction, TurnPlan


# =============================================================================
# Execution System Prompt
# =============================================================================

EXECUTION_SYSTEM_PROMPT = """You are executing a pre-planned GGLTCG turn.

Your task is simple: Match the planned action to the correct action number from the available actions list.

## Rules
1. Find the action in VALID ACTIONS that matches the PLANNED ACTION
2. Return the 1-based action number
3. If the planned action requires targets, select them from the target options
4. **CRITICAL**: If the planned action is NOT in the list, select "End turn" instead!
5. **NEVER return an action number higher than the number of available actions!**

## Output Format
Return a JSON object with:
- action_number: The 1-based number from the valid actions list (MUST be 1 to N where N = number of actions)
- target_ids: Array of card IDs if targets are needed (from [ID: xxx] in target options)
- alternative_cost_id: Card ID if using alternative cost (Ballaber)
- reasoning: Brief explanation of action selection

## IMPORTANT: Action Not Found
If the planned card (e.g., "Beary") is NOT in the valid actions list:
- DO NOT return a number that doesn't exist
- Find "End turn" action and return its number
- Explain in reasoning: "Planned card not available, ending turn"

## Target Selection Rules
- For tussle: Select the opponent card your card will attack
- For activate_ability (Archer): Select the card to remove stamina from
- For play_card: No target needed unless card has "requires target" 
- For direct_attack: No target needed (hits random opponent card)
- For Drop/Twist: Select the opponent card to target

## Matching Actions
Match by action TYPE and CARD NAME:
- "play_card" + "Knight" → Look for "Play Knight" in valid actions
- "tussle" + "Knight" → Look for tussle action involving Knight
- "direct_attack" → Look for "Direct attack" action
- "end_turn" → Look for "End turn" action
- "activate_ability" + "Archer" → Look for Archer ability activation
"""


# =============================================================================
# Execution Prompt Builder
# =============================================================================

def get_execution_prompt(
    planned_action: PlannedAction,
    action_index: int,
    total_actions: int,
    valid_actions_text: str,
    current_cc: int,
    num_valid_actions: int = None,
) -> str:
    """
    Build the execution prompt for a single planned action.
    
    Args:
        planned_action: The action to execute from the TurnPlan
        action_index: Which action this is (0-based) in the plan
        total_actions: Total number of actions in the plan
        valid_actions_text: Formatted valid actions from format_valid_actions_for_ai
        current_cc: Current CC available
        num_valid_actions: Number of valid actions available (for validation hint)
        
    Returns:
        Execution prompt string
    """
    # Format target info if present
    target_info = ""
    if planned_action.target_ids:
        target_info = f"\nPlanned targets: {planned_action.target_ids}"
    
    # Add validation hint about number of actions
    validation_hint = ""
    if num_valid_actions:
        validation_hint = f"\n\n**VALIDATION: There are exactly {num_valid_actions} valid actions. action_number MUST be 1-{num_valid_actions}!**"
    
    prompt = f"""{EXECUTION_SYSTEM_PROMPT}

## PLANNED ACTION (Step {action_index + 1} of {total_actions})

Action Type: {planned_action.action_type}
Card: {planned_action.card_name or "N/A"}
Card ID: {planned_action.card_id or "N/A"}{target_info}
Expected CC Cost: {planned_action.cc_cost}
Expected CC After: {planned_action.cc_after}
Plan Reasoning: {planned_action.reasoning}

## CURRENT STATE
CC Available: {current_cc}{validation_hint}

{valid_actions_text}

## Instructions
1. Find the action that matches: {planned_action.action_type} {f'with {planned_action.card_name}' if planned_action.card_name else ''}
2. If the planned card is NOT in the list, return the "End turn" action number
3. If targets are needed, select from the target options
4. Return the action_number (1-based) from the valid actions list

Select the matching action now."""

    return prompt


def get_replan_prompt(
    original_plan: TurnPlan,
    completed_actions: List[PlannedAction],
    failed_action: PlannedAction,
    failure_reason: str,
    valid_actions_text: str,
    current_cc: int,
) -> str:
    """
    Build a prompt to select an alternative action when planned action fails.
    
    Args:
        original_plan: The original TurnPlan
        completed_actions: Actions already executed successfully
        failed_action: The action that couldn't be executed
        failure_reason: Why the action failed
        valid_actions_text: Current valid actions
        current_cc: Current CC available
        
    Returns:
        Replan prompt string
    """
    completed_summary = "\n".join([
        f"  ✓ {a.action_type}: {a.card_name or 'N/A'}"
        for a in completed_actions
    ]) if completed_actions else "  (none yet)"
    
    prompt = f"""{EXECUTION_SYSTEM_PROMPT}

## PLAN DEVIATION - SELECT ALTERNATIVE

The planned action could not be executed:
- Planned: {failed_action.action_type} {failed_action.card_name or ''}
- Reason: {failure_reason}

## Original Plan Strategy
{original_plan.selected_strategy}

## Actions Completed
{completed_summary}

## Current State
CC Available: {current_cc}

{valid_actions_text}

## Instructions
Select the best alternative action:
1. If the plan goal can still be achieved, choose an action toward that goal
2. If not, choose the most efficient offensive action available
3. If nothing productive can be done, choose "End turn"

Select an alternative action now."""

    return prompt


# =============================================================================
# Action Matching Utilities
# =============================================================================

def find_matching_action_index(
    planned_action: PlannedAction,
    valid_actions: list,
) -> Optional[int]:
    """
    Try to find the matching action index without LLM call.
    
    This is a heuristic matcher that handles common cases:
    - end_turn always matches "End turn"
    - play_card matches "Play {card_name}"
    - direct_attack matches "Direct attack"
    - tussle matches actions containing "tussle" and card_name
    
    Args:
        planned_action: The planned action to match
        valid_actions: List of ValidAction objects
        
    Returns:
        0-based index if match found, None if LLM needed
    """
    action_type = planned_action.action_type
    card_name = planned_action.card_name
    _card_id = planned_action.card_id  # Reserved for future card ID matching
    
    for i, action in enumerate(valid_actions):
        desc_lower = action.description.lower()
        
        # Match end_turn
        if action_type == "end_turn" and "end turn" in desc_lower:
            return i
        
        # Match play_card
        if action_type == "play_card" and card_name:
            if f"play {card_name.lower()}" in desc_lower:
                return i
        
        # Match direct_attack
        if action_type == "direct_attack" and "direct attack" in desc_lower:
            return i
        
        # Match tussle - look for tussle actions with the card
        if action_type == "tussle" and card_name:
            if "tussle" in desc_lower and card_name.lower() in desc_lower:
                return i
        
        # Match activate_ability - look for ability actions
        if action_type == "activate_ability" and card_name:
            if "ability" in desc_lower or "activate" in desc_lower:
                if card_name.lower() in desc_lower:
                    return i
            # Archer special case: "Use Archer to remove stamina"
            if card_name.lower() == "archer" and "archer" in desc_lower and "stamina" in desc_lower:
                return i
    
    # No match found - will need LLM
    return None


def extract_target_from_action(
    valid_action,
    planned_targets: Optional[List[str]] = None,
) -> Optional[List[str]]:
    """
    Extract target IDs from a valid action or use planned targets.
    
    For simple actions (single target), try to extract from the action.
    For complex actions (multiple targets like Sun), use planned_targets.
    
    Args:
        valid_action: The ValidAction being executed
        planned_targets: Target IDs from the plan
        
    Returns:
        List of target IDs or None
    """
    # If planned targets were specified, use them
    if planned_targets:
        return planned_targets
    
    # Try to extract from action's target_options if only one option
    if hasattr(valid_action, 'target_options') and valid_action.target_options:
        if len(valid_action.target_options) == 1:
            # Single target option - use it
            return [valid_action.target_options[0].card_id]
    
    return None


# =============================================================================
# JSON Schema for Execution Response
# =============================================================================

EXECUTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "action_number": {
            "type": "integer",
            "description": "1-based action number from valid actions list",
            "minimum": 1
        },
        "target_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Target card IDs if action requires targets"
        },
        "alternative_cost_id": {
            "type": "string",
            "description": "Card ID for alternative cost payment (Ballaber)"
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of action selection"
        }
    },
    "required": ["action_number", "reasoning"]
}
