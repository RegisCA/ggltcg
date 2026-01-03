"""
AI Validation Layer

This module provides validators for AI turn plans that catch multi-step
reasoning errors that the game engine doesn't detect. The game engine
validates individual actions, but these validators ensure the entire
sequence is consistent.

Validators:
- CCBudgetValidator: Prevents negative CC in action sequences
- OpponentToyTracker: Prevents illegal direct attacks mid-plan
- SuicideAttackValidator: Prevents guaranteed-loss tussles
- DependencyValidator: Ensures correct action ordering (Wake before play, etc.)
"""

from .turn_plan_validator import (
    TurnPlanValidator,
    ValidationError,
    CCBudgetValidator,
    OpponentToyTracker,
    SuicideAttackValidator,
    DependencyValidator,
)

__all__ = [
    "TurnPlanValidator",
    "ValidationError",
    "CCBudgetValidator",
    "OpponentToyTracker",
    "SuicideAttackValidator",
    "DependencyValidator",
]
