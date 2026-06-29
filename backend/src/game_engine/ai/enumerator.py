"""
Deterministic sequence enumerator (WP-4).

Replaces V4's Request 1 (LLM sequence generation) with engine-side enumeration
of legal action sequences. Legal-sequence generation is a computation, not a
judgment call: a depth-limited search over the real action space — using a
cloned full-fidelity GameState and real GameEngine transitions — produces exact
Charge math by construction and cannot emit illegal actions.

The search reuses the two single-step authorities the live game already trusts:

- ``ActionValidator.get_valid_actions`` enumerates the legal actions in a state
  (with ``filter_for_ai=True`` to drop guaranteed-loss tussles, matching
  ``SuicideAttackValidator``).
- ``ActionExecutor`` applies a chosen action exactly as the human/AI endpoints
  do, so "tussle breaks the last toy → direct_attack becomes legal" falls out of
  real transitions rather than hand-written rules.

Output is the structured sequence-dict shape that ``add_tactical_labels`` and
``convert_sequence_to_turn_plan`` already consume (see
``prompts/sequence_generator.parse_sequences_response``): a list of action dicts
plus ``total_charge_spent``, ``charge_available``, ``cards_broken`` and a human-readable
``raw_string`` for the Request-2 selector prompt. Real ``card_id``s and exact
per-step Charge are a strict improvement over the LLM's regex-parsed string path.
"""

import contextlib
import copy
import itertools
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from game_engine.game_engine import GameEngine
from game_engine.rules.effects import EffectRegistry
from game_engine.rules.effects.base_effect import ActivatedEffect
from game_engine.validation import ActionExecutor, ActionValidator

from .card_metadata import CHARGE_GAIN_ON_PLAY
from .prompts.card_loader import build_card_labels

if TYPE_CHECKING:
    from game_engine.models.game_state import GameState

logger = logging.getLogger(__name__)

# Search bounds. Charge budget prunes most branches naturally (get_valid_actions
# only returns affordable actions); these cap the pathological cases the audit
# flagged: multi-target cards, repeated Archer activations, target-combination
# blow-up. Tunable; Phase 4.1 measures enumeration time against them.
DEFAULT_MAX_ACTIONS = 8          # max actions per sequence (length cap)
DEFAULT_MAX_SEQUENCES = 12       # max sequences returned (ranked) for selection
DEFAULT_MAX_TARGET_OPTIONS = 5   # target ids considered per targeted action
DEFAULT_MAX_TARGET_COMBOS = 8    # multi-target combinations considered per action
MAX_NODES = 4000                 # hard safety stop on total states expanded


@contextlib.contextmanager
def _quiet_simulation_logs():
    """Silence ActionExecutor's per-play INFO logging during enumeration.

    The DFS drives ``ActionExecutor`` hundreds of times on cloned states; each
    play would otherwise emit an INFO line ("Playing X with target ..."),
    flooding the logs with *simulated* (non-real) moves. We raise only that one
    logger to WARNING for the search and restore it afterward.

    Note: logger levels are process-global, so under heavy concurrency a parallel
    real action could be briefly de-noised too. Acceptable for the experimental
    enum path — the window is the (sub-second) enumeration only.
    """
    exec_logger = logging.getLogger("game_engine.validation.action_executor")
    prev = exec_logger.level
    exec_logger.setLevel(logging.WARNING)
    try:
        yield
    finally:
        exec_logger.setLevel(prev)


def clone_game_state(game_state: "GameState") -> "GameState":
    """Return a full-fidelity deep clone of ``game_state`` for offline search.

    The enumerator needs the *complete* state — including the opponent's hand —
    so it can reason about every legal line. Two other clone paths in the
    codebase are deliberately NOT used here:

    - ``GameState.from_dict(gs.to_dict())`` redacts **both** hands to ``[]`` when
      no ``requesting_player_id`` is supplied (``Player.to_dict`` defaults to
      ``reveal_hand=False``), so it silently loses hand contents.
    - ``serialize_game_state`` / ``deserialize_game_state`` preserve hands but
      drop ``charge_history`` and the transient in-turn Charge-tracking fields.

    ``copy.deepcopy`` reproduces the entire object graph — both hands,
    ``charge_history``, transient Charge tracking, and any dynamic per-card attributes
    (e.g. ``_copied_effects``) — with no references shared back to the original,
    so mutations during search cannot leak into the live game. It is safe
    because cards hold no live effect-object references: effects are resolved
    from ``EffectRegistry`` by the card's data strings, not stored on the card.
    """
    return copy.deepcopy(game_state)


