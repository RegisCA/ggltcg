# Effect System Architecture

## Overview

The GGLTCG effect system is responsible for managing card abilities that modify game state, apply stat buffs, and trigger special actions. This document explains how effects flow through the system from initial data definition to runtime execution.

**Last Updated**: December 8, 2025
**Status**: Data-driven system complete for all current cards

---

## Table of Contents

1. [Data Flow Overview](#data-flow-overview)
2. [System Components](#system-components)
3. [Effect Types](#effect-types)
4. [Lifecycle](#lifecycle)
5. [Dual System Problem](#dual-system-problem)
6. [Serialization](#serialization)
7. [Common Pitfalls](#common-pitfalls)
8. [Debug Tools](#debug-tools)

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
```

### Key Principle

**`effect_definitions` (string) is the single source of truth.**

- Stored in CSV
- Copied to Card instances
- Persisted to database
- Runtime effect objects (`_copied_effects`) are **ephemeral** and rebuilt on demand

---

## System Components

### 1. Card Data (cards.csv)

Located: `backend/data/cards.csv`

Cards define their effects in the `effects` column using a domain-specific language:

```csv
name,effects
Ka,stat_boost:strength:2
Demideca,stat_boost:all:1
Wake,unsleep:1
Wizard,set_tussle_cost:1
```

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
```

### 3. EffectFactory

Located: `backend/src/game_engine/rules/effects/effect_registry.py`

Parses effect definition strings into runtime effect objects.

```python
# Parse single effect
"stat_boost:strength:2" → StatBoostEffect(card, "strength", 2)

# Parse multiple effects
"stat_boost:strength:2;unsleep:1" → [
    StatBoostEffect(card, "strength", 2),
    UnsleepEffect(card, 1)
]
```

**Supported Effect Types (as of December 2025)**:

- `stat_boost:stat_name:amount` – Continuous stat buffs (`speed`, `strength`, `stamina`, `all`)
- `gain_cc:amount[:not_first_turn]` – Gain CC when played, with optional `not_first_turn` restriction
- `unsleep:count` – Return cards from Sleep Zone to hand
- `sleep_all` – Sleep all cards in play
- `set_tussle_cost:cost` – Set cost for all your tussles
- `set_self_tussle_cost:cost[:not_turn_1]` – Set cost for this card's tussles, optionally disabled on turn 1
- `reduce_cost_by_sleeping` – Reduce play cost by number of your sleeping cards
- `opponent_cost_increase:amount` – Opponent's cards cost +amount CC to play
- `gain_cc_when_sleeped:amount` – Gain CC when this card is sleeped from play
- `opponent_immunity` – This card is immune to opponent's effects
- `team_opponent_immunity` – All your cards are immune to opponent's effects
- `alternative_cost_sleep_card` – May sleep one of your cards instead of paying CC
- `return_all_to_hand` – Return all cards in play to owners' hands
- `take_control` – Take control of an opponent's Toy
- `copy_card` – Copy another card's effect definitions onto this card
- `sleep_target:count` – Sleep targeted cards in play
- `return_target_to_hand:count` – Return targeted cards in play to hand
- `turn_stat_boost:all:amount` – One-turn stat buff to all your Toys
- `start_of_turn_gain_cc:amount` – Gain CC at start of your turn
- `on_card_played_gain_cc:amount` – Gain CC when you play another card

### 4. EffectRegistry

Located: `backend/src/game_engine/rules/effects/effect_registry.py`

Central dispatcher for getting a card's effects. Implements priority system:

```python
def get_effects(card: Card) -> List[BaseEffect]:
    # Priority 0: Pre-parsed copied effects (Copy card)
    if hasattr(card, '_copied_effects') and card._copied_effects:
        return card._copied_effects

    # Priority 1: Data-driven effect definitions (MODERN)
    if hasattr(card, 'effect_definitions') and card.effect_definitions:
        return EffectFactory.parse_effects(card.effect_definitions, card)

    # Priority 2: Name-based registry (LEGACY - being phased out)
    return cls._effect_map.get(card.name, [])
```

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
```

---

## Effect Types

### Continuous Effects

Apply ongoing modifications while card is in play.

**Base Class**: `ContinuousEffect`
**Location**: `backend/src/game_engine/rules/effects/continuous_effects.py`

Examples:
- **StatBoostEffect**: Ka buffs adjacent cards (+2 strength)
- **SetTussleCostEffect**: Wizard makes all tussles cost 1
- **GainCCWhenSleepedEffect**: Umbruh gains 1 CC when sleeped

### Action Effects

Trigger once when action card is played.

**Base Class**: `ActionEffect`
**Location**: `backend/src/game_engine/rules/effects/action_effects.py`

Examples:
- **UnsleepEffect**: Wake/Sun returns cards to hand
- **SleepAllEffect**: Clean sleeps all cards
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
```

**Common Mistake**: Forgetting to copy `effect_definitions` from template.

### 2. Runtime Effect Parsing

Effects are parsed **on demand** when stats are calculated:

```python
# GameEngine.get_card_stat()
effects = EffectRegistry.get_effects(ka_card)
# → EffectFactory.parse_effects("stat_boost:strength:2", ka_card)
# → [StatBoostEffect(ka_card, "strength", 2)]
```

### 3. Copy Card Transformation

Special case: Copy card creates `_copied_effects` list:

```python
# CopyEffect.apply()
copy_card._is_transformed = True
copy_card._copied_effects = EffectFactory.parse_effects(
    target.effect_definitions,  # Copy target's effect string
    copy_card
)
```

**Why `_copied_effects`?**
- Allows Copy card to have different effects than its original definition
- Takes priority in `EffectRegistry.get_effects()`
- Rebuilt on deserialization from `effect_definitions`

### 4. Stat Calculation

```python
# Example: Ka (9 base strength + 2 buff) adjacent to Copy of Ka (+2 buff)
engine.get_card_stat(ka_card, 'strength')
# → 9 (base) + 2 (Ka's effect) + 2 (Copy's effect) = 13
```

---

## Dual System Problem

**⚠️ TECHNICAL DEBT**: Two effect systems currently exist.

### Modern System (Data-Driven)

**Status**: ✅ Active for 10 cards
**Cards**: Ka, Demideca, Wake, Sun, Clean, Rush, Wizard, Raggy, Umbruh, Dream, Ballaber

```python
# Card data includes effect_definitions
card.effect_definitions = "stat_boost:strength:2"

# Effects parsed at runtime
effects = EffectFactory.parse_effects(card.effect_definitions, card)
```

**Advantages**:
- Single source of truth (CSV)
- Easy to add new cards
- No code changes needed for new effects
- Survives serialization

### Name-Based Effect Registration

Some cards with complex, unique effects use custom effect classes registered by name:

```python
# Effects registered by card name
EffectRegistry.register_effect("Knight", KnightEffect)
EffectRegistry.register_effect("Copy", CopyEffect)
EffectRegistry.register_effect("Twist", TwistEffect)

# Retrieved by EffectRegistry.get_effects()
effects = EffectRegistry.get_effects(card)
```

**When to use**:
- Complex, unique card mechanics (Knight, Beary, Archer, Copy, Twist, Toynado)
- Dynamic behavior that can't be parameterized in CSV

---

## Serialization

Effects are **not** directly serialized. Instead, we persist the `effect_definitions` string and rebuild effects on load.

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
```

**Note**: Always include `effect_definitions` in serialized data and create a copy of the modifications dict before mutating to avoid aliasing issues.

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
```

### Database Storage

```sql
-- games table
game_state JSONB  -- Contains serialized GameState
```

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
```

---

## Common Pitfalls

### 1. Forgetting effect_definitions in Card Constructor

**❌ Bad**:
```python
card = Card(name=template.name, strength=template.strength)
# Missing effect_definitions!
```

**✅ Good**:
```python
card = Card(
    name=template.name,
    effect_definitions=template.effect_definitions,  # ← Don't forget!
    strength=template.strength
)
```

### 2. Mutating Original Modifications Dict

**❌ Bad**:
```python
card.modifications['new_key'] = value  # Mutates original!
return {"modifications": card.modifications}
```

**✅ Good**:
```python
modifications = card.modifications.copy()  # Create copy first
modifications['new_key'] = value
return {"modifications": modifications}
```

### 3. Testing Only Unit Level

**❌ Bad**:
```python
def test_copy_effect():
    effect = CopyEffect(card)
    effect.apply()
    assert card._copied_effects  # ✓ Passes but doesn't test persistence!
```

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
```

### 4. Using Commas Instead of Semicolons

**❌ Bad**:
```python
effect_definitions = "stat_boost:strength:2,stat_boost:speed:1"  # Comma!
```

**✅ Good**:
```python
effect_definitions = "stat_boost:strength:2;stat_boost:speed:1"  # Semicolon!
```

### 5. Not Handling Missing effect_definitions

**❌ Bad**:
```python
effects = EffectFactory.parse_effects(card.effect_definitions, card)
# Crashes if effect_definitions doesn't exist!
```

**✅ Good**:
```python
if hasattr(card, 'effect_definitions') and card.effect_definitions:
    effects = EffectFactory.parse_effects(card.effect_definitions, card)
else:
    effects = []
```

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

**Note**: Dev-only endpoint. Exposes complete game state including opponent's hand for debugging purposes.

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
```

### 2. Script: check_game_state.py

Inspect specific game from database:

```bash
cd backend
python check_game_state.py <game_id>
```

### 3. Script: check_copy_effects.py

Check Copy effect state for debugging:

```bash
cd backend
python check_copy_effects.py <game_id>
```

### 4. Add Debug Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.debug(f"Card {card.name} effect_definitions: {card.effect_definitions}")
logger.debug(f"Parsed effects: {[type(e).__name__ for e in effects]}")
logger.debug(f"Stats: strength={engine.get_card_stat(card, 'strength')}")
```

### 5. Comprehensive Serialization Tests

Located: `backend/tests/test_comprehensive_serialization.py`

Tests that all Card fields survive save/load cycle:
- All card types (Toy, Action)
- All zones (Hand, InPlay, Sleep)
- Transformed cards
- Multi-effect cards
- Edge cases from issue #77

Run tests:
```bash
cd backend
python -m pytest tests/test_comprehensive_serialization.py -v
```

---

## Related Documents

- [NEXT_SESSION_PROMPT.md](NEXT_SESSION_PROMPT.md) - Current development status
- [EFFECT_MIGRATION_PLAN.md](../EFFECT_MIGRATION_PLAN.md) - Migration roadmap
- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall system architecture

---

## Glossary

- **effect_definitions**: String field on Card containing semicolon-separated effect specifications from CSV
- **_copied_effects**: Runtime list of effect objects, used by transformed Copy cards
- **EffectFactory**: Parser that converts effect_definitions strings into effect objects
- **EffectRegistry**: Central dispatcher for getting a card's effects
- **Continuous Effect**: Ongoing modification (stat buffs, cost changes)
- **Action Effect**: One-time trigger when action card is played
- **Serialization**: Converting game state to JSON for database storage
- **Deserialization**: Reconstructing game state from JSON

---

**Last Updated**: December 8, 2025
