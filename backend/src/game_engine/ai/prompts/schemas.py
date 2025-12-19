"""
Pydantic schemas for AI player structured output.

This module defines the JSON schema that Gemini uses for structured output,
ensuring the AI always returns valid, parseable responses.

Version 3.0: Added TurnPlan schema for turn-level planning architecture.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# Version tracking for AI decision logs
# Increment this when making significant changes to prompts or strategy
# Format: MAJOR.MINOR (MAJOR = strategy overhaul, MINOR = tweaks/fixes)
PROMPTS_VERSION = "3.0"


# =============================================================================
# v2.x Schema (kept for fallback and execution phase)
# =============================================================================

class AIDecision(BaseModel):
    """
    Schema for AI player decisions (v2.x single-action selection).
    Uses Pydantic for Gemini's native structured output mode.
    Used in v3 for execution phase (matching plan steps to valid actions).
    """
    action_number: int = Field(
        ...,
        description="Action number from the valid actions list (1-indexed)",
        ge=1  # Must be >= 1
    )
    reasoning: str = Field(
        ...,
        description="1-2 sentence explanation of why this is the best move",
        max_length=200
    )
    target_ids: Optional[List[str]] = Field(
        default=None,
        description="Array of target card UUIDs. Use for targeting cards (Twist, Wake, Copy, Sun, tussles). Extract ONLY the UUID from [ID: xxx], never card names."
    )
    alternative_cost_id: Optional[str] = Field(
        default=None,
        description="UUID of card to sleep for alternative cost (Ballaber). Extract ONLY the UUID from [ID: xxx]."
    )


# =============================================================================
# v3.0 Turn Planning Schema
# =============================================================================

class PlannedAction(BaseModel):
    """Single action in the turn plan sequence."""
    action_type: Literal["play_card", "tussle", "activate_ability", "direct_attack", "end_turn"] = Field(
        ...,
        description="Type of action to perform"
    )
    card_id: Optional[str] = Field(
        default=None,
        description="UUID of the card performing or being played. Extract from [ID: xxx]."
    )
    card_name: Optional[str] = Field(
        default=None,
        description="Human-readable card name for logging (e.g., 'Archer', 'Knight')"
    )
    target_ids: Optional[List[str]] = Field(
        default=None,
        description="Target card UUID(s). For tussle: defender. For abilities/effects: target(s)."
    )
    target_names: Optional[List[str]] = Field(
        default=None,
        description="Human-readable target names for logging"
    )
    alternative_cost_id: Optional[str] = Field(
        default=None,
        description="UUID of card to sleep for alternative cost (Ballaber)"
    )
    cc_cost: int = Field(
        ...,
        description="CC cost for this action (0 for free cards, 2 for standard tussle)"
    )
    cc_after: int = Field(
        ...,
        description="Expected CC remaining after this action completes"
    )
    reasoning: str = Field(
        ...,
        description="Why this specific action at this point in the sequence"
    )


class TurnPlan(BaseModel):
    """
    Complete turn plan generated using the 4-phase framework.
    
    Phase 1: Threat Assessment - Evaluate opponent's board
    Phase 2: Resource Inventory - Catalog available tools and sequences
    Phase 3: Threat Mitigation - Generate and select removal sequences
    Phase 4: Offensive Opportunities - Direct attacks with remaining CC
    """
    # Phase 1: Threat Assessment
    threat_assessment: str = Field(
        ...,
        description="Summary of opponent threats by priority (CRITICAL > HIGH > MEDIUM > LOW)"
    )
    
    # Phase 2: Resource Inventory
    resources_summary: str = Field(
        ...,
        description="Summary of available action cards, toys in play, toys in hand, and CC budget"
    )
    
    # Phase 3: Viable sequences considered
    sequences_considered: List[str] = Field(
        ...,
        description="List of action sequences evaluated with their CC costs and outcomes"
    )
    
    # Selected strategy
    selected_strategy: str = Field(
        ...,
        description="The chosen strategy and why (e.g., 'Archer removal path: sleep Knight and Paper Plane for 4 CC')"
    )
    
    # Phase 4: Action Sequence
    action_sequence: List[PlannedAction] = Field(
        ...,
        description="Ordered list of actions to execute this turn"
    )
    
    # CC Budget tracking
    cc_start: int = Field(
        ...,
        description="CC available at turn start"
    )
    cc_after_plan: int = Field(
        ...,
        description="Expected CC remaining after all planned actions"
    )
    
    # Efficiency calculation
    expected_cards_slept: int = Field(
        ...,
        description="Number of opponent cards expected to be slept by this plan"
    )
    cc_efficiency: str = Field(
        ...,
        description="CC efficiency calculation (e.g., '4 CC to sleep 2 cards = 2.0 CC per card')"
    )
    
    # Overall reasoning
    plan_reasoning: str = Field(
        ...,
        description="High-level explanation of why this plan was selected over alternatives"
    )


# Generate JSON Schema for TurnPlan (for Gemini structured output)
_turn_plan_schema = TurnPlan.model_json_schema()

# Simplified JSON schema for Gemini (flattening nested $defs)
TURN_PLAN_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "threat_assessment": {
            "type": "string",
            "description": "Summary of opponent threats by priority (CRITICAL > HIGH > MEDIUM > LOW)"
        },
        "resources_summary": {
            "type": "string",
            "description": "Summary of available action cards, toys in play, toys in hand, and CC budget"
        },
        "sequences_considered": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5,
            "description": "List of 3-5 action sequences evaluated with their CC costs and outcomes"
        },
        "selected_strategy": {
            "type": "string",
            "description": "The chosen strategy and why"
        },
        "action_sequence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action_type": {
                        "type": "string",
                        "enum": ["play_card", "tussle", "activate_ability", "direct_attack", "end_turn"],
                        "description": "Type of action to perform"
                    },
                    "card_id": {
                        "type": ["string", "null"],
                        "description": "UUID of the card performing or being played"
                    },
                    "card_name": {
                        "type": ["string", "null"],
                        "description": "Human-readable card name for logging"
                    },
                    "target_ids": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                        "description": "Target card UUID(s)"
                    },
                    "target_names": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                        "description": "Human-readable target names"
                    },
                    "alternative_cost_id": {
                        "type": ["string", "null"],
                        "description": "UUID of card to sleep for alternative cost"
                    },
                    "cc_cost": {
                        "type": "integer",
                        "description": "CC cost for this action"
                    },
                    "cc_after": {
                        "type": "integer",
                        "description": "Expected CC remaining after this action"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why this specific action"
                    }
                },
                "required": ["action_type", "cc_cost", "cc_after", "reasoning"]
            },
            "description": "Ordered list of actions to execute"
        },
        "cc_start": {
            "type": "integer",
            "description": "CC available at turn start"
        },
        "cc_after_plan": {
            "type": "integer",
            "description": "Expected CC after all actions"
        },
        "expected_cards_slept": {
            "type": "integer",
            "description": "Number of opponent cards expected to sleep"
        },
        "cc_efficiency": {
            "type": "string",
            "description": "CC efficiency calculation"
        },
        "plan_reasoning": {
            "type": "string",
            "description": "Why this plan was selected"
        }
    },
    "required": [
        "threat_assessment",
        "resources_summary", 
        "sequences_considered",
        "selected_strategy",
        "action_sequence",
        "cc_start",
        "cc_after_plan",
        "expected_cards_slept",
        "cc_efficiency",
        "plan_reasoning"
    ],
    "propertyOrdering": [
        "threat_assessment",
        "resources_summary",
        "sequences_considered", 
        "selected_strategy",
        "action_sequence",
        "cc_start",
        "cc_after_plan",
        "expected_cards_slept",
        "cc_efficiency",
        "plan_reasoning"
    ]
}


# =============================================================================
# v2.x JSON Schema (kept for fallback and execution phase)
# =============================================================================

# Generate JSON Schema from Pydantic model
# This ensures the schema stays in sync with the model definition
_generated_schema = AIDecision.model_json_schema()

# Customize the schema for Gemini's structured output requirements
AI_DECISION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "action_number": {
            "type": "integer",
            "description": _generated_schema["properties"]["action_number"]["description"],
            "minimum": 1
        },
        "reasoning": {
            "type": "string",
            "description": _generated_schema["properties"]["reasoning"]["description"]
        },
        "target_ids": {
            "type": ["array", "null"],
            "items": {"type": "string"},
            "description": _generated_schema["properties"]["target_ids"]["description"]
        },
        "alternative_cost_id": {
            "type": ["string", "null"],
            "description": _generated_schema["properties"]["alternative_cost_id"]["description"]
        }
    },
    "required": ["action_number", "reasoning"],
    "propertyOrdering": ["action_number", "reasoning", "target_ids", "alternative_cost_id"]
}


# =============================================================================
# Future Improvements TODO
# =============================================================================
# TODO: Add CC efficiency tracking to game logging for all games (not just simulations)
# This will allow measuring CC spent per card slept across all game types.
# Currently, this data exists in simulation results but could be added to:
# - Game completion events
# - AI decision logs  
# - Stats service aggregations
# See: AI_V3_SESSION_PROMPT.md for target metrics (≤ 2.5 CC per card slept)