def _state_signature(game_state: "GameState") -> Tuple:
    """A canonical, hashable fingerprint of the parts of state that affect search.

    Used as a transposition key so order-equivalent lines that reach the same
    board (e.g. Surge→Knight vs Knight→Surge) are explored once. Captures each
    player's Charge, per-card id/stamina/zone, and direct-attack count.
    """
    parts: List[Any] = []
    for pid in sorted(game_state.players):
        p = game_state.players[pid]
        parts.append((pid, p.charge, p.direct_attacks_this_turn))
        for zone_name, zone in (("h", p.hand), ("p", p.in_play), ("s", p.break_zone)):
            cards = sorted(
                (c.id, c.current_stamina, c.zone.value) for c in zone
            )
            parts.append((pid, zone_name, tuple(cards)))
    return tuple(parts)


def _expand_action(va, game_state: "GameState") -> List[Dict[str, Any]]:
    """Expand one ValidAction into concrete, applyable step dicts (one per target choice).

    ``ValidAction`` from ActionValidator describes *what* is legal and lists
    candidate targets; the search must branch on each concrete target selection.
    """
    at = va.action_type

    if at == "end_turn":
        return []  # implicit: every recorded prefix (incl. the empty one) is "…then end_turn"

    if at == "tussle":
        opts = va.target_options or []
        # ActionValidator encodes a direct attack as a tussle with
        # target_options == ["direct_attack"]; everything else is a real defender.
        if opts and opts[0] == "direct_attack":
            return [_step("direct_attack", va.card_id, va.card_name, ())]
        return [
            _step("tussle", va.card_id, va.card_name, (defender_id,))
            for defender_id in opts
        ]

    if at == "activate_ability":
        opts = (va.target_options or [])[:DEFAULT_MAX_TARGET_OPTIONS]
        if not opts:
            return [_step("activate_ability", va.card_id, va.card_name, ())]
        return [
            _step("activate_ability", va.card_id, va.card_name, (tid,))
            for tid in opts
        ]

    if at == "play_card":
        opts = va.target_options
        if not opts:
            return [_step("play_card", va.card_id, va.card_name, ())]

        min_t = va.min_targets or 1
        max_t = va.max_targets or 1
        opts = list(opts)[:DEFAULT_MAX_TARGET_OPTIONS]

        combos: List[Tuple[str, ...]] = []
        if min_t == 0:
            combos.append(())  # optional target: also allow playing with none
        for size in range(max(1, min_t), max_t + 1):
            for combo in itertools.combinations(opts, size):
                combos.append(combo)
        combos = combos[:DEFAULT_MAX_TARGET_COMBOS]
        return [
            _step("play_card", va.card_id, va.card_name, combo) for combo in combos
        ]

    return []


def _step(action_type: str, card_id, card_name, target_ids: Tuple[str, ...]) -> Dict[str, Any]:
    return {
        "action_type": action_type,
        "card_id": card_id,
        "card_name": card_name,
        "target_ids": target_ids,
    }


def _apply_step(engine: GameEngine, player_id: str, step: Dict[str, Any]) -> bool:
    """Apply one step to ``engine``'s state via the real execution path.

    Returns True on success. Any failure (illegal in this state, insufficient
    Charge, missing target) returns False so the branch is dropped — the search only
    ever keeps lines the engine actually accepts.
    """
    at = step["action_type"]
    target_ids = list(step["target_ids"])
    try:
        executor = ActionExecutor(engine)
        if at == "play_card":
            res = executor.execute_play_card(
                player_id, step["card_id"],
                target_card_ids=target_ids or None,
            )
            return res.success
        if at == "tussle":
            res = executor.execute_tussle(player_id, step["card_id"], defender_id=target_ids[0])
            return res.success
        if at == "direct_attack":
            res = executor.execute_tussle(player_id, step["card_id"], defender_id=None)
            return res.success
        if at == "activate_ability":
            return _apply_activate(engine, player_id, step["card_id"],
                                   target_ids[0] if target_ids else None)
    except Exception as exc:  # pragma: no cover - defensive; pruned silently
        logger.debug("enumerator: step %s failed: %s", at, exc)
        return False
    return False


