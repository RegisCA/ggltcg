# Effect System Migration Plan

## Overview
This document outlines the strategy for migrating all GGLTCG cards from hardcoded Python effect classes to the data-driven CSV effect system.

## Current Status (Post-Phase 3)

### ✅ Migrated to Data-Driven (10 cards - 56%)
- **Ka**: `stat_boost:strength:2`
- **Demideca**: `stat_boost:all:1`
- **Rush**: `gain_cc:2:not_first_turn`
- **Wake**: `unsleep:1`
- **Sun**: `unsleep:2`
- **Clean**: `sleep_all`
- **Wizard**: `set_tussle_cost:1`
- **Dream**: `reduce_cost_by_sleeping`
- **Umbruh**: `gain_cc_when_sleeped:1`
- **Raggy**: `set_self_tussle_cost:0:not_turn_1`

### 📋 Remaining Cards (8 cards - 44%)
- Knight (2 custom effects - works well)
- Beary (2 custom effects - works well)
- Archer (2 custom effects - marked NOT WORKING)
- Copy (1 custom effect - too complex for generic system)
- Twist (1 custom effect - state manipulation)
- Toynado (1 custom effect - simple but one-off)
- Snuggles (1 custom effect - marked NOT WORKING)
- Ballaber (1 custom effect - alternative cost mechanic)

### 📋 Cards Analyzed (18 total cards)

## Migration Categories

### Category 1: Ready for Generic Effects (High Priority)
These cards can be migrated using existing or simple new generic effect types.

#### 1.1 Cost Modification Effects
**Cards**: Wizard, Raggy, Dream, Ballaber

**Wizard** - "Your cards' tussles cost 1"
- **Effect Type**: `tussle_cost:1` (set tussle cost to fixed value)
- **Complexity**: Simple
- **Priority**: HIGH - Common cost modification pattern

**Raggy** - "This card's tussles cost 0. Cannot tussle on turn 1"
- **Effect Type**: `self_tussle_cost:0` + `cannot_tussle_turn:1`
- **Complexity**: Medium (needs restriction support)
- **Priority**: MEDIUM

**Dream** - "Costs 1 less per sleeping card"
- **Effect Type**: `cost_reduction:per_sleeping:1`
- **Complexity**: Medium (needs counter logic)
- **Priority**: MEDIUM

**Ballaber** - "Sleep 1 card to play for free"
- **Effect Type**: `alternative_cost:sleep:1`
- **Complexity**: Medium (needs alternative payment UI)
- **Priority**: LOW - Requires frontend changes

### Category 2: Complex Protection/Interaction (Medium Priority)
These cards have inter-card dependencies and protection mechanics.

**Knight** - "Opponent's effects don't affect. Auto-win tussles on your turn"
- **Current**: 2 effects (KnightProtectionEffect, KnightWinConditionEffect)
- **Effect Type**: `protection:opponent_effects` + `auto_win_tussle:on_turn:except:Beary`
- **Complexity**: HIGH - Complex protection + win condition
- **Priority**: LOW - Works well with current system

**Beary** - "Knight effects don't affect. Cancel opponent tussles"
- **Current**: 2 effects (BearyProtectionEffect, BearyTussleCancelEffect)
- **Effect Type**: `protection:from_card:Knight` + `cancel_tussle:opponent`
- **Complexity**: HIGH - Named protection + reactive trigger
- **Priority**: LOW - Works well with current system

**Archer** - "Can't start tussles. Activated: spend CC to damage"
- **Current**: ArcherRestrictionEffect + ArcherActivatedAbility
- **Effect Type**: `cannot_tussle` + `activated:damage:cost_per_damage:1`
- **Complexity**: HIGH - Restriction + activated ability
- **Priority**: LOW - Marked "NOT WORKING" in CSV

### Category 3: Special Mechanics (Low Priority)
These cards have unique mechanics that may benefit from staying as custom effects.

