---
applyTo: 'backend/**/*.py'
description: "Python code style and patterns for GGLTCG backend"
---

# Python Code Standards

**Full details**: See `backend/BACKEND_GUIDE.md` for comprehensive backend patterns.

## Style Guidelines

**PEP 8** with line length 100.

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
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed info")
logger.info("General information")
logger.error("Error occurred", exc_info=True)
```

### Docstrings (Required for public APIs)

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

## API Input Validation

```python
# Validate UUIDs
if not is_valid_uuid(card_id):
    raise ValueError("Invalid card ID")

# Validate ownership
if card not in player.hand:
    raise ValueError("Card not in player's hand")
```

## Debug Endpoints

```
GET /games/{game_id}/debug         # Full game state
GET /games/{game_id}/logs          # Game logs
GET /games/{game_id}/valid-actions # Valid actions
```