def _apply_activate(engine: GameEngine, player_id: str, card_id: str,
                    target_id: Optional[str]) -> bool:
    """Apply an activated ability (e.g. Archer), mirroring routes_actions.

    ActionExecutor has no activate path, so this replicates the endpoint's:
    find source card → resolve its ActivatedEffect → pay Charge → apply → settle.
    """
    gs = engine.game_state
    player = gs.players[player_id]
    source = next((c for c in player.in_play if c.id == card_id), None)
    if source is None:
        return False
    effect = next(
        (e for e in EffectRegistry.get_effects(source) if isinstance(e, ActivatedEffect)),
        None,
    )
    if effect is None or player.charge < effect.cost_charge:
        return False
    target = gs.find_card_by_id(target_id) if target_id else None
    player.spend_charge(effect.cost_charge)
    effect.apply(gs, target=target, amount=1, game_engine=engine)
    engine.check_state_based_actions()
    return True


def _action_charge_cost(step: Dict[str, Any], charge_before: int, charge_after: int) -> int:
    """Real Charge cost of an applied step, derived from the Charge delta and known gains.

    charge_after = charge_before - cost + gain  ⇒  cost = charge_before - charge_after + gain.
    Every action's cost is just the Charge drop, except cards in
    ``CHARGE_GAIN_ON_PLAY`` which also grant Charge on play.
    """
    gain = 0
    if step["action_type"] == "play_card":
        gain = CHARGE_GAIN_ON_PLAY.get(step["card_name"], 0)
    return max(0, charge_before - charge_after + gain)


