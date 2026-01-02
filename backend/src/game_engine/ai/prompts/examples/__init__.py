"""
Contextual Example Library for AI V4.

Provides relevant examples based on current game state:
- Combo examples: When synergistic cards are present together
- Phase examples: Early/mid/end game patterns
- Card examples: Individual card tactical patterns

Usage:
    from .loader import get_relevant_examples
    examples = get_relevant_examples(game_state, player_id)
"""

from .loader import get_relevant_examples
from .phase_examples import PHASE_EXAMPLES
from .card_examples import CARD_EXAMPLES
from .combo_examples import COMBO_EXAMPLES

__all__ = [
    "get_relevant_examples",
    "PHASE_EXAMPLES",
    "CARD_EXAMPLES",
    "COMBO_EXAMPLES",
]
