"""
Phase 4.0 (WP-4): full-fidelity state-clone utility for the enumerator.

The deterministic sequence enumerator searches over legal action sequences on a
*cloned* game state so it never mutates the live game. These tests pin the two
properties the search depends on:

1. **Full fidelity** — the clone reproduces the entire state, including the
   opponent's hand (which the API-facing serialization paths redact) and
   ``cc_history`` (which serialize/deserialize drops).
2. **Isolation** — mutating the clone (directly or via a GameEngine) never leaks
   back into the original.

Plus a perf check: clone + a few engine transitions must stay in the low-ms
range so per-turn enumeration is cheap.
"""

import time

from conftest import create_game_with_cards
from game_engine.game_engine import GameEngine
from game_engine.models.game_state import TurnCCRecord
from game_engine.ai.enumerator import clone_game_state


def _scenario():
    """Active P1 with a board; P2 holds a hand, board, and sleep zone.

    P2's hand is the interesting part: the enumerator must see it, but
    ``to_dict()`` without a requesting player redacts it.
    """
    setup, cards = create_game_with_cards(
        player1_hand=["Knight", "Surge"],
        player1_in_play=["Knight"],
        player2_hand=["Drop", "Clean", "Wake"],
        player2_in_play=["Knight"],
        player2_sleep=["Surge"],
        active_player="player1",
        turn_number=2,
    )
    return setup.game_state


def test_clone_round_trips_opponent_hand_not_redacted():
    gs = _scenario()
    clone = clone_game_state(gs)

    orig_p2_hand = [c.name for c in gs.players["player2"].hand]
    clone_p2_hand = [c.name for c in clone.players["player2"].hand]

    assert clone_p2_hand == orig_p2_hand == ["Drop", "Clean", "Wake"]
    # Card identity is preserved (IDs not names) so the enumerator can target by ID.
    assert [c.id for c in clone.players["player2"].hand] == [
        c.id for c in gs.players["player2"].hand
    ]


def test_clone_preserves_all_zones_and_cc():
    gs = _scenario()
    clone = clone_game_state(gs)

    for pid in ("player1", "player2"):
        op, cp = gs.players[pid], clone.players[pid]
        assert cp.cc == op.cc
        assert [c.id for c in cp.hand] == [c.id for c in op.hand]
        assert [c.id for c in cp.in_play] == [c.id for c in op.in_play]
        assert [c.id for c in cp.sleep_zone] == [c.id for c in op.sleep_zone]

    assert clone.turn_number == gs.turn_number
    assert clone.active_player_id == gs.active_player_id
    assert clone.phase == gs.phase


def test_clone_preserves_cc_history():
    """serialize/deserialize drops cc_history; deepcopy must keep it."""
    gs = _scenario()
    gs.cc_history.append(
        TurnCCRecord(turn=1, player_id="player1", cc_start=0, cc_gained=2,
                     cc_spent=2, cc_end=0)
    )
    clone = clone_game_state(gs)

    assert len(clone.cc_history) == 1
    assert clone.cc_history[0].turn == 1
    assert clone.cc_history[0].cc_gained == 2


def test_mutating_clone_does_not_touch_original():
    gs = _scenario()
    clone = clone_game_state(gs)

    # Direct mutation via game methods. gain_cc caps at 7, so from 10 it lands
    # at 7 — the value doesn't matter, only that the clone moved and the
    # original did not.
    clone.players["player1"].gain_cc(5)
    clone.players["player2"].hand[0].apply_damage(1)

    assert gs.players["player1"].cc == 10  # unchanged
    assert clone.players["player1"].cc == 7
    assert clone.players["player1"].cc != gs.players["player1"].cc
    # The damaged clone card must be a distinct object from the original.
    assert clone.players["player2"].hand[0] is not gs.players["player2"].hand[0]


def test_engine_transitions_on_clone_are_isolated():
    """Apply a real engine action on the clone; original board is untouched."""
    gs = _scenario()
    clone = clone_game_state(gs)

    engine = GameEngine(clone)
    player = clone.get_active_player()
    knight_in_hand = next(c for c in player.hand if c.name == "Knight")

    before_in_play = len(gs.players["player1"].in_play)
    assert engine.play_card(player, knight_in_hand) is True

    # Clone advanced; original did not.
    assert len(clone.players["player1"].in_play) == before_in_play + 1
    assert len(gs.players["player1"].in_play) == before_in_play
    assert len(gs.players["player1"].hand) == 2  # original hand intact


def test_clone_plus_transitions_is_fast():
    """Clone + a few engine transitions must stay in the low-ms range.

    Generous ceiling (well above observed ~sub-ms) so CI noise doesn't flake it;
    the real measurement is printed for the record.
    """
    gs = _scenario()

    runs = 50
    start = time.perf_counter()
    for _ in range(runs):
        clone = clone_game_state(gs)
        engine = GameEngine(clone)
        player = clone.get_active_player()
        knight = next(c for c in player.hand if c.name == "Knight")
        engine.play_card(player, knight)
    elapsed_ms = (time.perf_counter() - start) / runs * 1000

    print(f"\nclone + play_card avg: {elapsed_ms:.3f} ms/iter over {runs} iters")
    assert elapsed_ms < 10.0, f"clone+transition too slow: {elapsed_ms:.3f} ms"
