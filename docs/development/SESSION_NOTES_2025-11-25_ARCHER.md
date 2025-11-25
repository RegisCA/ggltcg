# Session Notes: Archer Implementation & Activated Abilities System
**Date**: November 25, 2025  
**Focus**: Implement Archer's activated ability, complete frontend integration, clean up legacy code

---

## What We Accomplished

### 1. **Archer Activated Ability - Complete Implementation** ✅

**Backend Changes:**
- Modified `ActionValidator._get_valid_activated_abilities()` to create single ValidAction for 1 CC cost (repeatable)
- Fixed `ArcherActivatedAbility.get_valid_targets()` to only return opponent's cards in play (not both players)
- Fixed `ArcherActivatedAbility.apply()` to use `apply_damage()` instead of directly modifying `stamina`
  - **Critical Fix**: Direct stamina modification was changing base stats, not current stamina
  - Now properly uses `current_stamina` like tussle damage

**Frontend Changes:**
- Added `ActivateAbilityRequest` type to API types
- Created `activateAbility()` service function with correct endpoint `/games/{game_id}/activate-ability`
- Created `useActivateAbility()` React Query hook
- Added `activate_ability` case to `GameBoard.tsx` executeAction()
- Fixed `handleAction()` to check for target_options on activated abilities (was only checking play_card)

**Backend Route Fix:**
- Removed name-based card lookups (`request.card_name`, `request.target_card_name`)
- Now uses ID-based lookups (`request.card_id`, `request.target_id`)
- **Lesson**: This was legacy code that slipped through - we need to audit for more name-based logic

### 2. **AI Player Support for Activated Abilities** ✅

**Updated AI Guidance:**
- Added accurate Archer description to `CARD_EFFECTS_LIBRARY` in prompts.py
  - Effect: "Spend 1 CC to remove 1 stamina from target opponent card (can repeat)"
  - Strategic use: "Precision finisher - finish off damaged cards or weaken targets"
- Added `activate_ability` case to `LLMPlayer._build_action_request()` in llm_player.py
  - Handles target selection for activated abilities
  - Sets amount=1 (repeatable design)

---

## Critical Bugs Fixed

### Bug: Direct Stamina Modification
**Problem**: `target.stamina -= amount` was modifying base stamina, not current stamina  
**Impact**: Card showed wrong stats (e.g., "1/2" instead of "2/4")  
**Root Cause**: Direct attribute modification bypasses the proper damage system  
**Fix**: Changed to `target.apply_damage(amount)` which correctly updates `current_stamina`  

**Lesson Learned**: **NEVER** modify stats directly. Always use proper methods:
- ✅ `card.apply_damage(amount)` - for damage/stamina reduction
- ✅ `card.is_defeated()` - to check if card should be sleeped
- ❌ `card.stamina -= amount` - WRONG, modifies base stat
- ❌ `if card.stamina <= 0` - WRONG, checks base stamina not current

### Bug: Name-Based Card Lookups
**Problem**: `activate_ability` route was using `request.card_name` instead of `request.card_id`  
**Impact**: AttributeError crash, route didn't work at all  
**Root Cause**: Legacy code pattern from before ID-based refactoring  
**Fix**: Changed all lookups to use card IDs  

**Audit Needed**: Search codebase for other instances of name-based logic:
- `card.name ==` comparisons (except for specific effect checks like Knight/Beary)
- `request.card_name` or `request.target_card_name` in routes
- Any iteration looking for cards by name instead of ID

---

## Architecture Decisions

### Activated Abilities Design Pattern

**Single Action, Repeatable Execution:**
- Backend creates ONE ValidAction with cost 1 CC
- Player can execute multiple times per turn (as long as they have CC)
- Each execution requires new target selection
- Simple, flexible design that works for any cost-per-use ability

**Why Not Multi-Cost Options?**
- Initially tried creating 4 ValidActions (1 CC, 2 CC, 3 CC, 4 CC)
- User feedback: "Only show 1 CC option, players can repeat"
- Better UX: One button, repeatable actions
- More flexible: Works for any CC amount available

**Target Scoping:**
- Archer targets **opponent's cards only** (not both players)
- Different from Copy which targets **your own cards only**
- Target validation happens in `get_valid_targets()` method
- Frontend receives filtered list, no client-side filtering needed

---

## Code Quality & Technical Debt

### Issues Identified

**1. Legacy Name-Based Code Still Exists**
Locations to audit:
- `backend/src/game_engine/rules/tussle_resolver.py` - `_check_knight_auto_win()` uses `attacker.name == "Knight"`
- `backend/src/game_engine/rules/effects/` - Some effects check `card.name` for special cases
- All API routes - Need to verify all use IDs not names

**2. Direct Stat Modification Pattern**
Need to search for:
- `card.stamina =` or `card.stamina +=` or `card.stamina -=`
- `card.strength =` or similar
- `card.speed =` or similar
- Should use `apply_damage()`, `heal()`, or effect modifiers instead

