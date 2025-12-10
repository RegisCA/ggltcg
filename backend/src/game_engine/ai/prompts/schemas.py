"""
Pydantic schemas for AI player structured output.

This module defines the JSON schema that Gemini uses for structured output,
ensuring the AI always returns valid, parseable responses.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

# Version tracking for AI decision logs
# Increment this when making significant changes to prompts or strategy
# Format: MAJOR.MINOR (MAJOR = strategy overhaul, MINOR = tweaks/fixes)
PROMPTS_VERSION = "2.1"


class AIDecision(BaseModel):
    """
    Schema for AI player decisions.
    Uses Pydantic for Gemini's native structured output mode.
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
