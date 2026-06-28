"""
AI Prompts Module

This module contains all prompt templates and schemas for the AI player.
Split into logical submodules for maintainability:

- schemas.py: Pydantic models and JSON schemas for structured output
- card_guidance.yaml / card_loader.py: Card-specific traps/reminders/threats
- formatters.py: Functions to format valid actions for the execution prompt
- narrative.py: Prompts for generating story narratives
- execution_prompt.py: Action execution prompt (plan step -> action matching)
- sequence_format.py: Tactical labeling/display for enumerator sequences
- strategic_selector.py: Strategic-selection prompt (the planner's one LLM call)
"""

from .schemas import (
    PROMPTS_VERSION,
    PlannedAction,
    TurnPlan,
    TURN_PLAN_JSON_SCHEMA,
)
from .formatters import (
    format_valid_actions_for_ai,
)
from .narrative import (
    NARRATIVE_PROMPT,
    get_narrative_prompt,
)
from .execution_prompt import (
    get_execution_prompt,
    find_matching_action_index,
    EXECUTION_JSON_SCHEMA,
)

__all__ = [
    # Schemas
    "PROMPTS_VERSION",
    "PlannedAction",
    "TurnPlan",
    "TURN_PLAN_JSON_SCHEMA",
    # Formatters
    "format_valid_actions_for_ai",
    # Narrative
    "NARRATIVE_PROMPT",
    "get_narrative_prompt",
    # Execution
    "get_execution_prompt",
    "find_matching_action_index",
    "EXECUTION_JSON_SCHEMA",
]