**3. Effect System Still Partially Legacy**
Progress on data-driven migration (Phase 4):
- ✅ 17/18 cards migrated to `effect_definitions` in CSV
- ✅ Archer, Knight, Beary, Toynado, Twist, Copy, Ballaber all data-driven
- ❌ Snuggles still marked "NOT WORKING" in CSV
- ⏳ Legacy `EffectRegistry.get_instance().get_effects_by_card_name()` might still exist

---

## New Bugs Discovered

### Bug #1: AI Sees Unbuffed Stats in Valid Actions ⚠️

**Problem**: The ValidActions shown to AI player include base stats, not buffed stats from Ka/Demideca  
**Impact**: AI makes poor tussle decisions, attacking when it will lose  
**Example**: AI sees opponent's card as "2 STR" but Ka is giving it +2 STR, making it actually 4 STR  

**Root Cause**: `ActionValidator._get_valid_tussles()` might be showing base stats in descriptions  
**Fix Needed**: When building ValidAction descriptions, use `_get_stat_with_effects()` to show buffed stats  

**Files to Check**:
- `backend/src/game_engine/validation/action_validator.py` - ValidAction description building
- Need to ensure descriptions show effective stats, not base stats

### Bug #2: Sun Effect Broken 🚨 CRITICAL

**Problem**: Sun is supposed to "Unsleep 2 of your cards" but appears to be sleeping opponent's cards instead  
**Evidence**: Screenshot shows "Successfully played Sun (sleeped Wizard)" - wrong behavior entirely  
**Expected**: Return up to 2 cards from YOUR Sleep Zone to YOUR hand  
**Actual**: Something completely different happened  

**Investigation Needed**:
1. Check if `UnsleepEffect.get_valid_targets()` is returning wrong cards
2. Check if target selection is picking from wrong zone
3. Check if `apply()` method is doing something unexpected
4. Verify AI's target selection for Sun isn't picking opponent's cards

**Files to Check**:
- `backend/src/game_engine/rules/effects/action_effects.py` - `UnsleepEffect` class
- `backend/src/api/routes_actions.py` - How targets are passed to effects
- `backend/src/game_engine/validation/action_validator.py` - Target option generation

---

## Testing Status

### What Works ✅
- Archer shows 1 action button with correct description
- Clicking Archer button opens target selection modal
- Target list shows only opponent's cards (correct scoping)
- Selecting target executes ability
- Stamina damage correctly updates `current_stamina` (e.g., 4/6/2 → 4/6/1)
- Card sleeps when current_stamina reaches 0
- Can repeat action multiple times in same turn
- AI player can see and select activated ability actions

### What Needs Testing ⚠️
- AI player actually executing Archer ability in real game
- Archer ability with multiple uses in one turn
- Edge cases: Archer targeting card that will be sleeped
- Sun effect (currently broken)
- Any other effects that might use direct stat modification

---

## Lessons Learned

### 1. **Always Use Proper Methods, Never Direct Modification**
**Bad**:
```python
target.stamina -= 1  # Modifies base stamina!
if target.stamina <= 0:  # Checks base stamina!
    sleep_card()
```

**Good**:
```python
target.apply_damage(1)  # Modifies current_stamina
if target.is_defeated():  # Checks current_stamina
    sleep_card()
```

### 2. **Name-Based Lookups Are Legacy Code**
- All routes should use IDs (card_id, target_id, etc.)
- Only check `card.name` for game rule exceptions (Knight vs Beary)
- Effect registration should be data-driven via `effect_definitions`

### 3. **Frontend-Backend Contract Must Match**
- Frontend called `/games/{id}/players/{player_id}/activate_ability`
- Backend had `/games/{id}/activate-ability`
- Mismatch caused 404 errors
- Always verify routes match between client and server

### 4. **Test with Real UI, Not Just Unit Tests**
- Unit tests passed for Archer
- But integration revealed:
  - Wrong stamina attribute being modified
  - Missing frontend handler for activate_ability
  - URL mismatch between frontend and backend
- **Takeaway**: E2E testing catches integration bugs unit tests miss

---

## Files Changed This Session

### Backend
- `backend/src/game_engine/validation/action_validator.py` - Fixed Archer to show single 1 CC action
- `backend/src/game_engine/rules/effects/action_effects.py` - Fixed Archer to use apply_damage()
- `backend/src/api/routes_actions.py` - Fixed activate_ability to use IDs not names
- `backend/src/api/schemas.py` - Already had ActivateAbilityRequest (no changes needed)
- `backend/src/game_engine/ai/prompts.py` - Updated Archer description for AI
- `backend/src/game_engine/ai/llm_player.py` - Added activate_ability case

### Frontend
- `frontend/src/types/api.ts` - Added ActivateAbilityRequest interface
- `frontend/src/api/gameService.ts` - Added activateAbility service function
- `frontend/src/hooks/useGame.ts` - Added useActivateAbility hook
- `frontend/src/components/GameBoard.tsx` - Added activate_ability handler and target check

### Data
- No changes to `backend/data/cards.csv` - Archer already had `effect_definitions`

---