def enumerate_sequences(
    game_state: "GameState",
    player_id: str,
    *,
    max_actions: int = DEFAULT_MAX_ACTIONS,
    max_sequences: int = DEFAULT_MAX_SEQUENCES,
) -> List[Dict[str, Any]]:
    """Enumerate legal action sequences for ``player_id`` from ``game_state``.

    Depth-limited DFS over the real action space on cloned states. Every prefix
    is a valid "do these actions, then end turn" line, so each is recorded;
    order-equivalent lines are de-duplicated and the result is ranked
    (winning → most breaks → least Charge wasted → shortest) and capped at
    ``max_sequences``.

    Returns sequence dicts matching ``parse_sequences_response``'s shape so the
    rest of the V4 pipeline (validation cross-check, ``add_tactical_labels``,
    strategic selection, ``convert_sequence_to_turn_plan``) is unchanged.
    """
    start_opp_broken = len(game_state.get_opponent(player_id).break_zone)
    start_own_broken = len(game_state.players[player_id].break_zone)

    # Built once from the root state, before any simulated action moves cards
    # between zones. Card ids are stable through deepcopy, so this same
    # mapping resolves any target id encountered mid-search, and the
    # strategic-selector prompt computes the identical mapping independently
    # for its board legend (see build_card_labels' docstring).
    card_labels = build_card_labels(game_state, player_id)

    # multiset-of-steps signature -> best recorded sequence (order-equivalent dedupe)
    recorded: Dict[frozenset, Dict[str, Any]] = {}
    # state signature -> shallowest depth it was expanded at. A plain set would be
    # depth-insensitive: reaching a state via a *longer* path first would prune a
    # later *shorter* path that still has more depth budget under max_actions,
    # dropping valid (possibly best) continuations. Tracking the min depth lets us
    # re-expand when we arrive with more budget to spend.
    expanded_depth: Dict[Tuple, int] = {}
    node_budget = [MAX_NODES]

    def record(state: "GameState", path: List[Dict[str, Any]], costs: List[int]) -> None:
        # The empty path is the explicit "pass" line (do nothing, then end_turn);
        # recording it keeps behavior consistent with _expand_action's "every
        # prefix is recorded" contract and always gives the selector a pass option.
        # frozenset of (signature, count) makes order-equivalent paths collide.
        sig_counts: Dict[Tuple, int] = {}
        for s in path:
            key = (s["action_type"], s["card_id"], s["target_ids"])
            sig_counts[key] = sig_counts.get(key, 0) + 1
        multiset_sig = frozenset(sig_counts.items())

        opp = state.get_opponent(player_id)
        me = state.players[player_id]
        cards_broken = max(0, len(opp.break_zone) - start_opp_broken)
        # Net own cards left broken by this line. Wake/Sun move cards back out of
        # the break zone, so a Drop+Wake recovery combo nets to 0 (no penalty);
        # only a self-break with no payoff leaves the count positive.
        own_broken = max(0, len(me.break_zone) - start_own_broken)
        wins = state.winner_id == player_id
        total_charge_spent = sum(costs)
        charge_wasted = me.charge  # leftover Charge the line did not spend
        charge_available = total_charge_spent + charge_wasted

        candidate = {
            "actions": _format_actions(path, state),
            "total_charge_spent": total_charge_spent,
            "charge_available": charge_available,
            "cards_broken": cards_broken,
            "raw_string": _raw_string(path, total_charge_spent, charge_available, cards_broken, card_labels),
            # internal ranking fields (ignored by downstream consumers)
            "_wins": wins,
            "_own_broken": own_broken,
            "_charge_wasted": charge_wasted,
            "_length": len(path),
        }
        prev = recorded.get(multiset_sig)
        if prev is None or _rank_key(candidate) > _rank_key(prev):
            recorded[multiset_sig] = candidate

    def dfs(state: "GameState", path: List[Dict[str, Any]], costs: List[int]) -> None:
        record(state, path, costs)

        if len(path) >= max_actions or node_budget[0] <= 0 or state.winner_id is not None:
            return
        sig = _state_signature(state)
        # Prune only if we already expanded this state at an equal-or-shallower
        # depth (i.e. with at least as much remaining budget). Arriving via a
        # shorter path means more depth left, so re-expand and update the record.
        prev_depth = expanded_depth.get(sig)
        if prev_depth is not None and prev_depth <= len(path):
            return
        expanded_depth[sig] = len(path)
        node_budget[0] -= 1

        engine = GameEngine(state)
        valid = ActionValidator(engine).get_valid_actions(player_id, filter_for_ai=True)
        for va in valid:
            for step in _expand_action(va, state):
                child = clone_game_state(state)
                child_engine = GameEngine(child)
                charge_before = child.players[player_id].charge
                if not _apply_step(child_engine, player_id, step):
                    continue
                charge_after = child.players[player_id].charge
                cost = _action_charge_cost(step, charge_before, charge_after)
                step["charge_cost"] = cost  # real engine-derived cost (e.g. Raggy tussle = 0)
                dfs(child, path + [step], costs + [cost])

    root = clone_game_state(game_state)
    with _quiet_simulation_logs():
        dfs(root, [], [])

    # recorded always contains at least the empty "pass" line (recorded at the
    # root), so sequences is never empty.
    ranked = sorted(recorded.values(), key=_rank_key, reverse=True)
    # The pass line always ranks last; reserve a slot so the cap can't truncate it
    # away — the selector should always have an explicit "do nothing" option.
    pass_seq = recorded.get(frozenset())
    if pass_seq is not None and len(ranked) > max_sequences:
        sequences = [s for s in ranked if s is not pass_seq][:max_sequences - 1]
        sequences.append(pass_seq)
    else:
        sequences = ranked[:max_sequences]
    for seq in sequences:  # strip internal ranking fields
        for k in ("_wins", "_own_broken", "_charge_wasted", "_length"):
            seq.pop(k, None)

    logger.debug(
        "enumerator: %d sequences (from %d unique lines) for %s",
        len(sequences), len(recorded), player_id,
    )
    return sequences


