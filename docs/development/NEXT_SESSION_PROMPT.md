# Next Session: Core Game Mechanics & Effect System Completion

## Session Goal
Complete the core game mechanics implementation, finish effect system migration, and improve testing infrastructure to prevent bugs like issue #77.

## Critical Context

### What Just Happened (Previous Session)
We fixed issue #77 (Copy effect not working) which revealed **three interconnected bugs**:

1. **Deck Creation Bug**: `_create_deck()` wasn't copying `effect_definitions` from card templates
   - Location: `backend/src/api/game_service.py` line 683
   - Impact: All cards in new games had empty effect_definitions
   - Fix: Added `effect_definitions=template.effect_definitions` to Card constructor

2. **Serialization Bug**: `serialize_card()` wasn't saving `effect_definitions` to database
   - Location: `backend/src/api/serialization.py` lines 30-38
   - Impact: Even if cards had effect_definitions, they were lost on save
   - Fix: Always include `effect_definitions` in serialized data

3. **Dict Mutation Bug**: `serialize_card()` was mutating the original `modifications` dict
   - Location: `backend/src/api/serialization.py` line 35
   - Impact: Setting `_is_transformed` flag modified the card object
   - Fix: Create copy of modifications dict before mutating

**Result**: Copy effects now work correctly. Example: Umbruh 6/6/6 (4 base + 1 Demideca + 1 Copy) ✓

### Architecture Overview

**Effect System Data Flow**:
```
cards.csv
  └─> effect_definitions (string)
       └─> CardLoader.load_cards()
            └─> Card templates with effect_definitions
                 └─> _create_deck() creates player deck
                      └─> EffectFactory.parse_effects()
                           └─> _copied_effects (runtime list)
                                └─> EffectRegistry.get_effects()
                                     └─> GameEngine.get_card_stat()
```

**Persistence Flow**:
```
Card in memory
  └─> serialize_card()
       └─> JSONB in PostgreSQL
            └─> deserialize_card()
                 └─> Card in memory
                      └─> EffectFactory.parse_effects() (re-creates effects)
```

**Key Insight**: `effect_definitions` (string from CSV) is the source of truth. `_copied_effects` (list of effect objects) is ephemeral and rebuilt on load.

### Current State

**What Works**:
- ✅ Copy effect transforms in-place and creates `_copied_effects`
- ✅ Serialization preserves `effect_definitions` and `_is_transformed` flag
- ✅ Deserialization rebuilds effects correctly from `effect_definitions`
- ✅ Stats calculated correctly with all continuous effects
- ✅ **PR #88 MERGED & DEPLOYED TO PRODUCTION** (November 25, 2025)

