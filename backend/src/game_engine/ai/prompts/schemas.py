"""
Pydantic schemas for AI player structured output.

This module defines the JSON schema that Gemini uses for structured output,
ensuring the AI always returns valid, parseable responses.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# Version tracking for AI decision logs
# Increment this when making significant changes to prompts or strategy
# Format: MAJOR.MINOR (MAJOR = strategy overhaul, MINOR = tweaks/fixes)
PROMPTS_VERSION = "3.1"


# =============================================================================
# Turn Planning Schema
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
        description="UUID of card to break for alternative cost (Ballaber)"
    )
    charge_cost: int = Field(
        ...,
        ge=0,
        description="Charge cost for this action (0 for free cards, 2 for standard tussle)"
    )
    charge_after: int = Field(
        ...,
        ge=0,
        description="Expected Charge remaining after this action. Formula: charge_before - charge_cost + charge_gained"
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
    Phase 4: Offensive Opportunities - Direct attacks with remaining Charge
    """
    # Phase 1: Threat Assessment
    threat_assessment: str = Field(
        ...,
        description="Summary of opponent threats by priority (CRITICAL > HIGH > MEDIUM > LOW)"
    )

    # Phase 2: Resource Inventory
    resources_summary: str = Field(
        ...,
        description="Summary of available action cards, toys in play, toys in hand, and Charge budget"
    )

    # Phase 3: Viable sequences considered
    sequences_considered: List[str] = Field(
        ...,
        description="List of action sequences evaluated with their Charge costs and outcomes"
    )

    # Selected strategy
    selected_strategy: str = Field(
        ...,
        description="The chosen strategy and why (e.g., 'Archer removal path: break Knight and Paper Plane for 4 Charge')"
    )

    # Phase 4: Action Sequence
    action_sequence: List[PlannedAction] = Field(
        ...,
        description="Ordered list of actions to execute this turn"
    )

    # Charge Budget tracking
    charge_start: int = Field(
        ...,
        description="Charge available at turn start"
    )
    charge_after_plan: int = Field(
        ...,
        description="Expected Charge remaining after all planned actions"
    )

    # Efficiency calculation
    expected_cards_broken: int = Field(
        ...,
        description="Total opponent cards expected to break by ANY method (tussle wins, direct attacks, Drop, Archer ability, Monster effect)"
    )

    # Overall reasoning
    plan_reasoning: str = Field(
        ...,
        description="Brief (1-3 sentences) explanation of why this plan was selected. Do NOT repeat analysis.",
        max_length=500
    )

    # Residual Charge justification (v3.1)
    residual_charge_justification: Optional[str] = Field(
        default=None,
        description="If ending with Charge >= 2, explain why no further attacks were possible"
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
            "description": "Summary of available action cards, toys in play, toys in hand, and Charge budget"
        },
        "sequences_considered": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5,
            "description": "List of 3-5 action sequences evaluated with their Charge costs and outcomes"
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
                        "description": "UUID of card to break for alternative cost"
                    },
                    "charge_cost": {
                        "type": "integer",
                        "description": "Charge cost for this action",
                        "minimum": 0
                    },
                    "charge_after": {
                        "type": "integer",
                        "description": "Expected Charge remaining after this action. MUST be >= 0. Formula: charge_before - charge_cost + charge_gained (Surge +1, Rush +2)",
                        "minimum": 0
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why this specific action"
                    }
                },
                "required": ["action_type", "charge_cost", "charge_after", "reasoning"]
            },
            "description": "Ordered list of actions to execute"
        },
        "charge_start": {
            "type": "integer",
            "description": "Charge available at turn start"
        },
        "charge_after_plan": {
            "type": "integer",
            "description": "Expected Charge after all actions"
        },
        "expected_cards_broken": {
            "type": "integer",
            "description": "Total opponent cards expected to break by ANY method (tussle wins, direct attacks, Drop, Archer ability, Monster effect)"
        },
        "plan_reasoning": {
            "type": "string",
            "description": "Brief (1-3 sentences) explanation of why this plan was selected. Do NOT repeat analysis.",
            "maxLength": 500
        },
        "residual_charge_justification": {
            "type": ["string", "null"],
            "description": "If ending with Charge >= 2, explain why no further attacks were possible"
        }
    },
    "required": [
        "threat_assessment",
        "resources_summary",
        "sequences_considered",
        "selected_strategy",
        "action_sequence",
        "charge_start",
        "charge_after_plan",
        "expected_cards_broken",
        "plan_reasoning"
    ],
    "propertyOrdering": [
        "threat_assessment",
        "resources_summary",
        "sequences_considered",
        "selected_strategy",
        "action_sequence",
        "charge_start",
        "charge_after_plan",
        "expected_cards_broken",
        "plan_reasoning",
        "residual_charge_justification"
    ]
}
