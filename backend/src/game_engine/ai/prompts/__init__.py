"""
AI Prompts Module

This module contains all prompt templates and schemas for the AI player.
Split into logical submodules for maintainability:

- schemas.py: Pydantic models and JSON schemas for structured output
- card_library.py: Card effect descriptions and strategic hints
- system_prompt.py: Core rules and decision framework
- formatters.py: Functions to format game state and actions for AI
- narrative.py: Prompts for generating story narratives
- planning_prompt.py: v3 turn planning framework prompt (4-phase)
"""

from .schemas import (
    AIDecision,
    AI_DECISION_JSON_SCHEMA,
    PROMPTS_VERSION,
    # v3 Turn Planning
    PlannedAction,
    TurnPlan,
    TURN_PLAN_JSON_SCHEMA,
)
from .card_library import CARD_EFFECTS_LIBRARY
from .system_prompt import SYSTEM_PROMPT, ACTION_SELECTION_PROMPT
from .formatters import (
    format_game_state_for_ai,
    format_valid_actions_for_ai,
    get_ai_turn_prompt,
)
from .narrative import (
    NARRATIVE_PROMPT,
    get_narrative_prompt,
)
from .planning_prompt import (
    get_planning_prompt,
    format_hand_for_planning,
    format_in_play_for_planning,
    format_sleep_zone_for_planning,
    THREAT_PRIORITIES,
    CC_COST_REFERENCE,
)

__all__ = [
    # Schemas (v2.x)
    "AIDecision",
    "AI_DECISION_JSON_SCHEMA",
    "PROMPTS_VERSION",
    # Schemas (v3 Turn Planning)
    "PlannedAction",
    "TurnPlan",
    "TURN_PLAN_JSON_SCHEMA",
    # Card Library
    "CARD_EFFECTS_LIBRARY",
    # System Prompt
    "SYSTEM_PROMPT",
    # Formatters
    "format_game_state_for_ai",
    "format_valid_actions_for_ai",
    "get_ai_turn_prompt",
    "ACTION_SELECTION_PROMPT",
    # Narrative
    "NARRATIVE_PROMPT",
    "get_narrative_prompt",
    # v3 Planning
    "get_planning_prompt",
    "format_hand_for_planning",
    "format_in_play_for_planning",
    "format_sleep_zone_for_planning",
    "THREAT_PRIORITIES",
    "CC_COST_REFERENCE",
]
