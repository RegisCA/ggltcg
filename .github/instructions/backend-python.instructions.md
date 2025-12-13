---
applyTo: 'backend/**/*.py'
description: "Python code style and patterns for GGLTCG backend"
---

# Python Code Standards

## Style Guidelines

**PEP 8** with line length 100.

### Type Hints

Always use type hints for function signatures:
```python
def play_card(
    player: Player,
    card: Card,
    target_ids: Optional[List[str]] = None
) -> None:
    ...
```

### Dataclasses

Use dataclasses for data structures:
```python
@dataclass
class ValidAction:
    action_type: str
    card_id: str
    target_options: Optional[List[str]] = None
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

logger.debug("Detailed info for debugging")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

## Documentation Standards

### Docstrings

**Required for**: All public functions/methods, classes, and modules.

```python
def apply_damage(self, amount: int) -> None:
    """
    Apply damage to this card, reducing current stamina.
    
    Damage reduces current_stamina, not base stamina.
    If current_stamina reaches 0, card should be sleeped.
    
    Args:
        amount: Amount of damage to apply (positive integer)
        
    Raises:
        ValueError: If amount is negative
    """
    if amount < 0:
        raise ValueError("Damage amount must be non-negative")
    
    self.current_stamina = max(0, self.current_stamina - amount)
```

### Code Comments

**When to comment**:
- Complex algorithms that aren't self-explanatory
- Non-obvious design decisions
- Workarounds for known issues (with issue number)

**When NOT to comment**:
- Self-explanatory code
- What the code does (code should be readable)

**Good comment**:
```python
# FIX (Issue #70): Check protection before applying effect
# Knight has opponent_immunity which prevents Clean from sleeping it
if game_state.is_protected_from_effect(card, self):
    continue
```

**Bad comment**:
```python
# Loop through cards  ← Obvious from code
for card in cards:
    ...
```

## API Input Validation

Always validate API inputs:
```python
# Validate UUIDs
if not is_valid_uuid(card_id):
    raise ValueError("Invalid card ID")

# Validate player owns card
if card not in player.hand:
    raise ValueError("Card not in player's hand")

# Validate targets are legal
if target not in effect.get_valid_targets(game_state):
    raise ValueError("Invalid target")
```

## Local Development

### Backend Setup

```bash
cd /Users/regis/Projects/ggltcg
source .venv/bin/activate
pip install -r backend/requirements.txt

cd backend
python run_server.py
# Server: http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Running Tests

```bash
# All tests
pytest backend/tests/

# Specific test file
pytest backend/tests/test_game_engine.py

# Specific test
pytest backend/tests/test_game_engine.py::test_play_card

# With coverage
pytest --cov=backend/src backend/tests/
```

## Debug Endpoints

```bash
GET /games/{game_id}/debug         # Full game state
GET /games/{game_id}/logs          # Game logs
GET /games/{game_id}/valid-actions?player_id={id}  # Valid actions
```
