"""
Deterministic sequence enumerator (WP-4).

Replaces V4's Request 1 (LLM sequence generation) with engine-side enumeration
of legal action sequences. Legal-sequence generation is a computation, not a
judgment call: a depth-limited search over the real action space, using a cloned
full-fidelity GameState and real GameEngine transitions, produces exact CC math
by construction and cannot emit illegal actions.

Phase 4.0 (this file, initial): the full-fidelity state-clone utility the search
depends on. Later phases add the enumeration itself and wire an `enum` planner
mode through the selector.
"""

import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_engine.models.game_state import GameState


def clone_game_state(game_state: "GameState") -> "GameState":
    """Return a full-fidelity deep clone of ``game_state`` for offline search.

    The enumerator needs the *complete* state — including the opponent's hand —
    so it can reason about every legal line. Two other clone paths in the
    codebase are deliberately NOT used here:

    - ``GameState.from_dict(gs.to_dict())`` redacts **both** hands to ``[]`` when
      no ``requesting_player_id`` is supplied (``Player.to_dict`` defaults to
      ``reveal_hand=False``), so it silently loses hand contents.
    - ``serialize_game_state`` / ``deserialize_game_state`` preserve hands but
      drop ``cc_history`` and the transient in-turn CC-tracking fields.

    ``copy.deepcopy`` reproduces the entire object graph — both hands,
    ``cc_history``, transient CC tracking, and any dynamic per-card attributes
    (e.g. ``_copied_effects``) — with no references shared back to the original,
    so mutations during search cannot leak into the live game. It is safe
    because cards hold no live effect-object references: effects are resolved
    from ``EffectRegistry`` by the card's data strings, not stored on the card.
    """
    return copy.deepcopy(game_state)
