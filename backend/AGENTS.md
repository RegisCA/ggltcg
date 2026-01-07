# Backend Guide

**Purpose**: Backend-specific context for GitHub Copilot agents  
**Parent**: See root `AGENTS.md` for project-wide context  
**Last Updated**: January 7, 2026

---

## 🔴 Check Backend Facts First

Before writing backend code, verify these facts:

### Game State Manipulation (HIGH RISK)

**Problem**: Agents bypass game logic with direct state modifications

**Solution**: Always use GameEngine methods, never direct attribute assignment

| ✅ CORRECT | ❌ WRONG |
|------------|----------|
| `card.apply_damage(3)` | `card.stamina -= 3` |
| `card.is_defeated()` | `card.stamina <= 0` |
| `engine._sleep_card(card, owner, True)` | `player.sleep_zone.append(card)` |
| `game_state.find_card_by_id(id)` | `next(c for c in cards if c.name == name)` |

### Test Setup (HIGH RISK - Causes impossible states)

**Problem**: Tests create invalid game states with wrong turn/player combinations

**Solution**: Always verify turn parity matches active player

- Odd turns (1, 3, 5...) → `active_player="player1"`
- Even turns (2, 4, 6...) → `active_player="player2"`

```python
# ✅ CORRECT - explicit and valid
setup, cards = create_game_with_cards(
    player1_hand=["Ka"],
    turn_number=3,  # P1's second turn
    active_player="player1",
    player1_cc=4,
)

# ❌ WRONG - impossible state
setup, cards = create_game_with_cards(
    turn_number=2,
    active_player="player1",  # INVALID! Turn 2 is P2's turn
)
```

---

## Architecture Patterns

### ID-Based Lookups (CRITICAL)

Multiple cards can have the same name in different zones. **Always use IDs**.

```python
# ✅ CORRECT
card = game_state.find_card_by_id(card_id)
target = game_state.find_card_by_id(target_id)

# ❌ WRONG - will fail with duplicate card names
card = next((c for c in cards if c.name == "Ka"), None)
```

### GameEngine vs GameState

| Class | Purpose | Contains |
|-------|---------|----------|
| **GameEngine** | All game logic | Effect triggers, cost calculations, tussles, victory |
| **GameState** | Pure data container | Players, cards, zones, turn, phase |

```python
# ✅ CORRECT - GameEngine for logic
engine.play_card(player, card, target_ids=[target.id])
engine._sleep_card(card, owner, was_in_play=True)

# ❌ WRONG - GameState shouldn't have logic
game_state.play_card(card)  # Method shouldn't exist here
```

### Owner vs Controller (Stolen Cards)

| Property | Meaning | Changes? |
|----------|---------|----------|
| `owner` | Original card owner | NEVER |
| `controller` | Who currently controls | Yes, via Twist |

- Cards **always** sleep to `owner`'s sleep zone
- "Your cards" effects check `controller`, not owner
- When sleeping stolen card: remove from `controller.in_play`, add to `owner.sleep_zone`

### Method-Based State Modification

```python
# ✅ CORRECT - uses proper methods
card.apply_damage(amount)        # Updates current_stamina
card.is_defeated()               # Checks current_stamina
card.modifications["strength"]   # Via effect system

# ❌ WRONG - bypasses game logic
card.stamina -= 1                # Modifies BASE stat, not current!
card.strength = 5                # Bypasses effect calculations!
```

---

## Effect System

### Data-Driven First

Card effects are defined in `backend/data/cards.csv`, parsed by `EffectRegistry`.

```csv
name,type,cost,effect_definitions,...
Ka,Toy,1,stat_boost:strength:2,...
Rush,Action,0,gain_cc:2:not_first_turn,...
Clean,Action,0,sleep_all,...
```

**Custom classes only** for truly unique mechanics (Copy, Transform).

### Effect Type Checking

```python
if isinstance(effect, PlayEffect):
    effect.apply(game_state, **kwargs)
if isinstance(effect, ContinuousEffect):
    effect.get_stat_modifier(card)
if isinstance(effect, ActivatedEffect):
    effect.can_activate(card, game_state)
```

