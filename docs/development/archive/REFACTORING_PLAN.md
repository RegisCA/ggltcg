> **Historical Document**: This refactoring has been completed.

# GGLTCG Refactoring Plan

**Created:** November 20, 2025  
**Completed:** November 21, 2025  
**Status:** ✅ COMPLETE (Phases 1-3 finished, Phase 4 integrated into Phase 3)  
**Priority:** High  
**Branch:** `refactor/action-architecture` (ready for PR)

## Executive Summary

This refactoring successfully addressed critical architectural issues identified during the November 20, 2025 debugging session. The main problems were:

1. ~~**Code Duplication**~~: ✅ RESOLVED - Three separate code paths consolidated
2. ~~**Type Safety**~~: ✅ IMPROVED - Structured action types implemented

**Results:**
- **~457 lines of duplicate code eliminated**
- **Single source of truth** for validation (`ActionValidator`)
- **Single source of truth** for execution (`ActionExecutor`)
- **Consistent behavior** between human and AI players
- **Easier to maintain** - bugs only need to be fixed once

## Problem Statement

### Issue #1: Code Duplication Between AI and Human Player Paths

**Current Architecture:**

```
Human Player Path:
  POST /play-card → routes_actions.py (lines 53-250)
    → Validate action
    → Check effects for targets
    → Build description
    → Call engine.play_card()
    → Return response

AI Player Path:
  POST /ai-turn → routes_actions.py (lines 555-950)
    → Get valid actions
    → Call LLM to select action
    → [DUPLICATE] Check effects for targets
    → [DUPLICATE] Build description
    → [DUPLICATE] Call engine.play_card() with kwargs
    → Return response

Valid Actions Path:
  GET /valid-actions → routes_actions.py (lines 252-553)
    → [DUPLICATE] Check effects for targets
    → Build action list
    → Return actions
```

**Problems:**

- Effect checking logic appears in 2 places (valid actions + AI turn)
- Target validation duplicated
- Description building duplicated
- Cost calculation duplicated
- Bug fixes must be applied to multiple locations
- Inconsistent behavior between paths

**Example Bug from Nov 20:**

Twist effect wasn't working for AI because the `target` kwarg wasn't being passed to `engine.play_card()` in the AI turn endpoint, even though it was being passed in the human player endpoint.

### Issue #2: Complex and Ambiguous Function Arguments

**Current Pattern:**

```python
def play_card(
    self,
    player: Player,
    card: Card,
    target: Optional[Card] = None,           # Sometimes used
    target_name: Optional[str] = None,       # Why both?
    targets: Optional[List[Card]] = None,    # Plural for Sun
    alternative_cost_paid: bool = False,
    alternative_cost_card: Optional[str] = None,  # Name not object!
    **kwargs                                  # More unknown args
) -> None:
```

**Problems:**

- Hard to know what arguments are required for each card
- Mixing card objects (`target`) and card names (`alternative_cost_card`)
- Kwargs hide what's being passed
- Easy to forget required arguments
- Type checking doesn't help catch errors
- Different conventions (singular `target` vs plural `targets`)

## Proposed Solution

### Architecture Refactoring

**Desired Architecture:**

```
Human Player Path:
  POST /play-card → routes_actions.py
    → Parse request → PlayCardAction
    → ActionValidator.validate(action)
    → ActionExecutor.execute(action)
    → Return response

AI Player Path:
  POST /ai-turn → routes_actions.py
    → ActionValidator.get_valid_actions()
    → LLM selects action → PlayCardAction
    → ActionValidator.validate(action)  # Same validator!
    → ActionExecutor.execute(action)    # Same executor!
    → Return response

Valid Actions Path:
  GET /valid-actions → routes_actions.py
    → ActionValidator.get_valid_actions()  # Same validator!
    → Return actions
```

**Key Principles:**

1. **Single Source of Truth**: One place for validation logic, one place for execution logic
2. **Structured Types**: Replace kwargs with explicit dataclasses
3. **Separation of Concerns**: Validation separate from execution
4. **Testability**: Easy to unit test validators and executors independently

### Type System Refactoring

**Proposed Action Types:**

