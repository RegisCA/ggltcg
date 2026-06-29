# Effect System Architecture

## Overview

The GGLTCG effect system is responsible for managing card abilities that modify
game state, apply stat buffs, and trigger special actions. This document
explains how effects flow through the system from initial data definition to
runtime execution.

**Last Updated**: June 29, 2026
**Status**: Data-driven system complete for all 30 current cards — no
name-based registry remains (removed PR #347)

---

## Table of Contents

1. Data Flow Overview
2. System Components
3. Effect Types
4. Lifecycle
5. Effect Resolution Path
6. Serialization
7. Common Pitfalls
8. Debug Tools

---

## Data Flow Overview

```text
┌─────────────┐
│ cards.csv   │  ← SOURCE OF TRUTH
│             │    "stat_boost:strength:2"
└──────┬──────┘
       │
       │ CardLoader.load_cards()
       ▼
┌─────────────────────────┐
│ Card Templates          │
│ (effect_definitions str)│
└──────┬──────────────────┘
       │
       │ GameService._create_deck()
       ▼
┌─────────────────────────┐
│ Player Deck Cards       │
│ (effect_definitions str)│
└──────┬──────────────────┘
       │
       │ When needed: EffectRegistry.get_effects()
       ▼
┌─────────────────────────┐
│ EffectFactory           │
│ .parse_effects()        │
└──────┬──────────────────┘
       │
       │ Creates runtime effect objects
       ▼
┌─────────────────────────┐
│ Effect Objects          │
│ (StatBoostEffect, etc.) │
│ (_copied_effects list)  │
└──────┬──────────────────┘
       │
       │ GameEngine.get_card_stat()
       ▼
┌─────────────────────────┐
│ Calculated Stats        │
│ (with all effects)      │
└─────────────────────────┘
```text

### Key Principle

**`effect_definitions` (string) is the single source of truth.**

- Stored in CSV
- Copied to Card instances
- Persisted to database
- Runtime effect objects (`_copied_effects`) are **ephemeral** and rebuilt on
  demand

---

## System Components

### 1. Card Data (cards.csv)

Located: `backend/data/cards.csv`

Cards define their effects in the `effects` column using a domain-specific
language:

```csv
name,effects
Ka,stat_boost:strength:2
Demideca,stat_boost:all:1
Wake,fix:1
Wizard,set_tussle_cost:1
```text
**Format**: `effect_type:param1:param2`
**Multiple effects**: Use semicolon separator: `effect1:p1;effect2:p1:p2`

### 2. CardLoader

Located: `backend/src/game_engine/data/card_loader.py`

Responsibilities:

- Parse CSV file
- Create Card template objects
- Copy `effects` column to `effect_definitions` attribute

```python
template = Card(
    name=row['name'],
    effect_definitions=row['effects'],  # String from CSV
    # ... other fields
)
```text
### 3. EffectFactory

Located: `backend/src/game_engine/rules/effects/effect_registry.py`

Parses effect definition strings into runtime effect objects.

```python
# Parse single effect
"stat_boost:strength:2" → StatBoostEffect(card, "strength", 2)

# Parse multiple effects
"stat_boost:strength:2;fix:1" → [
    StatBoostEffect(card, "strength", 2),
    FixEffect(card, 1)
]
```text
**Supported Effect Types**: ~25 types, e.g. `stat_boost:stat_name:amount`,
`gain_charge:amount[:not_first_turn]`, `fix:count`, `break_all`,
`take_control`, `copy_card`. The full, current list with CSV syntax for
every type (including ones added after this doc's last full pass —
`auto_win_tussle_on_own_turn`, `cannot_tussle`, `direct_attack`,
`remove_stamina_ability`, `damage_all_opponent_cards`, etc.) lives in
[`ADDING_NEW_CARDS.md`](ADDING_NEW_CARDS.md) — kept there as the single
source of truth rather than duplicated here, where a prior copy of this
list had already drifted out of sync.

### 4. EffectRegistry

Located: `backend/src/game_engine/rules/effects/effect_registry.py`

Central dispatcher for getting a card's effects:

```python
def get_effects(card: Card) -> List[BaseEffect]:
    # Pre-parsed copied effects (Copy card transformation) take precedence
    if hasattr(card, '_copied_effects') and card._copied_effects:
        return card._copied_effects

    # Every other card: parse effect_definitions from cards.csv
    return EffectFactory.parse_effects(card.effect_definitions, card)
```text

The legacy name-based registry fallback (`_effect_map`, `register_effect()`)
was removed in PR #347 — `EffectFactory.parse_effects()` is the only
effect-resolution path now.

### 5. GameEngine

Located: `backend/src/game_engine/game_engine.py`

Uses effects to calculate modified stats:

```python
def get_card_stat(self, card: Card, stat_name: str) -> int:
    """Get card stat with all continuous effects applied."""
    base_value = getattr(card, stat_name)

    # Get all continuous effects from all cards
    for c in all_cards_in_play:
        effects = EffectRegistry.get_effects(c)
        for effect in effects:
            if isinstance(effect, ContinuousEffect):
                base_value = effect.modify_stat(card, stat_name, base_value)

    return base_value + card.modifications.get(stat_name, 0)
```text
---

## Effect Types

### Continuous Effects

Apply ongoing modifications while card is in play.

**Base Class**: `ContinuousEffect`
**Location**: `backend/src/game_engine/rules/effects/continuous_effects.py`

Examples:
- **StatBoostEffect**: Ka buffs adjacent cards (+2 strength)
- **SetTussleCostEffect**: Wizard makes all tussles cost 1
- **GainChargeWhenBrokenEffect**: Umbruh gains 1 Charge when broken

### Action Effects

Trigger once when action card is played.

**Base Class**: `ActionEffect`
**Location**: `backend/src/game_engine/rules/effects/action_effects.py`

Examples:
- **FixEffect**: Wake/Sun returns cards to hand
- **BreakAllEffect**: Clean breaks all cards
- **CopyEffect**: Copy transforms into another card

---

## Lifecycle

### 1. Game Creation

```python
# GameService._create_deck()
template = all_cards['Ka']  # From CardLoader

# BUG FIX (Issue #77 Bug #1): Must copy effect_definitions!
card = Card(
    name=template.name,
    effect_definitions=template.effect_definitions,  # ← CRITICAL
    strength=template.strength,
    # ... other fields
)
```text
**Common Mistake**: Forgetting to copy `effect_definitions` from template.

### 2. Runtime Effect Parsing

Effects are parsed **on demand** when stats are calculated:

```python
# GameEngine.get_card_stat()
effects = EffectRegistry.get_effects(ka_card)
# → EffectFactory.parse_effects("stat_boost:strength:2", ka_card)
# → [StatBoostEffect(ka_card, "strength", 2)]
```text
### 3. Copy Card Transformation

Special case: Copy card creates `_copied_effects` list:

```python
# CopyEffect.apply()
copy_card._is_transformed = True
copy_card._copied_effects = EffectFactory.parse_effects(
    target.effect_definitions,  # Copy target's effect string
    copy_card
)
```text
**Why `_copied_effects`?**
- Allows Copy card to have different effects than its original definition
- Takes priority in `EffectRegistry.get_effects()`
- Rebuilt on deserialization from `effect_definitions`

### 4. Stat Calculation

```python
# Example: Ka (9 base strength + 2 buff) adjacent to Copy of Ka (+2 buff)
engine.get_card_stat(ka_card, 'strength')
# → 9 (base) + 2 (Ka's effect) + 2 (Copy's effect) = 13
```text
---

## Effect Resolution Path

There is a single effect system: every one of the 30 production cards,
including mechanically complex ones like Knight, Copy, and Twist, is
parsed from its `effect_definitions` CSV string by `EffectFactory` — there
is no name-based registration and no per-card effect class.

```python
# Card data includes effect_definitions
card.effect_definitions = "stat_boost:strength:2"

# Effects parsed at runtime
effects = EffectFactory.parse_effects(card.effect_definitions, card)
```text
**Advantages**:
- Single source of truth (CSV)
- Easy to add new cards
- No code changes needed for new effects
- Survives serialization

A name-based registry (`EffectRegistry.register_effect(name, EffectClass)`,
looked up as a fallback when a card had no `effect_definitions`) existed
historically for cards whose mechanics predated the generic effect types
needed to express them. As the generic effect types grew to ~25 (see
[`ADDING_NEW_CARDS.md`](ADDING_NEW_CARDS.md)), every card was migrated onto
CSV-driven definitions; the registry's fallback branch was confirmed dead
(never reached, per `tests/test_effects.py`) and removed in PR #347.

---

## Serialization

Effects are **not** directly serialized. Instead, we persist the
`effect_definitions` string and rebuild effects on load.

### Save Flow

```python
# serialize_card()
serialized = {
    "name": card.name,
    "effect_definitions": card.effect_definitions,  # ← String persisted
    "modifications": card.modifications.copy(),  # ← Copy to avoid mutation
    # ... other fields
}

# For transformed Copy cards
if card._is_transformed:
    modifications['_is_transformed'] = True  # Store flag in modifications
```text
**Note**: Always include `effect_definitions` in serialized data and create a
copy of the modifications dict before mutating to avoid aliasing issues.

### Load Flow

```python
# deserialize_card()
card = Card(
    name=data["name"],
    effect_definitions=data["effect_definitions"],  # ← Source of truth
    modifications=data["modifications"],
)

# Restore transformation state
if modifications.get('_is_transformed'):
    card._is_transformed = True
    card._copied_effects = EffectFactory.parse_effects(
        card.effect_definitions,  # ← Rebuild from string
        card
    )
```text
### Database Storage

```sql
-- games table
game_state JSONB  -- Contains serialized GameState
```text
Example JSONB structure:

```json
{
  "players": {
    "player1": {
      "in_play": [
        {
          "name": "Ka",
          "effect_definitions": "stat_boost:strength:2",
          "modifications": {},
          ...
        },
        {
          "name": "Copy of Ka",
          "effect_definitions": "stat_boost:strength:2",
          "modifications": {"_is_transformed": true},
          ...
        }
      ]
    }
  }
}
```text
---

## Common Pitfalls

### 1. Forgetting effect_definitions in Card Constructor

**❌ Bad**:
```python
card = Card(name=template.name, strength=template.strength)
# Missing effect_definitions!
```text
**✅ Good**:
```python
card = Card(
    name=template.name,
    effect_definitions=template.effect_definitions,  # ← Don't forget!
    strength=template.strength
)
```text
### 2. Mutating Original Modifications Dict

**❌ Bad**:
```python
card.modifications['new_key'] = value  # Mutates original!
return {"modifications": card.modifications}
```text
**✅ Good**:
```python
modifications = card.modifications.copy()  # Create copy first
modifications['new_key'] = value
return {"modifications": modifications}
```text
### 3. Testing Only Unit Level

**❌ Bad**:
```python
def test_copy_effect():
    effect = CopyEffect(card)
    effect.apply()
    assert card._copied_effects  # ✓ Passes but doesn't test persistence!
```text
**✅ Good**:
```python
def test_copy_effect_full_cycle():
    game = create_game()
    execute_copy_action()

    # Serialize and deserialize
    serialized = serialize_game_state(game.game_state)
    loaded = deserialize_game_state(serialized)

    # Create new engine and verify stats
    engine = GameEngine(loaded)
    assert engine.get_card_stat(card, 'strength') == expected
```text
### 4. Using Commas Instead of Semicolons

**❌ Bad**:
```python
effect_definitions = "stat_boost:strength:2,stat_boost:speed:1"  # Comma!
```text
**✅ Good**:
```python
effect_definitions = "stat_boost:strength:2;stat_boost:speed:1"  # Semicolon!
```text
### 5. Not Handling Missing effect_definitions

**❌ Bad**:
```python
effects = EffectFactory.parse_effects(card.effect_definitions, card)
# Crashes if effect_definitions doesn't exist!
```text
**✅ Good**:
```python
if hasattr(card, 'effect_definitions') and card.effect_definitions:
    effects = EffectFactory.parse_effects(card.effect_definitions, card)
else:
    effects = []
```text
---

## Debug Tools

### 1. Debug Endpoint

**Endpoint**: `GET /games/{id}/debug`

Exposes complete game state including:
- All cards in all zones
- Effect definitions (CSV strings)
- Parsed effect objects
- Modifications and transformations
- Internal flags like `_is_transformed`

**Note**: Dev-only endpoint. Exposes complete game state including opponent's
hand for debugging purposes.

Example response:

```json
{
  "game_id": "abc123",
  "players": {
    "player1": {
      "in_play": [
        {
          "name": "Ka",
          "effect_definitions": "stat_boost:strength:2",
          "parsed_effects": [
            {
              "class": "StatBoostEffect",
              "repr": "StatBoostEffect(Ka, strength, 2)"
            }
          ],
          "base_stats": {"strength": 9, "speed": 5, "stamina": 9},
          "effective_stats": {"strength": 13, "speed": 5, "stamina": 9},
          "modifications": {},
          "is_transformed": false
        }
      ]
    }
  }
}
```text
### 2. Script: check_game_state.py

Inspect specific game from database:

```bash
cd backend
python check_game_state.py <game_id>
```text
### 3. Script: check_copy_effects.py

Check Copy effect state for debugging:

```bash
cd backend
python check_copy_effects.py <game_id>
```text
### 4. Add Debug Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.debug(f"Card {card.name} effect_definitions: {card.effect_definitions}")
logger.debug(f"Parsed effects: {[type(e).__name__ for e in effects]}")
logger.debug(f"Stats: strength={engine.get_card_stat(card, 'strength')}")
```text
### 5. Comprehensive Serialization Tests

Located: `backend/tests/test_comprehensive_serialization.py`

Tests that all Card fields survive save/load cycle:
- All card types (Toy, Action)
- All zones (Hand, InPlay, Break)
- Transformed cards
- Multi-effect cards
- Edge cases from issue #77

Run tests:
```bash
cd backend
python -m pytest tests/test_comprehensive_serialization.py -v
```text
---

## Related Documents

- [NEXT_SESSION_PROMPT.md](NEXT_SESSION_PROMPT.md) - Current development status
- [EFFECT_MIGRATION_PLAN.md](../EFFECT_MIGRATION_PLAN.md) - Migration roadmap
- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall system architecture

---

## Glossary

- **effect_definitions**: String field on Card containing semicolon-separated
  effect specifications from CSV
- **_copied_effects**: Runtime list of effect objects, used by transformed Copy
  cards
- **EffectFactory**: Parser that converts effect_definitions strings into effect
  objects
- **EffectRegistry**: Central dispatcher for getting a card's effects
- **Continuous Effect**: Ongoing modification (stat buffs, cost changes)
- **Action Effect**: One-time trigger when action card is played
- **Serialization**: Converting game state to JSON for database storage
- **Deserialization**: Reconstructing game state from JSON

---

**Last Updated**: December 8, 2025