**Copy** - "Acts as exact copy of card in play"
- **Current**: CopyEffect (complex cloning logic)
- **Effect Type**: Custom - Too complex for generic system
- **Complexity**: VERY HIGH
- **Priority**: NONE - Keep as custom effect
- **Reason**: Dynamic card state copying requires runtime logic

**Twist** - "Take control of opponent's card"
- **Current**: TwistEffect (ownership transfer)
- **Effect Type**: Custom - State manipulation
- **Complexity**: VERY HIGH
- **Priority**: NONE - Keep as custom effect
- **Reason**: Controller reassignment is state-based

**Toynado** - "Return all in-play cards to owner's hands"
- **Current**: ToynadoEffect
- **Effect Type**: `return_all_to_hand`
- **Complexity**: MEDIUM
- **Priority**: LOW - Simple but one-off effect

### Category 4: Simple Action Effects (High Priority)
These are straightforward action cards that could use generic patterns.

**Clean** - "Sleep all in-play cards"
- **Current**: CleanEffect
- **Effect Type**: `sleep_all_in_play`
- **Complexity**: LOW
- **Priority**: HIGH - Simple batch operation

**Wake** - "Unsleep 1 card"
- **Current**: WakeEffect (requires target selection)
- **Effect Type**: `unsleep:count:1`
- **Complexity**: LOW
- **Priority**: HIGH - Common pattern

**Sun** - "Unsleep 2 cards"
- **Current**: SunEffect (requires target selection)
- **Effect Type**: `unsleep:count:2`
- **Complexity**: LOW
- **Priority**: HIGH - Same as Wake

**Rush** - "Gain 2 CC. Not on first turn"
- **Current**: RushEffect
- **Effect Type**: `gain_cc:2:not_first_turn`
- **Complexity**: LOW
- **Priority**: HIGH - Simple with restriction

### Category 5: Triggered Effects (Medium Priority)
These cards trigger on specific game events.

**Umbruh** - "When sleeped, gain 1 CC"
- **Current**: UmbruhEffect
- **Effect Type**: `on_sleep:gain_cc:1`
- **Complexity**: MEDIUM
- **Priority**: MEDIUM - Common trigger pattern

**Snuggles** - "When sleeped, sleep a card in play"
- **Current**: SnugglesWhenSleepedEffect
- **Effect Type**: `on_sleep:sleep_target:count:1`
- **Complexity**: MEDIUM
- **Priority**: LOW - Marked "NOT WORKING" in CSV

## Recommended Migration Phases

### ✅ Phase 1: Simple Action Effects (COMPLETED)
**Goal**: Prove action effect pattern works

**Implemented Generic Effect Types**:
1. `GainCCEffect(amount, not_first_turn)` - for Rush
2. `UnsleepEffect(count)` - for Wake, Sun
3. `SleepAllEffect()` - for Clean

**Migrated Cards**:
- Rush: `gain_cc:2:not_first_turn`
- Wake: `unsleep:1`
- Sun: `unsleep:2`
- Clean: `sleep_all`

