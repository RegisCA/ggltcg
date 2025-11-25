# Effect System Migration Plan

## Overview
This document outlines the strategy for migrating all GGLTCG cards from hardcoded Python effect classes to the data-driven CSV effect system.

## Current Status (Post-PR #78)

### ✅ Migrated to Data-Driven (2 cards)
- **Ka**: `stat_boost:strength:2`
- **Demideca**: `stat_boost:all:1`

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

### Phase 1: Simple Action Effects (Next PR)
**Goal**: Prove action effect pattern works

**New Generic Effect Types Needed**:
1. `GainCCEffect(amount, restrictions)` - for Rush
2. `UnsleepEffect(count)` - for Wake, Sun
3. `SleepAllEffect()` - for Clean

**Cards to Migrate**:
- Rush: `gain_cc:2:not_first_turn`
- Wake: `unsleep:1`
- Sun: `unsleep:2`
- Clean: `sleep_all`

**Estimated Effort**: 1-2 days
**Risk**: LOW - Simple, well-understood patterns

### Phase 2: Cost Modification (Future)
**Goal**: Demonstrate cost modification patterns

**New Generic Effect Types Needed**:
1. `TussleCostEffect(amount, scope)` - for Wizard
2. `CardCostReductionEffect(per_condition)` - for Dream

**Cards to Migrate**:
- Wizard: `tussle_cost:1:scope:controller`

**Estimated Effort**: 2-3 days
**Risk**: MEDIUM - Requires cost system integration

### Phase 3: Triggered Effects (Future)
**Goal**: Support event-based effects

**New Generic Effect Types Needed**:
1. `OnSleepEffect(action)` - for Umbruh, Snuggles

**Cards to Migrate**:
- Umbruh: `on_sleep:gain_cc:1`

**Estimated Effort**: 3-4 days
**Risk**: MEDIUM - Requires event system

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

- **Phase 1 Complete**: 4 more cards migrated (6 total / 18 = 33%)
- **Phase 2 Complete**: 1 more card migrated (7 total / 18 = 39%)
- **Phase 3 Complete**: 1 more card migrated (8 total / 18 = 44%)
- **Final State**: 8 data-driven, 10 custom (reasonable split)

## Benefits vs. Complexity

**High Value Migrations** (do these):
- Simple action effects (Rush, Wake, Sun, Clean)
- Common patterns that will be reused for future cards
- Effects that are currently error-prone

**Low Value Migrations** (skip these):
- One-off complex effects (Copy, Twist)
- Cards marked as broken (Archer, Snuggles)
- Well-functioning complex interactions (Knight, Beary)

## Next Steps

1. ✅ Review this migration plan
2. 🔄 Implement Phase 1 generic effects
3. 🔄 Migrate Rush, Wake, Sun, Clean
4. 🔄 Test and validate Phase 1
5. 📋 Create PR for Phase 1
6. 📋 Decide on Phase 2 based on learnings
