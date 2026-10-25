"""
Regression tests for end-of-game stats and game-state persistence.

- count_player_actions / _calculate_game_stats: play-by-play entries name the
  acting player by *name*, and tussles are logged as "X tussled Y (N Charge)".
  Stats used to compare names against player IDs and look for " tussles ",
  so every count was 0.
- serialization: turn_modifications and charge_history must survive a
  save/reload round trip.
- start_lobby_game: must reuse the lobby's games row, not insert a second one.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from conftest import create_game_with_cards
from game_engine.game_engine import GameEngine
from game_engine.models.game_state import TurnChargeRecord
from game_engine.validation import ActionExecutor, build_tussle_description
from api.game_service import GameService, count_player_actions
from api.serialization import serialize_game_state, deserialize_game_state

CSV_PATH = Path(__file__).parent.parent / "data" / "cards.csv"


def _finished_game():
    setup, _ = create_game_with_cards(
        player1_in_play=["Ka"],
        player2_in_play=["Knight"],
        turn_number=3,
        active_player="player1",
    )
    gs = setup.game_state
    p1, p2 = gs.players["player1"], gs.players["player2"]
    p1.name, p2.name = "Alice", "Gemiknight"

    gs.add_play_by_play(p1.name, "play_card", "Played Surge (0 Charge)")
    gs.add_play_by_play(p1.name, "play_card", "Played Ballaber (broke Ka for cost)")
    gs.add_play_by_play(p1.name, "tussle", build_tussle_description(2, "Ka", defender_label="Knight"))
    gs.add_play_by_play(p1.name, "tussle", build_tussle_description(2, "Ka", broken_from_hand="Wake"))
    gs.add_play_by_play(p1.name, "tussle", build_tussle_description(2, "Ka"))
    gs.add_play_by_play(p2.name, "play_card", "Played Wake, returned Knight to hand (1 Charge)")
    gs.add_play_by_play(p2.name, "tussle", build_tussle_description(1, "Knight", defender_label="Ka"))
    gs.add_play_by_play(p2.name, "end_turn", "Ended turn")
    gs.add_play_by_play(p1.name, "victory", "Alice wins! All opponent's cards are broken.")
    gs.winner_id = "player1"
    return GameEngine(gs)


def test_count_player_actions_maps_names_to_ids():
    engine = _finished_game()
    counts = count_player_actions(engine.game_state)
    assert counts["player1"] == {"cards_played": 2, "tussles": 1, "direct_attacks": 2}
    assert counts["player2"] == {"cards_played": 1, "tussles": 1, "direct_attacks": 0}


def test_count_player_actions_from_real_executor_descriptions():
    """Descriptions produced by ActionExecutor are what gets counted."""
    setup, cards = create_game_with_cards(
        player1_hand=["Surge"],
        player1_in_play=["Ka"],
        player2_hand=["Wake"],
        turn_number=3,
        active_player="player1",
        player1_charge=5,
    )
    gs = setup.game_state
    engine = setup.engine
    executor = ActionExecutor(engine)
    p1 = gs.players["player1"]

    surge = next(c for c in p1.hand if c.name == "Surge")
    result = executor.execute_play_card("player1", surge.id)
    gs.add_play_by_play(p1.name, "play_card", result.description)

    ka = next(c for c in p1.in_play if c.name == "Ka")
    result = executor.execute_tussle("player1", ka.id)  # direct attack
    assert result.success
    gs.add_play_by_play(p1.name, "tussle", result.description)

    counts = count_player_actions(gs)
    assert counts["player1"]["cards_played"] == 1
    assert counts["player1"]["direct_attacks"] == 1
    assert counts["player1"]["tussles"] == 0


def test_calculate_game_stats_nonzero():
    engine = _finished_game()
    service = GameService(cards_csv_path=str(CSV_PATH), use_database=False)
    stats = service._calculate_game_stats(str(uuid.uuid4()), engine)
    assert stats["winner_id"] == "Alice"
    assert stats["loser_id"] == "Gemiknight"
    assert stats["winner_cards_played"] == 2
    assert stats["winner_tussles_initiated"] == 1
    assert stats["winner_direct_attacks"] == 2
    assert stats["loser_cards_played"] == 1
    assert stats["loser_tussles_initiated"] == 1
    assert stats["loser_direct_attacks"] == 0


def test_serialization_round_trips_turn_modifications_and_charge_history():
    setup, _ = create_game_with_cards(
        player1_in_play=["Ka"],
        turn_number=3,
        active_player="player1",
    )
    gs = setup.game_state
    ka = gs.players["player1"].in_play[0]
    ka.add_turn_modification(3, "strength", 2)
    gs.charge_history.append(TurnChargeRecord(
        turn=1, player_id="player1", charge_start=0, charge_gained=4,
        charge_spent=3, charge_end=1,
    ))
    gs._turn_charge_snapshot = 5
    gs._turn_charge_gained = 2

    restored = deserialize_game_state(serialize_game_state(gs))

    restored_ka = restored.find_card_by_id(ka.id)
    assert restored_ka.get_turn_modification("strength", 3) == 2
    assert [r.to_dict() for r in restored.charge_history] == [r.to_dict() for r in gs.charge_history]
    assert restored._turn_charge_snapshot == 5
    assert restored._turn_charge_gained == 2


@pytest.fixture
def sqlite_service(monkeypatch):
    """GameService backed by a throwaway in-memory SQLite DB with tables."""
    import api.game_service as game_service_module
    from api.db_models import Base

    db_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(db_engine)
    session_factory = sessionmaker(bind=db_engine)
    monkeypatch.setattr(game_service_module, "SessionLocal", session_factory)
    monkeypatch.setattr(game_service_module, "get_session_local", lambda: session_factory)

    service = GameService(cards_csv_path=str(CSV_PATH), use_database=True)
    return service, session_factory


def test_start_lobby_game_reuses_lobby_row(sqlite_service):
    from api.db_models import GameModel

    service, session_factory = sqlite_service
    game_id, code = service.create_lobby("google-alice", "Alice")
    service.join_lobby(code, "google-bob", "Bob")

    deck = ["Ka", "Knight", "Wizard", "Beary", "Surge", "Wake"]
    first = service.start_lobby_game(code, "google-alice", deck)
    assert first["ready"] is False
    result = service.start_lobby_game(code, "google-bob", deck)
    assert result["ready"] is True
    assert result["game_id"] == game_id

    db = session_factory()
    try:
        rows = db.query(GameModel).all()
        assert len(rows) == 1
        assert str(rows[0].id) == game_id
        assert rows[0].status == "active"
        assert rows[0].game_state["game_id"] == game_id
    finally:
        db.close()

    engine = service.get_game(game_id)
    assert engine.game_state.game_id == game_id