**Status**: ✅ COMPLETED (PR #79)
**Tests**: 7 tests passing

### ✅ Phase 2: Cost Modification (COMPLETED)
**Goal**: Demonstrate cost modification patterns

**Implemented Generic Effect Types**:
1. `SetTussleCostEffect(cost)` - for Wizard
2. `ReduceCostBySleepingEffect()` - for Dream

**Migrated Cards**:
- Wizard: `set_tussle_cost:1`
- Dream: `reduce_cost_by_sleeping`

**Status**: ✅ COMPLETED (PR #80)
**Tests**: 6 tests passing

### ✅ Phase 3: Triggered Effects (COMPLETED)
**Goal**: Support event-based effects and self-cost modifications

**Implemented Generic Effect Types**:
1. `GainCCWhenSleepedEffect(amount)` - triggered effect for Umbruh
2. `SetSelfTussleCostEffect(cost, not_turn_1)` - self tussle cost with restriction for Raggy

**Migrated Cards**:
- Umbruh: `gain_cc_when_sleeped:1`
- Raggy: `set_self_tussle_cost:0:not_turn_1`

**Status**: ✅ COMPLETED (Current PR)
**Tests**: 5 tests passing
**Architectural Fix**: Updated SleepAllEffect to use game_engine reference to properly trigger when-sleeped effects

**Key Learning**: Effects that trigger other effects (like Clean sleeping Umbruh) need access to GameEngine, not just GameState, to maintain proper architectural boundaries.

### Phase 4+: Complex/Custom Effects (Optional)
**Decision**: Keep as custom Python classes

**Cards to Keep Custom**:
- Knight (complex protection + win condition)
- Beary (reactive + named protection)
- Copy (runtime state cloning)
- Twist (state manipulation)
- Archer (broken - needs redesign)
- Snuggles (broken - needs redesign)

## Generic Effect Types to Implement

### Priority 1 (Phase 1)
```python
class GainCCEffect(PlayEffect):
    """Generic CC gain effect"""
    def __init__(self, source_card, amount, restrictions=None)
    
class UnsleepEffect(PlayEffect):
    """Generic unsleep N cards effect"""
    def __init__(self, source_card, count)
    
class SleepAllEffect(PlayEffect):
    """Sleep all cards in play"""
    def __init__(self, source_card)
```

### Priority 2 (Phase 2)
```python
class TussleCostEffect(CostModificationEffect):
    """Modify tussle cost"""
    def __init__(self, source_card, cost, scope)
    
class CardCostReductionEffect(CostModificationEffect):
    """Reduce card cost based on condition"""
    def __init__(self, source_card, reduction_type, amount)
```

### Priority 3 (Phase 3)
```python
class OnSleepEffect(TriggeredEffect):
    """Trigger effect when card is sleeped"""
    def __init__(self, source_card, action, params)
```

## Success Metrics

- ✅ **Phase 1 Complete**: 4 cards migrated (6 total / 18 = 33%)
- ✅ **Phase 2 Complete**: 2 cards migrated (8 total / 18 = 44%)
- ✅ **Phase 3 Complete**: 2 cards migrated (10 total / 18 = 56%)
- **Final State**: 10 data-driven, 8 custom (excellent split!)

**Achievement**: More than half of all cards (56%) now use the data-driven system!

## Benefits vs. Complexity

**High Value Migrations** (do these):
- Simple action effects (Rush, Wake, Sun, Clean)
- Common patterns that will be reused for future cards
- Effects that are currently error-prone

**Low Value Migrations** (skip these):
- One-off complex effects (Copy, Twist)
- Cards marked as broken (Archer, Snuggles)
- Well-functioning complex interactions (Knight, Beary)

## Known Issues

### Issue #84: Review LLM Prompt Guidance

**Status**: Open  
**Priority**: HIGH  
**Link**: https://github.com/RegisCA/ggltcg/issues/84

**Problem**: AI prompt guidance in `prompts.py` contains inaccurate card descriptions that cause the LLM to make invalid plays.

**Examples**:
- **Copy**: Prompt says "Create a copy of target Toy" but doesn't clarify it must be YOUR Toy, not opponent's
  - AI tried to copy opponent's Umbruh which is not allowed
  - AI used card name/stats as target_id instead of UUID
- **Wizard**: Description may not accurately reflect cost modification mechanics

**Impact**:
- LLM makes illegal moves that fail validation
- Poor user experience when playing against AI
- Increased hallucination rate

**Action Items**:
1. Audit all card descriptions in `prompts.py` against actual card effects
2. Add ownership constraints (e.g., "your Toy" vs "any Toy")
3. Clarify targeting rules more explicitly
4. Test AI behavior with corrected prompts
5. Consider adding validation examples to reduce hallucinations

### Issue #85: GameEngine/GameState Separation Violations

**Status**: Open  
**Priority**: MEDIUM  
**Link**: https://github.com/RegisCA/ggltcg/issues/85

**Problem**: Code directly calls `game_state` methods that perform game logic instead of delegating to `game_engine`. This bypasses effect triggering and violates architectural separation of concerns.

**Architecture**:
- **GameState**: Pure data model - holds state, provides data access methods
- **GameEngine**: Logic orchestrator - handles all game rules, cost calculations, and effect triggering

## Architectural Analysis: GameState Methods

The following methods currently exist on `GameState`. This analysis determines which should move to `GameEngine`:

### ✅ Appropriate for GameState (Pure Data Access)
These methods only read or query state without triggering game logic:

- `get_active_player()` - Simple lookup
- `get_opponent()` - Simple lookup
- `get_opponent_of_active()` - Simple lookup
- `is_first_turn()` - State check
- `is_active_player()` - State check
- `log_event()` - Event recording (no logic)
- `add_play_by_play()` - Event recording (no logic)
- `get_all_cards_in_play()` - Data access
- `get_cards_in_play()` - Data access
- `get_card_controller()` - Data access
- `get_card_owner()` - Data access
- `find_card_by_name()` - Data access
- `find_card_by_id()` - Data access
- `to_dict()` / `from_dict()` - Serialization

### ⚠️ SHOULD MOVE to GameEngine (Triggers Effects or Contains Logic)

#### 1. `sleep_card(card, was_in_play)` - **HIGH PRIORITY**
**Current Issues**:
- **action_executor.py:256** - Ballaber alternative cost payment
- **game_engine.py:241** - Duplicate alternative cost handling
- **triggered_effects.py:109** - Snuggles' when-sleeped effect
- **action_effects.py:505** - Archer activated ability (damage → sleep)

**Impact**: 
- When Ballaber sleeps a card from play (like Umbruh), triggered effects don't fire
- When Snuggles sleeps a card, that card's when-sleeped effects don't fire
- When Archer damages a card to 0 stamina, sleep effects don't fire

**Correct Behavior**:
- Sleeping a card **from Play zone** → triggers when-sleeped effects
- Sleeping a card **from Hand zone** → NO trigger (not "was_in_play")
- This distinction is already tracked with `was_in_play` parameter

**Fix**: All code should call `game_engine._sleep_card(card, owner, was_in_play)` which:
1. Moves card to sleep zone via `player.sleep_card(card)`
2. If `was_in_play=True`, triggers when-sleeped effects

#### 2. `unsleep_card(card, player)` - **LOW PRIORITY**
**Current Behavior**: Directly calls `player.unsleep_card(card)`

**Analysis**: 
- Currently no "when unsleeped" effects exist in the game
- If we add such effects in future, this would need to move to GameEngine
- For now, this is just a data operation (move card from sleep zone to hand)

**Decision**: Keep in GameState for now, but monitor if unsleep effects are added

#### 3. `return_card_to_hand(card, owner)` - **MEDIUM PRIORITY**
**Current Users**: Toynado effect

**Current Behavior**:
- Resets card modifications
- Changes zone to HAND
- Resets controller to owner
- Adds to owner's hand

**Analysis**: This contains game logic (resetting modifications, resetting controller). Should be in GameEngine.

**Potential Issues**:
- If we add "when returned to hand" effects, they won't trigger
- State modifications (reset) mixed with data changes (zone movement)

**Recommendation**: Move to GameEngine as `_return_card_to_hand()`

#### 4. `change_control(card, new_controller)` - **MEDIUM PRIORITY**
**Current Users**: Twist effect

**Current Behavior**:
- Removes from old controller's in_play
- Updates card.controller field
- Adds to new controller's in_play
- Logs event

**Analysis**: Contains logic about control changes. Should be in GameEngine.

**Potential Issues**:
- If we add "when control changes" effects, they won't trigger
- If continuous effects should update when control changes, they might not

**Recommendation**: Move to GameEngine as `_change_control()`

#### 5. `play_card_from_hand(card, player)` - **MEDIUM PRIORITY**
**Current Users**: Beary's tussle cancel effect

**Current Behavior**:
- Removes from hand
- Sets zone to IN_PLAY
- Adds to in_play

**Analysis**: This is game logic (playing a card). Should use normal play_card flow through GameEngine.

**Issue**: Beary's effect bypasses normal "when played" triggers and CC cost payment

**Recommendation**: Refactor Beary effect to use `game_engine.play_card()` or a special internal method that handles free plays

#### 6. `is_protected_from_effect(card, effect)` - **COMPLEX**
**Current Behavior**: Checks card's protection effects against incoming effect

**Analysis**: This is effect resolution logic, not pure data access

**Issue**: Currently okay, but ties GameState to effect system imports

**Recommendation**: Consider moving to GameEngine or a separate EffectResolver class

#### 7. `check_victory()` - **ALREADY IN GAMEENGINE**
**Note**: GameEngine also has `check_victory()` method that calls this. Should probably consolidate.

### 🔧 Specific Fixes Needed

#### Fix #1: Ballaber Alternative Cost (2 locations)
**Files**: `action_executor.py:256`, `game_engine.py:241`

**Current**:
```python
self.game_state.sleep_card(card_to_sleep, was_in_play=was_in_play)
```

**Should be**:
```python
owner = self.game_state.get_card_owner(card_to_sleep)
self.engine._sleep_card(card_to_sleep, owner, was_in_play=was_in_play)
```

**Test Case**: Play Ballaber, sleep Umbruh from play → Umbruh's owner should gain 1 CC

#### Fix #2: Snuggles When-Sleeped Effect
**File**: `triggered_effects.py:109`

**Current**:
```python
game_state.sleep_card(target, was_in_play=True)
```

**Should be**:
```python
game_engine = kwargs.get("game_engine")
owner = game_state.get_card_owner(target)
game_engine._sleep_card(target, owner, was_in_play=True)
```

**Test Case**: Sleep Snuggles from play, target Umbruh in play → Umbruh's owner gains 1 CC

#### Fix #3: Archer Activated Ability
**File**: `action_effects.py:505`

**Current**:
```python
if target.stamina <= 0:
    game_state.sleep_card(target, was_in_play=True)
```

**Should be**:
```python
if target.stamina <= 0:
    game_engine = kwargs.get("game_engine")
    owner = game_state.get_card_owner(target)
    game_engine._sleep_card(target, owner, was_in_play=True)
```

**Test Case**: Archer damages Umbruh to 0 stamina → Umbruh's owner gains 1 CC

#### Fix #4: Remove Duplicate Alternative Cost Logic
**File**: `game_engine.py:241`

**Issue**: Alternative cost is handled in both `action_executor.py` and `game_engine.py`

**Recommendation**: Consolidate into single location (probably action_executor since it validates actions)

### 📋 "Punch" Effect - Mystery Solved

**Finding**: There is NO card named "Punch" in the game!

**What was found**: `action_effects.py:505` contains an UNNAMED effect class for Archer's activated ability that deals damage. The grep search flagged line 505 which has damage logic, but this is actually `ArcherActivatedAbility`, not a "Punch" effect.

**Conclusion**: "Punch" was a false positive from the grep search. The actual issue is Archer's damage-to-sleep logic at line 505.

## Next Steps

1. ✅ Review this migration plan
2. ✅ Implement Phase 1 generic effects
3. ✅ Migrate Rush, Wake, Sun, Clean
4. ✅ Test and validate Phase 1
5. ✅ Create PR for Phase 1 (PR #79)
6. ✅ Implement Phase 2 cost modifications
7. ✅ Create PR for Phase 2 (PR #80)
8. ✅ Implement Phase 3 triggered effects
9. ✅ Create PR for Phase 3 (PR #83)
10. 📋 Address Issue #84 (AI prompt accuracy)
11. 📋 Address Issue #85 (GameEngine/GameState separation):
    - Fix Ballaber + Umbruh interaction (HIGH PRIORITY)
    - Fix Snuggles cascading effects
    - Fix Archer damage-to-sleep triggering
    - Consider moving `return_card_to_hand()` and `change_control()` to GameEngine
12. 📋 Decide whether to implement Phase 4 or keep remaining cards as custom effects