**What Needs Work** (see issue #89):
- ❌ No easy way to inspect game state in database
- ❌ Effect system still has legacy name-based registry (Phase 4 incomplete)
- ❌ Serialization not fully tested (only Copy case tested)
- ❌ No architecture documentation for effect system
- ❌ Error messages don't help when `effect_definitions` is missing

## Your Mission

### Priority 1: Verify Production Deployment ✅ DONE

- ✅ PR #88 merged to main (November 25, 2025)
- ✅ Production deployment complete (Render backend + Vercel frontend)
- ✅ Issue #77 can be closed
- **Next**: Monitor production for any Copy effect issues in live games

### Priority 2: Testing Infrastructure (Issue #89)
**Short-term wins**:
1. Create `/games/{id}/debug` endpoint to inspect full game state
2. Add comprehensive serialization tests for all Card fields
3. Document effect system architecture with diagrams

**Why**: These would have caught the bugs much earlier and saved hours of debugging.

### Priority 3: Complete Effect Migration (Phase 4)
**Current Problem**: Two ways to get effects:
- Legacy: `EffectRegistry.get_instance().get_effects_by_card_name(card.name)`
- Modern: `EffectFactory.parse_effects(card.effect_definitions)`

**Goal**: Retire the legacy name-based registry entirely.

**Steps**:
1. Audit codebase for calls to `get_effects_by_card_name()`
2. Verify all cards use `effect_definitions` in CSV
3. Remove name-based effect registration
4. Delete legacy registry code

**Files to Check**:
- `backend/src/game_engine/rules/effects/__init__.py`
- `backend/src/game_engine/game_engine.py`
- Any effect classes still using name-based registration

### Priority 4: Core Game Mechanics
Continue implementing remaining effect cards and game features.

**Remaining Effect Types** (from CSV):
- Review `backend/data/cards.csv` for cards with complex `effect_definitions`
- Ensure EffectFactory can parse all effect types
- Add tests for each effect type

## Key Files You'll Need

### Effect System Core
- `backend/src/game_engine/rules/effects/__init__.py` - EffectFactory, EffectRegistry
- `backend/src/game_engine/rules/effects/action_effects.py` - CopyEffect (reference implementation)
- `backend/src/game_engine/rules/effects/continuous_effects.py` - Stat buff effects

### Serialization & Persistence
- `backend/src/api/serialization.py` - serialize_card(), deserialize_card()
- `backend/src/api/game_service.py` - _create_deck(), create_game()
- `backend/src/api/database.py` - Database models

### Testing
- `backend/tests/test_simple_serialization.py` - Current serialization test (Copy only)
- `backend/tests/test_effects.py` - Effect tests
- `backend/tests/test_game_engine.py` - Game logic tests

### Data
- `backend/data/cards.csv` - Card definitions with effect_definitions column

## Common Pitfalls to Avoid

### 1. Serialization Bugs
**Bad**:
```python
# Mutates original!
card.modifications['new_key'] = value
serialized = {"modifications": card.modifications}
```

**Good**:
```python
# Create copy first
modifications = card.modifications.copy()
modifications['new_key'] = value
serialized = {"modifications": modifications}
```

### 2. Missing effect_definitions
**Bad**:
```python
# Might not copy effect_definitions!
card = Card(name=template.name, strength=template.strength)
```

**Good**:
```python
# Explicitly copy all fields
card = Card(
    name=template.name,
    effect_definitions=template.effect_definitions,
    strength=template.strength
)
```

### 3. Testing Only Unit Level
**Bad**:
```python
# Unit test passes but integration fails
def test_copy_effect():
    effect = CopyEffect(...)
    effect.apply(...)
    assert card._copied_effects  # ✓ but doesn't test serialization!
```

**Good**:
```python
# Test full cycle
def test_copy_effect_survives_save():
    game = create_game()
    execute_action()  # Apply Copy
    state = serialize_game_state(game)
    loaded = deserialize_game_state(state)
    assert loaded.get_card_stat()  # ✓ tests everything
```

## Questions to Answer

### Architecture
1. Is `effect_definitions` (CSV string) truly the single source of truth?
2. Can we remove the name-based effect registry entirely?
3. Should `_copied_effects` be serialized or always rebuilt from `effect_definitions`?

### Testing
4. What's the minimum set of fields every Card must have?
5. How do we validate that serialization doesn't drop fields?
6. Should we have integration tests for the full game flow?

### Implementation
7. Are there other places besides `_create_deck()` that create Card instances?
8. Do all card templates from CSV have `effect_definitions`?
9. Are there effects that can't be expressed in the current `effect_definitions` format?

## Success Metrics

After this session, we should have:

- ✅ PR #88 merged and deployed to production (DONE - November 25, 2025)
- ⏳ `/games/{id}/debug` endpoint working
- ⏳ Comprehensive serialization test suite
- ⏳ Effect system architecture documented
- ⏳ Phase 4 complete (legacy registry removed) OR clear plan to complete
- ⏳ No more "game state is hard to inspect" issues

## Related Issues & PRs

- **Issue #77**: Copy effect not working (CLOSED - fixed by PR #88)
- **PR #88**: Fix for Copy effect bugs (MERGED - November 25, 2025, deployed to production)
- **Issue #89**: Testing infrastructure improvements (OPEN - next priority)
- **Issue #82**: Testing difficulties (mentioned by user as related)

## Debug Tools Available

If you need to inspect game state during this session:

- `backend/check_game_state.py` - Inspect specific game from database
- `backend/check_copy_effects.py` - Check Copy effect state
- Add debug logging: `logger.debug(f"Card {card.name} effects: {card.effect_definitions}")`

## Final Notes

The Copy effect bug hunt taught us that **multiple small bugs can compound into one mysterious failure**. The effect system is complex with data flowing through many layers (CSV → templates → deck cards → serialization → database → deserialization → effects).

**Be paranoid about serialization**: Always assume data might be lost unless proven otherwise with tests.

**Trust the architecture docs**: Once you create them, they'll prevent future confusion about which system is authoritative.

**Build debugging tools early**: The time spent creating inspection tools pays off quickly.

Good luck! 🚀
