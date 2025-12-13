---
applyTo: 'backend/**/*.py'
description: "Core architecture principles for GGLTCG game engine and backend"
---

# GGLTCG Architecture Principles

## 1. ID-Based Lookups (NEVER Use Names)

**CRITICAL**: Always use unique card IDs for lookups, NEVER use card names.

**Why**: Multiple cards can have the same name in different zones. Name-based lookups cause bugs when targeting/finding cards.

**✅ CORRECT**:
```python
card = game_state.find_card_by_id(card_id)
target = game_state.find_card_by_id(target_id)
```

**❌ WRONG**:
```python
card = next((c for c in cards if c.name == "Ka"), None)  # NEVER DO THIS
```

**Exceptions**: NONE. Even Knight/Beary interactions use effect types, not names.

## 2. Method-Based State Modification (NEVER Direct Assignment)

**CRITICAL**: Always use proper methods to modify card state. NEVER assign to attributes directly.

**Why**: Direct modification bypasses game logic, stat calculations, and effect triggers.

**✅ CORRECT**:
```python
# Damage
card.apply_damage(amount)  # Updates current_stamina

# Check if defeated
if card.is_defeated():  # Checks current_stamina
    game_engine._sleep_card(card, owner, was_in_play=True)

# Stat modifications
card.modifications["strength"] = 2  # Via effect system
```

**❌ WRONG**:
```python
card.stamina -= 1  # Modifies base stat, not current!
card.strength = 5  # Bypasses effect calculations!

if card.stamina <= 0:  # Checks wrong attribute!
    sleep_card()
```

**Exceptions**: Initial card creation in constructors/factories only.

## 3. GameEngine vs GameState Separation

**Architecture Rule**: GameState is pure data, GameEngine contains all game logic.

**GameState** (Data Container):
- Stores current game state (players, turn, phase, etc.)
- Provides data access methods (get_active_player, find_card_by_id, etc.)
- NO game logic, NO effect triggering, NO cost calculations

**GameEngine** (Logic Orchestrator):
- All game rules and mechanics
- Effect triggering and resolution
- Cost calculations
- Victory condition checking
- Turn management

**✅ CORRECT**:
```python
# Call GameEngine methods that trigger effects
game_engine._sleep_card(card, owner, was_in_play=True)
game_engine.play_card(player, card, target_ids=[target.id])

# Use GameState for data access only
player = game_state.get_active_player()
cards = game_state.get_cards_in_play(player)
```

**❌ WRONG**:
```python
# Don't call GameState methods that should trigger effects
game_state.sleep_card(card, was_in_play=True)  # Bypasses when-sleeped effects!

# Don't put game logic in GameState
if game_state.calculate_cost(card):  # Logic belongs in GameEngine!
    ...
```

**When to use which**:
- Need to trigger effects? → `game_engine`
- Need to access data? → `game_state`
- Unsure? → Use `game_engine` (it will use `game_state` internally)

## 4. Owner vs Controller (Stolen Cards)

**CRITICAL**: Understand the difference between `card.owner` and `card.controller`.

| Property | Meaning | Changes? |
|----------|---------|----------|
| `owner` | Original card owner | NEVER changes |
| `controller` | Who currently controls the card | Changes via Twist |

**Key Rules**:
- Cards always sleep to **owner's** sleep zone
- "Your cards" effects check **controller**, not owner
- When sleeping a stolen card, remove from **controller's** `in_play`, add to **owner's** `sleep_zone`

**✅ CORRECT** (in `_sleep_card`):
```python
controller = game_state.players.get(card.controller)
owner = game_state.players.get(card.owner)

if controller != owner:
    # Stolen card - remove from controller's zone
    controller.in_play.remove(card)
    # Add to owner's sleep zone
    owner.sleep_zone.append(card)
```

## 5. Tussle Logic (Single Source of Truth)

Tussle logic is consolidated in GameEngine with these key methods:

| Method | Purpose |
|--------|---------|
| `_execute_tussle()` | Actual tussle execution with side effects |
| `predict_tussle_winner()` | AI prediction (returns "attacker"/"defender"/"tie") |
| `get_effective_stamina()` | Get stamina with continuous effects applied |
| `is_card_defeated()` | Check if card should be sleeped |

All tussle-related logic lives in `game_engine.py`.

## 6. Effect System - Data-Driven First

**Pattern**: Use data-driven CSV effect definitions. Only create custom effect classes for truly unique mechanics.

**Data-Driven (Preferred)**:
```csv
name,type,cost,effect_definitions,...
Ka,Toy,1,stat_boost:strength:2,...
Rush,Action,0,gain_cc:2:not_first_turn,...
Clean,Action,0,sleep_all,...
```

**Custom Effect Class (Only if necessary)**:
```python
class CopyEffect(PlayEffect):
    """Complex dynamic behavior that can't be parameterized."""
    def apply(self, game_state, **kwargs):
        # Custom logic here
        ...
```

**Effect Type Checking**:
```python
# Use isinstance() to check effect types
if isinstance(effect, PlayEffect):
    ...
if isinstance(effect, ContinuousEffect):
    ...
if isinstance(effect, ActivatedEffect):
    ...
```

## 7. Common Anti-Patterns to Avoid

### Magic Strings
```python
# BAD
if action_type == "play_card":
    ...

# GOOD
if action.action_type == ActionType.PLAY_CARD:
    ...
```

### Code Duplication
```python
# BAD - same logic in multiple places
def ai_play_card(...):
    # validate, execute

def human_play_card(...):
    # same validate, execute (duplicated!)

# GOOD - shared logic
def play_card(action: PlayCardAction):
    ActionValidator.validate(action)
    ActionExecutor.execute(action)
```

### Hardcoded Card Names
```python
# BAD
if card.name == "Wake":
    # Special handling

# GOOD
effects = EffectRegistry.get_effects(card)
for effect in effects:
    if isinstance(effect, UnsleepEffect):
        # Handle based on effect type
```

## 8. Troubleshooting Guide

**Issue**: "Card not found by ID"
- Check that IDs are being passed, not names
- Verify card exists in the specified zone
- Check serialization/deserialization preserves IDs

**Issue**: "Card shows wrong stats (e.g., 1/2 instead of 2/4)"
- Direct stat modification detected
- Use `apply_damage()` instead of `card.stamina -= amount`
- Check `current_stamina` not `stamina`

**Issue**: "Effect doesn't trigger"
- Verify effect is in card's `effect_definitions` CSV field
- Check GameEngine is being used, not GameState
- Verify effect type (PlayEffect, TriggeredEffect, etc.)

**Issue**: "AI makes illegal moves"
- Check `prompts.py` card descriptions are accurate
- Verify `ActionValidator` returns correct valid actions
- Ensure AI sees buffed stats, not base stats
