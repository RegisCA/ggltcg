"""Sequence-selection policies for LLM-free simulation.

``TurnPlanner`` narrows every turn to at most ``DEFAULT_MAX_SEQUENCES`` (12)
engine-legal action sequences and then asks Gemini for one integer. A policy here
supplies that integer locally, so a game costs CPU instead of API requests.

The policies differ in how much they look ahead, which is the point: a card that
grades well under every policy is genuinely strong, whereas one that grades well
only under ``greedy`` is an artifact of that heuristic's myopia. See
``docs/development/CARD_EVALUATION_PLAN.md``.

Every policy takes ``(sequences, game_state, player_id, rng, enum_kwargs)`` and
returns an index. ``rng`` is a per-game seeded ``random.Random`` — policies must
never touch the global ``random`` module, or runs stop being reproducible.
``enum_kwargs`` carries the caller's enumerator ceilings so a policy that
enumerates further (``search2``) models the opponent under the same limits it
plays under; policies that do not look ahead simply ignore it.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Protocol

logger = logging.getLogger(__name__)


class SelectionPolicy(Protocol):
    """Chooses one of the enumerated sequences for the current turn."""

    name: str

    def __call__(
        self,
        sequences: List[Dict[str, Any]],
        game_state: Any,
        player_id: str,
        rng: Any,
        enum_kwargs: Dict[str, Any] | None = None,
    ) -> int: ...


def _named(name: str) -> Callable:
    def decorate(fn):
        fn.name = name
        return fn

    return decorate


@_named("greedy")
def greedy(sequences, game_state, player_id, rng, enum_kwargs=None) -> int:
    """Take the enumerator's own top-ranked line.

    ``enumerator._rank_key`` orders by: wins first, then most opponent breaks,
    fewest self-breaks, least Charge wasted, shortest. That is a strong but
    strictly single-turn heuristic — it never banks Charge for a bigger next turn
    (the Charge-waste term actively discourages it) and never values a board
    position that only pays off later. Expect it to overrate tempo and underrate
    setup.
    """
    return 0


@_named("random")
def random_policy(sequences, game_state, player_id, rng, enum_kwargs=None) -> int:
    """Uniform over legal sequences — the null model.

    Every line here is engine-legal and the enumerator already filters absurd
    lines, so this is "plays legally, chooses without judgement", not "plays
    badly at random". A card that grades well under this policy is winning on raw
    card quality rather than on being piloted well.
    """
    return rng.randrange(len(sequences))


@_named("softmax")
def softmax(sequences, game_state, player_id, rng, enum_kwargs=None) -> int:
    """Greedy with jitter: uniform over the top 3 ranked lines.

    Cheap way to get variance out of an almost-deterministic engine without
    giving up competence, which matters because the only native randomness in the
    game is ``random.choice`` on a direct attack. Useful when a matchup needs a
    distribution rather than a single replayed game.
    """
    return rng.randrange(min(3, len(sequences)))


# --- depth-2 search ---------------------------------------------------------

def _score_state(game_state, player_id: str) -> float:
    """Heuristic value of a position from ``player_id``'s seat.

    Deliberately simple and material-flavoured: broken cards dominate, then board
    presence, then Charge. It exists to *rank* the opponent's likely replies, not
    to be a faithful evaluation, and it must stay cheap — it runs once per node.
    """
    me = game_state.players[player_id]
    opp = game_state.get_opponent(player_id)

    if game_state.winner_id == player_id:
        return 1000.0
    if game_state.winner_id is not None:
        return -1000.0

    # Opponent cards in their break zone are progress for us, and vice versa.
    score = 10.0 * (len(opp.break_zone) - len(me.break_zone))

    me_board = me.in_play
    opp_board = opp.in_play
    score += 3.0 * (len(me_board) - len(opp_board))

    # Surviving stats are worth something beyond raw card count.
    score += 0.5 * sum((c.strength or 0) + (c.stamina or 0) for c in me_board)
    score -= 0.5 * sum((c.strength or 0) + (c.stamina or 0) for c in opp_board)

    score += 0.3 * (me.charge - opp.charge)
    score += 1.0 * (len(me.hand) - len(opp.hand))
    return score


MAX_REPLIES_CONSIDERED = 6


@_named("search2")
def search2(sequences, game_state, player_id, rng, enum_kwargs=None) -> int:
    """Depth-2: for each of my lines, assume the opponent answers with theirs.

    Scores each candidate by the value of the position *after the opponent's best
    reply*, so lines that hand over a winning board rank below lines that do not
    — the specific blind spot ``greedy`` has.

    Cost is one full ``enumerate_sequences`` per candidate line (not a single node
    expansion), plus a replay per reply considered, so it runs roughly 20x slower
    than ``greedy``. Only the top ``MAX_REPLIES_CONSIDERED`` replies are scored;
    they arrive pre-ranked by the enumerator, so this keeps the opponent's most
    dangerous answers and drops the tail.

    ``enum_kwargs`` carries the caller's enumerator ceilings. Without it the reply
    model would silently stay at the 8-action default while our own lines ran to a
    raised ceiling — understating what the opponent can do back, in exactly the
    combo runs where long turns are the whole point.

    Falls back to ``greedy`` if the search cannot run (the enumerator raising
    mid-search must not abort a sweep game).
    """
    from game_engine.ai.enumerator import clone_game_state, enumerate_sequences
    from game_engine.game_engine import GameEngine

    opponent_id = "player2" if player_id == "player1" else "player1"
    best_index, best_score = 0, float("-inf")

    for index, seq in enumerate(sequences):
        try:
            state = clone_game_state(game_state)
            engine = GameEngine(state)
            if not _replay(engine, state, player_id, seq):
                continue

            if state.winner_id == player_id:
                return index

            # Hand the turn over before enumerating the reply. Without this the
            # opponent is modelled on our turn — no turn-start Charge, wrong
            # active player — which systematically understates what they can do
            # back to us, exactly the blind spot this policy exists to close.
            # end_turn() switches players, bumps the turn number and calls
            # start_turn() internally.
            engine.end_turn()
            engine.check_state_based_actions()
            if state.winner_id is not None:
                score = 1000.0 if state.winner_id == player_id else -1000.0
                if score > best_score:
                    best_index, best_score = index, score
                continue

            # Opponent's best single-turn reply, scored from our seat. Same
            # ceilings as our own enumeration, or the reply model is weaker than
            # the position it is meant to evaluate.
            replies = enumerate_sequences(state, opponent_id, **(enum_kwargs or {}))
            if replies:
                worst = float("inf")
                for reply in replies[:MAX_REPLIES_CONSIDERED]:
                    reply_state = clone_game_state(state)
                    reply_engine = GameEngine(reply_state)
                    if not _replay(reply_engine, reply_state, opponent_id, reply):
                        continue
                    worst = min(worst, _score_state(reply_state, player_id))
                score = worst if worst != float("inf") else _score_state(state, player_id)
            else:
                score = _score_state(state, player_id)
        except Exception:  # pragma: no cover - defensive, keeps sweeps alive
            logger.debug("search2 failed on sequence %s, skipping", index, exc_info=True)
            continue

        # Ties break toward the enumerator's own ranking, which is already sorted.
        if score > best_score:
            best_index, best_score = index, score

    return best_index


def _replay(engine, state, player_id: str, sequence: Dict[str, Any]) -> bool:
    """Apply an enumerated sequence to a cloned state. False if it desyncs."""
    from game_engine.ai.enumerator import _apply_step

    for action in sequence.get("actions", []):
        if action.get("action_type") == "end_turn":
            break
        step = {
            "action_type": action.get("action_type"),
            "card_id": action.get("card_id"),
            "card_name": action.get("card_name"),
            "target_ids": tuple(action.get("target_ids") or ()),
        }
        if not _apply_step(engine, player_id, step):
            return False
    return True


POLICIES: Dict[str, SelectionPolicy] = {
    p.name: p for p in (greedy, random_policy, softmax, search2)
}


def get_policy(name: str) -> SelectionPolicy:
    try:
        return POLICIES[name]
    except KeyError:
        raise ValueError(
            f"Unknown policy '{name}'. Available: {', '.join(sorted(POLICIES))}"
        ) from None