**See**: `docs/development/EFFECT_SYSTEM_ARCHITECTURE.md`

---

## Testing Patterns

### Use Fixtures from conftest.py

```python
from conftest import create_game_with_cards, create_basic_game, steal_card

# Create game with specific cards
setup, cards = create_game_with_cards(
    player1_hand=["Sun", "Wake"],
    player1_in_play=["Ka"],
    player2_in_play=["Knight", "Beary"],
    active_player="player1",
    turn_number=3,
    player1_cc=5,
)

# Access created cards by key pattern
ka = cards["p1_inplay_Ka"]
knight = cards["p2_inplay_Knight"]
```

### Method Signatures

```python
# Tussle - CORRECT argument order
engine.initiate_tussle(attacker, defender, player)

# Play card with targets
engine.play_card(player, card, target_ids=[card1.id, card2.id])

# Play card with alternative cost
engine.play_card(player, card, alternative_cost_card_id=cost_card.id)
```

### Card Creation Helpers

```python
from conftest import create_beary, create_knight, create_ka, create_copy

# Cards have correct stats and effects from CSV
beary = create_beary(owner="player1", zone=Zone.IN_PLAY)
ka = create_ka(owner="player2")
```

### Anti-Patterns

```python
# ❌ NEVER create cards manually
card = Card(name="Ka", card_type=CardType.TOY, ...)

# ✅ USE fixtures that load from CSV
setup, cards = create_game_with_cards(player1_in_play=["Ka"])
```

---

## Python Code Style

### Type Hints (Required)

```python
def play_card(
    player: Player,
    card: Card,
    target_ids: Optional[List[str]] = None
) -> None:
    ...
```

### Import Order

```python
# Standard library
import os
from typing import List, Optional

# Third-party
from fastapi import APIRouter

# Local
from ..models.card import Card
from ..models.game_state import GameState
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed info")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

### Docstrings

```python
def apply_damage(self, amount: int) -> None:
    """
    Apply damage to this card, reducing current stamina.
    
    Args:
        amount: Amount of damage to apply (positive integer)
        
    Raises:
        ValueError: If amount is negative
    """
```

---

## AI System (V4 Architecture)

### Dual-Request Pattern

1. **Request 1** (Sequence Generator): Generate valid action sequences
2. **Request 2** (Strategic Selector): Evaluate and select best sequence

**Files**:
- `backend/src/game_engine/ai/prompts/sequence_generator.py`
- `backend/src/game_engine/ai/prompts/strategic_selector.py`
- `backend/src/game_engine/ai/prompts/turn_planner.py`

**Roadmap**: `docs/plans/AI_V4_REMEDIATION_PLAN.md`

### Common AI Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| AI makes illegal moves | Card descriptions in prompt don't match actual effects | Update card text in `turn_planner.py` |
| AI sees wrong stats | Using base stats instead of buffed | Check `get_effective_*()` methods |
| Target selection wrong | Card ID vs name confusion | Ensure IDs in valid actions list |

---

## Running Tests

```bash
# From project root, venv activated
cd backend
pytest tests/ -v                    # All tests
pytest tests/test_game_engine.py -v # Specific file
pytest tests/test_file.py::TestClass::test_method -v  # Specific test
pytest --cov=src tests/             # With coverage
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Card not found by ID" | Check IDs passed, not names; verify zone |
| "Card shows wrong stats" | Use `apply_damage()` not direct assignment |
| "Effect doesn't trigger" | Check CSV `effect_definitions`; use GameEngine |
| "Invalid turn state" | Verify turn_number parity matches active_player |

---

## Key Files

| File | Purpose |
|------|---------|
| `src/game_engine/game_engine.py` | Core game logic |
| `src/game_engine/game_state.py` | Game state data |
| `src/game_engine/models/card.py` | Card model |
| `src/game_engine/effects/` | Effect system |
| `data/cards.csv` | Card definitions |
| `tests/conftest.py` | Test fixtures |
