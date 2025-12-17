# Backend Audit Status

- **Issue**: [#196]
- **Branch**: `fix/backend-audit-196`
- **Last Updated**: 2025-12-05

## Summary

- **1. ID-Based Lookups**
  - Violations: 2
  - Severity: 🔴 Critical
  - Status: ✅ Fixed

- **2. Method-Based State Modification**
  - Violations: 1
  - Severity: 🟡 Medium
  - Status: ✅ Reviewed (Acceptable)

- **3. GameEngine vs GameState Separation**
  - Violations: 0
  - Status: ✅ Clean

- **4. Owner vs Controller**
  - Violations: 0
  - Status: ✅ Clean

- **5. Effect System Architecture**
  - Violations: 0
  - Status: ✅ Fixed (via #1.2)

- **6. Single Source of Truth**
  - Violations: 1
  - Severity: 🟢 Low
  - Status: ✅ Fixed (Dead code removed)

- **Documentation**
  - Violations: 1
  - Severity: 🟢 Low
  - Status: ✅ Fixed

---

## 1. ID-Based Lookups ✅ FIXED

### 1.1 Name-based target lookup in Copy cost calculation

- **Location**: `backend/src/game_engine/game_engine.py:203`
- **Issue**: Used `c.name == target_name` to find card by name
- **Fix**: Changed to use `target_id` parameter and `find_card_by_id()`
- **Status**: ✅ Fixed

### 1.2 Name-based card check for Wizard effect

- **Location**: `backend/src/game_engine/game_engine.py:600`
- **Issue**: Used `card_in_play.name == "Wizard"` to identify Wizard
- **Fix**: Now checks for `SetTussleCostEffect` type instead of hardcoded name
- **Status**: ✅ Fixed

---

## 2. Method-Based State Modification ✅ REVIEWED

### 2.1 CopyEffect directly assigns stats

- **Location**:
  `backend/src/game_engine/rules/effects/action_effects.py:337-341`
- **Issue**: Directly assigns `.speed`, `.strength`, `.stamina` to copy card
- **Analysis**: This is card **initialization** during Copy effect, not
  damage/modification during play. The Copy card is a fresh entity that needs
  its base stats set.
- **Decision**: **Acceptable** - This is initial setup, not runtime
  modification. No fix needed.
- **Status**: ✅ Reviewed (Acceptable)

---

## 3. GameEngine vs GameState Separation ✅ CLEAN

Zone manipulation in `GameState` methods is **intentional and appropriate**:

- `game_state.py:242-248` - `change_card_controller()` - Data operation for
  Twist
- `game_state.py:265` - `play_card_from_hand()` - Used by Beary's effect
- `player.py:70-84` - Helper methods for zone management

These are **data access layer** operations called by GameEngine. The logic lives
in GameEngine.

---

## 4. Owner vs Controller ✅ CLEAN

The `_sleep_card()` method correctly handles owner vs controller.

Verified that stolen cards return to owner's sleep zone.

---

## 5. Effect System Architecture ✅ FIXED

The hardcoded card name checks in `turn_manager.py` were **dead code** (unused
methods). They have been removed as part of Fix 6.1.

The active code in `game_engine.py` now uses proper effect type checking
(`isinstance(effect, SetTussleCostEffect)`).

---

## 6. Single Source of Truth ✅ FIXED

### 6.1 Dead code in TurnManager

- **Location**: `backend/src/game_engine/rules/turn_manager.py:88-164`
- **Issue**: `get_tussle_cost`, `calculate_card_cost`, and `can_raggy_tussle`
  were unused
- **Fix**: Removed all three dead methods
- **Status**: ✅ Fixed

---

## 7. Documentation ✅ FIXED

### 7.1 API docstring mentions card_name instead of card_id

- **Location**: `backend/src/api/routes_actions.py:45-47`
- **Issue**: Docstring said "card_name" but actual API uses `card_id`
- **Fix**: Updated docstring to match actual schema (card_id, target_card_id)
- **Status**: ✅ Fixed

---

## Changes Made

- `game_engine.py` — Use `target_id` in `calculate_card_cost()`
- `game_engine.py` — Use effect type check in `calculate_tussle_cost()`
- `action_executor.py` — Add `target_id` to kwargs for Copy card support
- `turn_manager.py` — Remove unused methods (dead code removed)
- `routes_actions.py` — Fix docstring to reference `card_id`

---

## Testing

All 123 tests pass after fixes:

```bash
pytest backend/tests/ -v
================= 123 passed, 2 skipped, 39 warnings in 0.96s ==================
```

[#196]: https://github.com/RegisCA/ggltcg/issues/196

## Conclusion

The backend codebase is **cleaner than expected**. Most architectural principles
are followed correctly:

- ✅ GameEngine vs GameState separation is proper
- ✅ Owner vs Controller handling is correct
- ✅ Zone manipulation is appropriately layered
- ✅ Effect system uses proper type checking (after fixes)

Only **4 actual violations** were found:

1. One name-based lookup (Copy cost calculation)
2. One hardcoded card name (Wizard check)
3. Dead code in TurnManager
4. Outdated API docstring

All have been fixed.