## Next Steps (Priority Order)

### Priority 1: Fix Critical Bug 🚨
1. **Investigate and fix Sun effect** - it's completely broken
   - Debug why it's sleeping opponent's cards instead of unsleepping your own
   - Check target validation and effect application
   - Add tests for UnsleepEffect with multiple targets

### Priority 2: Fix AI Decision Making ⚠️
2. **Update AI valid actions to show buffed stats**
   - Modify ValidAction descriptions to use `_get_stat_with_effects()`
   - Ensure AI sees real combat stats, not base stats
   - Add tests for tussle predictions with buffs

### Priority 3: Code Quality Audit 🔍
3. **Search for legacy name-based code**
   - Grep for `card.name ==` (except Knight/Beary exceptions)
   - Grep for `request.card_name` or similar in routes
   - Replace with ID-based lookups

4. **Search for direct stat modification**
   - Grep for `.stamina =`, `.stamina +=`, `.stamina -=`
   - Grep for `.strength =`, `.speed =`
   - Replace with `apply_damage()` or effect modifiers

5. **Audit `get_effects_by_card_name()` usage**
   - Find remaining calls to legacy name-based registry
   - Migrate to data-driven `effect_definitions`

### Priority 4: Complete Phase 4 Migration
6. **Migrate Snuggles to data-driven** (only remaining card)
7. **Remove legacy effect registry** for name-based lookups
8. **Update documentation** with new patterns

### Priority 5: Testing Infrastructure (from Issue #89)
9. **Create `/games/{id}/debug` endpoint** for easy game state inspection
10. **Add comprehensive serialization tests** for all Card fields
11. **Document effect system architecture** with diagrams

---

## Questions for Next Session

### Architecture
1. Should we add validation to prevent direct stat modification? (e.g., make attributes read-only?)
2. Should effect registration be entirely removed in favor of CSV-based system?
3. How do we ensure AI sees buffed stats without duplicating stat calculation logic?

### Testing
4. What's the best way to test activated abilities with AI player?
5. Should we add integration tests that verify frontend-backend contracts?
6. How do we prevent regressions in stat calculation (base vs current vs buffed)?

### Implementation
7. Is there a systematic way to find all name-based lookups in codebase?
8. Should we create a base class method for stat modification to enforce proper usage?
9. What other effects might be using direct modification that we haven't caught?

---

## Related Issues & PRs

- **Issue #89**: Testing infrastructure improvements (still open)
- **Issue #70**: Knight immunity not protecting against Clean (FIXED in previous session)
- **Issue #72**: Knight/Beary swap (FIXED in previous session)
- **Issue #66**: Archer implementation (FIXED this session) ✅

**PR to Create**:
- Title: "Implement Archer activated ability and fix stat modification bugs"
- Includes: Archer implementation, frontend integration, ID-based lookups, AI support
- Fixes: Direct stamina modification, name-based route lookups
- Adds: Complete activated abilities system for future cards

---

## Success Metrics

**Completed** ✅:
- Archer fully playable for human players
- Archer visible and selectable for AI players
- No direct stat modification in Archer code
- No name-based lookups in activated ability routes
- Frontend and backend properly integrated

**Pending** ⏳:
- AI actually using Archer in real games (not tested yet)
- Sun effect fixed and working
- All stat modifications using proper methods
- All name-based code eliminated

---

## Technical Notes

### Activated Ability Flow
1. **Action Discovery**: `ActionValidator._get_valid_activated_abilities()` finds cards with ActivatedEffect
2. **Target Generation**: `effect.get_valid_targets()` provides filtered target list
3. **Frontend Display**: Single action button shown with target requirement
4. **Target Selection**: Modal shows only valid targets (e.g., opponent's cards for Archer)
5. **API Call**: POST to `/games/{id}/activate-ability` with `card_id`, `target_id`, `amount`
6. **Execution**: Route finds card by ID, finds target by ID, calls `effect.apply()`
7. **Damage Application**: `apply_damage()` modifies `current_stamina`, checks `is_defeated()`
8. **Sleep Handling**: If defeated, card moved to Sleep Zone via `game_engine._sleep_card()`

### Key Design Patterns
- **ID-Based Everything**: All routes, all lookups use UUIDs not names
- **Method-Based Modification**: Never modify attributes directly, always use methods
- **Effect Factory Pattern**: CSV → EffectFactory → Effect instances → Registry
- **Single Responsibility**: Each effect class does one thing (ActivatedEffect, PlayEffect, etc.)

---

## Final Notes

This session demonstrated the importance of:
1. **Proper abstraction** - `apply_damage()` vs direct modification
2. **Consistent patterns** - ID-based lookups everywhere
3. **Integration testing** - Unit tests didn't catch the bugs
4. **User feedback** - "Only show 1 CC" led to better UX
5. **Defensive programming** - Check assumptions (Sun bug shows we need this)

**Most Important Takeaway**: Even when implementing new features, always audit for legacy patterns that might have slipped through. The name-based lookup in the activate_ability route was a red flag that more legacy code might exist.