def _rank_key(seq: Dict[str, Any]) -> Tuple:
    """Sort key: winning lines first, then most opponent breaks, fewest own cards
    left broken, least Charge waste, shortest.

    The ``-_own_broken`` term sits below ``cards_broken`` so a productive line that
    also self-breaks (e.g. Clean clearing the whole board) is still preferred when
    the opponent-break payoff justifies it, but above ``-_charge_wasted`` so spending
    Charge to break your own card can never out-rank simply not doing so. This is what
    keeps a pointless self-Drop ranked below the pass line.
    """
    return (
        1 if seq.get("_wins") else 0,
        seq.get("cards_broken", 0),
        -seq.get("_own_broken", 0),
        -seq.get("_charge_wasted", 0),
        -seq.get("_length", 0),
    )


def _format_actions(path: List[Dict[str, Any]], state: "GameState") -> List[Dict[str, Any]]:
    """Convert internal steps to the action-dict shape downstream consumers expect.

    Appends an explicit ``end_turn`` so the sequence matches the LLM format and
    ``convert_sequence_to_turn_plan`` produces a terminated plan.
    """
    actions: List[Dict[str, Any]] = []
    for step in path:
        target_ids = list(step["target_ids"])
        target_names = [
            t.name for tid in target_ids
            if (t := state.find_card_by_id(tid)) is not None
        ]
        # Prefer the real engine-derived cost recorded during the search; fall
        # back to nominal costs only if it is somehow absent.
        charge_cost = step.get(
            "charge_cost",
            {"tussle": 2, "direct_attack": 2, "activate_ability": 1}.get(step["action_type"], 0),
        )
        actions.append({
            "action_type": step["action_type"],
            "card_id": step["card_id"],
            "card_name": step["card_name"],
            "target_ids": target_ids or None,
            "target_id": target_ids[0] if target_ids else None,
            "target_names": target_names or None,
            "target_name": target_names[0] if target_names else None,
            "charge_cost": charge_cost,
        })
    actions.append(_end_turn_action())
    return actions


def _end_turn_action() -> Dict[str, Any]:
    return {
        "action_type": "end_turn",
        "card_id": None,
        "card_name": None,
        "target_ids": None,
        "target_id": None,
        "target_names": None,
        "target_name": None,
        "charge_cost": 0,
    }


def _raw_string(path: List[Dict[str, Any]], charge_spent: int, charge_available: int,
                cards_broken: int, card_labels: Dict[str, str]) -> str:
    """Human-readable line for the Request-2 selector prompt (format_sequence_for_display).

    Tussle/ability/play_card targets are rendered via ``card_labels`` (the same
    Y1/O2-style short labels shown in the prompt's board legend) instead of
    raw card-id UUIDs, so the model can actually tell which card a candidate
    sequence targets. ``card_labels`` covers the AI's own hand/in_play/
    break_zone and the opponent's in_play (see build_card_labels), so this
    also resolves Wake/Sun/Glue/"That was fun" recursion targets correctly.
    """
    parts = []
    for step in path:
        name = step["card_name"] or step["card_id"] or ""
        if step["action_type"] == "play_card":
            target_ids = step["target_ids"]
            if target_ids:
                targets = ",".join(card_labels.get(tid, tid) for tid in target_ids)
                parts.append(f"play {name}->{targets}".strip())
            else:
                parts.append(f"play {name}".strip())
        elif step["action_type"] == "tussle":
            tgt_id = step["target_ids"][0] if step["target_ids"] else "?"
            tgt = card_labels.get(tgt_id, tgt_id)
            parts.append(f"tussle {name}->{tgt}")
        elif step["action_type"] == "direct_attack":
            parts.append(f"direct_attack {name}".strip())
        elif step["action_type"] == "activate_ability":
            tgt_id = step["target_ids"][0] if step["target_ids"] else "?"
            tgt = card_labels.get(tgt_id, tgt_id)
            parts.append(f"activate {name}->{tgt}")
    actions_str = " -> ".join(parts) if parts else "end_turn"  # empty path = pass
    return f"{actions_str} | Charge: {charge_spent}/{charge_available} | Breaks: {cards_broken}"