```python
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

class ActionType(Enum):
    PLAY_CARD = "play_card"
    TUSSLE = "tussle"
    END_TURN = "end_turn"
    DIRECT_ATTACK = "direct_attack"

@dataclass
class GameAction:
    """Base class for all game actions."""
    action_type: ActionType
    player_id: str

@dataclass
class PlayCardAction(GameAction):
    """Action to play a card from hand."""
    card_id: str
    target_ids: List[str] = field(default_factory=list)
    alternative_cost_card_id: Optional[str] = None
    
    def __post_init__(self):
        self.action_type = ActionType.PLAY_CARD

@dataclass
class TussleAction(GameAction):
    """Action to initiate a tussle."""
    attacker_id: str
    defender_id: str
    
    def __post_init__(self):
        self.action_type = ActionType.TUSSLE

@dataclass
class EndTurnAction(GameAction):
    """Action to end the current turn."""
    
    def __post_init__(self):
        self.action_type = ActionType.END_TURN
```

**Benefits:**

- ✅ All required fields explicitly declared
- ✅ Type checking catches missing fields at compile time
- ✅ Self-documenting (you can see what's needed)
- ✅ Consistent use of card IDs (not mixing IDs and names)
- ✅ Easy to serialize/deserialize for API

## Implementation Status

### ✅ Phase 1: Foundation - COMPLETE (Nov 21, 2025)

**Completed Tasks:**
- ✅ Created action type definitions (`actions.py`)
- ✅ Created helper functions for duplicated logic
- ✅ Validated with full game playthrough

**Files Created:**
- `/backend/src/game_engine/models/actions.py` (78 lines)

**Code Impact:**
- Reduced `routes_actions.py` by ~100 lines
- Established pattern for structured actions

### ✅ Phase 2: Action Validation - COMPLETE (Nov 21, 2025)

**Completed Tasks:**
- ✅ Created `ActionValidator` class
- ✅ Extracted valid action generation logic
- ✅ Consolidated effect checking logic
- ✅ Fixed Bug #1: `player.id` → `player.player_id`
- ✅ Fixed Bug #2: Pydantic ValidAction vs dataclass mismatch
- ✅ Validated with full game playthrough

**Files Created:**
- `/backend/src/game_engine/validation/action_validator.py` (372 lines)

**Code Impact:**
- Reduced `routes_actions.py` from 880 to 684 lines (-196 lines)
- Single source of truth for validation

### ✅ Phase 3: Action Execution - COMPLETE (Nov 21, 2025)

**Completed Tasks:**
- ✅ Created `ActionExecutor` class
- ✅ Migrated execution logic from routes to executor
- ✅ Migrated description building logic
- ✅ Refactored `play_card` endpoint to use executor
- ✅ Refactored `ai_take_turn` endpoint to use executor
- ✅ Removed helper functions (now in executor)
- ✅ Fixed Bug #3: `request.player_id` → `player_id` parameter
- ✅ Validated with full game playthrough

**Files Created:**
- `/backend/src/game_engine/validation/action_executor.py` (420 lines)

**Code Impact:**
- Reduced `routes_actions.py` from 684 to 523 lines (-161 lines)
- Single source of truth for execution
- Both human and AI paths use identical code

### ✅ Phase 4: Refactor API Endpoints - INTEGRATED INTO PHASE 3

**Note:** Phase 4 tasks were completed as part of Phase 3 implementation:
- ✅ Refactored `POST /play-card` endpoint
- ✅ Refactored `POST /ai-turn` endpoint
- ✅ Deleted duplicated code (helper functions)
- ✅ Both endpoints use `ActionValidator` and `ActionExecutor`

### ⏸️ Phase 5: Cleanup and Documentation - IN PROGRESS

**Completed Tasks:**
- ✅ Updated `ARCHITECTURE.md` with new design
- ✅ Updated `REFACTORING_PLAN.md` status
- ✅ Updated `SESSION_NOTES_2025-11-21.md`

**Remaining Tasks:**
- [ ] Update `COPILOT_CONTEXT.md` with new patterns
- [ ] Consider adding unit tests for ActionValidator and ActionExecutor
- [ ] Consider improving test coverage

## Final Metrics

**Code Reduction:**
- Phase 1: ~100 lines removed
- Phase 2: ~196 lines removed
- Phase 3: ~161 lines removed
- **Total: ~457 lines of duplication eliminated**

**Code Added:**
- `actions.py`: 78 lines
- `action_validator.py`: 372 lines
- `action_executor.py`: 420 lines
- **Total: 870 lines of new, well-structured code**

**Net Impact:**
- Removed 457 lines of duplicate code
- Added 870 lines of organized, reusable code
- Net +413 lines, but with significantly better architecture
- `routes_actions.py`: 880 → 523 lines (-40%)

**Quality Improvements:**
- ✅ Single source of truth for validation
- ✅ Single source of truth for execution
- ✅ Consistent behavior across all code paths
- ✅ Bugs only need to be fixed once
- ✅ Easier to test (isolated components)
- ✅ Easier to extend (clear patterns)

## Implementation Plan

The original implementation plan is preserved below for reference, with status annotations.

---

### Phase 1: Add Structured Action Types ✅ COMPLETE

**Goal:** Introduce action dataclasses without breaking existing code

**Tasks:**

1. Create `backend/src/game_engine/models/actions.py`
   - Define `GameAction`, `PlayCardAction`, `TussleAction`, `EndTurnAction`
   - Add unit tests for action creation

2. Update API schemas in `backend/src/api/schemas.py`
   - Add Pydantic models that mirror action dataclasses
   - Keep existing schemas for backwards compatibility

**Estimated Effort:** 2 hours

**Testing:**
- Unit tests for action creation
- Verify existing API still works

### Phase 2: Create ActionValidator

**Goal:** Single source of truth for what actions are valid

**Tasks:**

1. Create `backend/src/game_engine/rules/action_validator.py`

   ```python
   class ActionValidator:
       """Validates game actions and provides valid action lists."""
       
       def __init__(self, game_state: GameState):
           self.game_state = game_state
       
       def get_valid_actions(self, player_id: str) -> List[GameAction]:
           """Get all valid actions for a player."""
           pass
       
       def validate_action(self, action: GameAction) -> ValidationResult:
           """Validate if an action can be executed."""
           pass
       
       def get_target_options(self, card_id: str) -> List[str]:
           """Get valid target IDs for a card."""
           pass
   ```

2. Migrate effect checking logic from `routes_actions.py` to `ActionValidator`
   - Move `get_valid_targets()` calls
   - Move alternative cost checking
   - Move CC validation

3. Update `GET /valid-actions` endpoint to use `ActionValidator`

**Estimated Effort:** 4 hours

**Testing:**
- Unit tests for each validation method
- Integration test: valid actions endpoint returns same results as before
- Test edge cases (not enough CC, wrong phase, etc.)

### Phase 3: Create ActionExecutor

**Goal:** Single source of truth for how to execute actions

**Tasks:**

1. Create `backend/src/game_engine/rules/action_executor.py`

   ```python
   class ActionExecutor:
       """Executes validated game actions."""
       
       def __init__(self, game_engine: GameEngine):
           self.engine = game_engine
       
       def execute(self, action: GameAction) -> ExecutionResult:
           """Execute a validated action."""
           if isinstance(action, PlayCardAction):
               return self._execute_play_card(action)
           elif isinstance(action, TussleAction):
               return self._execute_tussle(action)
           # ... etc
       
       def _execute_play_card(self, action: PlayCardAction) -> ExecutionResult:
           """Execute a play card action."""
           pass
       
       def _build_description(self, action: GameAction) -> str:
           """Build human-readable description of action."""
           pass
   ```

2. Migrate execution logic from `routes_actions.py` to `ActionExecutor`
   - Move card playing logic
   - Move description building
   - Move effect resolution

3. Update `game_engine.play_card()` to use structured action
   - Change signature to accept `PlayCardAction` instead of kwargs
   - Simplify internal logic

**Estimated Effort:** 6 hours

**Testing:**
- Unit tests for each execution method
- Integration test: full game flow works
- Test all 18 cards still work correctly
- Compare play-by-play output with previous version

### Phase 4: Refactor API Endpoints

**Goal:** Use new validators and executors in all endpoints

**Tasks:**

1. Refactor `POST /play-card` endpoint
   - Parse request to `PlayCardAction`
   - Call `ActionValidator.validate()`
   - Call `ActionExecutor.execute()`
   - Return result

2. Refactor `POST /ai-turn` endpoint
   - Call `ActionValidator.get_valid_actions()`
   - LLM selects action
   - Parse to `PlayCardAction`
   - Call `ActionExecutor.execute()` (same path as human!)
   - Return result

3. Delete duplicated code
   - Remove effect checking from AI turn endpoint
   - Remove description building from AI turn endpoint
   - Remove target validation from AI turn endpoint

4. Refactor `POST /tussle` endpoint
   - Use `TussleAction`
   - Use `ActionExecutor`

**Estimated Effort:** 4 hours

**Testing:**
- Full integration tests for all endpoints
- Test human player can complete full game
- Test AI player can complete full game
- Test all card effects work for both players
- Regression test: compare behavior with previous version

### Phase 5: Cleanup and Documentation

**Goal:** Remove old code and update docs

**Tasks:**

1. Remove deprecated code paths
   - Old play_card signature (if replaced)
   - Unused helper functions

2. Update documentation
   - Update ARCHITECTURE.md with new design
   - Add docstrings to new classes
   - Update COPILOT_CONTEXT.md with new patterns

3. Add comprehensive tests
   - Add missing test cases
   - Achieve >80% code coverage for new modules

**Estimated Effort:** 2 hours

**Testing:**
- All existing tests pass
- New tests added for refactored code
- Coverage report shows >80% for action_validator and action_executor

## Total Effort Estimate

- **Phase 1:** 2 hours
- **Phase 2:** 4 hours
- **Phase 3:** 6 hours
- **Phase 4:** 4 hours
- **Phase 5:** 2 hours

**Total: ~18 hours (~2-3 development sessions)**

## Success Criteria

### Must Have ✅

1. **No Code Duplication**: Effect checking, validation, execution in single location
2. **Type Safety**: All actions use structured dataclasses, no kwargs
3. **All Tests Pass**: Existing behavior preserved, all cards work
4. **AI and Human Use Same Code**: Both paths use ActionValidator and ActionExecutor
5. **Documentation Updated**: ARCHITECTURE.md reflects new design

### Nice to Have 🎯

6. **Improved Test Coverage**: >80% coverage for new modules
7. **Performance**: No regression in API response times
8. **Logging**: Structured logging for action execution
9. **Debugging**: Clear error messages for validation failures

## Risks and Mitigations

### Risk 1: Breaking Existing Functionality

**Likelihood:** Medium
**Impact:** High

**Mitigation:**

- Keep existing code working during refactoring
- Add comprehensive integration tests before refactoring
- Refactor incrementally, one phase at a time
- Manual testing after each phase

### Risk 2: Time Estimate Too Low

**Likelihood:** Medium
**Impact:** Medium

**Mitigation:**

- Break into small, independently valuable phases
- Can stop after Phase 2 or 3 if needed
- Each phase delivers value on its own

### Risk 3: Unforeseen Edge Cases

**Likelihood:** Medium
**Impact:** Medium

**Mitigation:**

- Comprehensive test suite catches edge cases
- Manual testing with all 18 cards
- Keep old code available for reference

## Future Extensions

After this refactoring, these features become easier:

1. **Undo/Redo**: Actions are discrete objects, can be stored and reversed
2. **Game Replay**: Action log can be replayed to recreate game state
3. **Network Protocol**: Actions are already structured data, easy to serialize
4. **AI Improvements**: AI gets clean list of valid actions with all metadata
5. **Rule Changes**: Validation logic in one place, easy to modify

## References

- **Session Notes:** `docs/development/SESSION_NOTES_2025-11-20.md`
- **Current Architecture:** `docs/development/ARCHITECTURE.md`
- **Issue Tracker:** GitHub Issues #41, #50 (AI improvements completed)

## Approval and Timeline

**Proposed Start Date:** After PR #61 review complete
**Proposed Branch:** `refactor/action-architecture` from `feat/complete-card-effects`
**Review Required:** Yes (significant architectural change)
**Deployment Impact:** None (internal refactoring only)

---

**Next Steps:**

1. ✅ Create this document
2. Review and approve refactoring plan
3. Create feature branch
4. Begin Phase 1 implementation
5. Iterate through phases with testing after each
