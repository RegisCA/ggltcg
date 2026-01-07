---
applyTo: 'backend/**/*.py'
description: "Core architecture principles for GGLTCG game engine and backend"
---

# GGLTCG Architecture Principles

**Full details**: See `backend/AGENTS.md` for comprehensive backend patterns.

## Critical Rules (Quick Reference)

### 1. ID-Based Lookups (NEVER Use Names)

```python
# ✅ CORRECT
card = game_state.find_card_by_id(card_id)

# ❌ WRONG
card = next((c for c in cards if c.name == "Ka"), None)
```

### 2. Method-Based State Modification (NEVER Direct Assignment)

```python
# ✅ CORRECT
card.apply_damage(amount)
if card.is_defeated():
    engine._sleep_card(card, owner, was_in_play=True)

# ❌ WRONG
card.stamina -= 1
if card.stamina <= 0:
    player.sleep_zone.append(card)
```

### 3. GameEngine vs GameState Separation

- **GameState**: Pure data (players, cards, zones, turn)
- **GameEngine**: All game logic (effects, costs, tussles)

```python
# ✅ CORRECT - GameEngine for logic
engine.play_card(player, card, target_ids=[target.id])

# ❌ WRONG - GameState shouldn't have logic
game_state.play_card(card)
```

### 4. Owner vs Controller (Stolen Cards)

- `owner`: Original owner (NEVER changes)
- `controller`: Current controller (changes via Twist)
- Cards always sleep to **owner's** sleep zone

### 5. Data-Driven Effects First

Card effects defined in `backend/data/cards.csv`, parsed by EffectRegistry.

Custom effect classes only for truly unique mechanics (Copy, Transform).

## Common Anti-Patterns

| ❌ Don't | ✅ Do Instead |
|----------|---------------|
| `if action_type == "play_card"` | `if action.action_type == ActionType.PLAY_CARD` |
| `if card.name == "Wake"` | `if isinstance(effect, UnsleepEffect)` |
| Duplicate logic in AI vs human paths | Shared `ActionValidator` + `ActionExecutor` |

