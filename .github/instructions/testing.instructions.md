---
applyTo: 'backend/tests/**/*.py'
description: "Testing standards and patterns for GGLTCG backend tests"
---

# GGLTCG Testing Instructions

**Full details**: See `backend/BACKEND_GUIDE.md` for comprehensive testing patterns.

## ⚠️ Critical: Turn Number Validation

**Odd turns** (1, 3, 5...) → `active_player="player1"`  
**Even turns** (2, 4, 6...) → `active_player="player2"`

```python
# ✅ CORRECT - explicit and valid
setup, cards = create_game_with_cards(
    turn_number=3,           # P1's second turn
    active_player="player1", # Matches odd turn
)

# ❌ WRONG - impossible state
setup, cards = create_game_with_cards(
    turn_number=2,           # P2's turn
    active_player="player1", # INVALID!
)
```

## Test Fixtures (conftest.py)

```python
from conftest import create_game_with_cards, steal_card

# Create game with specific cards
setup, cards = create_game_with_cards(
    player1_hand=["Sun", "Wake"],
    player1_in_play=["Ka"],
    player2_in_play=["Knight"],
    active_player="player1",
    turn_number=3,
    player1_cc=5,
)

# Access cards by key pattern: p{1|2}_{zone}_{CardName}
ka = cards["p1_inplay_Ka"]
knight = cards["p2_inplay_Knight"]
```

## Method Signatures

```python
# Tussle - CORRECT argument order
engine.initiate_tussle(attacker, defender, player)

# Play card with targets
engine.play_card(player, card, target_ids=[target.id])
```

## Anti-Patterns

| ❌ Don't | ✅ Do Instead |
|----------|---------------|
| Create cards manually | Use `create_game_with_cards()` fixture |
| Look up cards by name | Use card IDs from fixture |
| Bypass GameEngine | Use `engine._sleep_card()` not direct zone manipulation |
| Rely on defaults | Explicitly set `turn_number` and `active_player` |

## Running Tests

```bash
cd backend
pytest tests/ -v                    # All tests
pytest tests/test_file.py -v        # Specific file
pytest tests/test_file.py::TestClass::test_method -v  # Specific test
```

