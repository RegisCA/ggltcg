"""
Regression test for the game playback save in GameService._save_game_stats.

The GameModel lookup used to compare the UUID column against a raw string
(`GameModel.id == game_id`), which raises `'str' object has no attribute
'hex'` on SQLite (postgresql.UUID(as_uuid=True) bind processing). The
exception was swallowed by the surrounding try/except, so the playback row
was silently never written and game duration fell back to 0.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# Add backend/src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pathlib import Path as _Path

CARDS_CSV = str(_Path(__file__).parent.parent / "data" / "cards.csv")


def _make_completed_engine(svc, game_id_holder):
    """Create a game via the service and drive it to a win for player 1."""
    game_id, engine = svc.create_game(
        player1_id="109999999999999999999",
        player1_name="Regression Tester",
        player1_deck=svc.generate_random_full_deck(),
        player2_id="ai-gemiknight",
        player2_name="Gemiknight",
        player2_deck=svc.generate_random_full_deck(),
    )
    game_id_holder.append(game_id)
    gs = engine.game_state
    p2 = gs.players["ai-gemiknight"]
    for card in list(p2.hand) + list(p2.in_play):
        p2.break_card(card)
    winner = gs.check_victory()
    assert winner == "109999999999999999999"
    return game_id, engine


def test_playback_save_reads_game_row_on_sqlite():
    """The playback block must find the GameModel row (UUID-wrapped query)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from api.db_models import Base, GameModel
    from api.game_service import GameService

    db_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=db_engine)
    TestSession = sessionmaker(bind=db_engine)

    # Build the completed game without touching the real database
    svc = GameService(cards_csv_path=CARDS_CSV, use_database=False)
    holder = []
    game_id, engine = _make_completed_engine(svc, holder)

    # Seed the games row the playback block reads created_at from
    started_at = datetime.now(timezone.utc) - timedelta(seconds=90)
    seed = TestSession()
    seed.add(GameModel(
        id=uuid.UUID(game_id),
        player1_id="109999999999999999999",
        player1_name="Regression Tester",
        player2_id="ai-gemiknight",
        player2_name="Gemiknight",
        status="completed",
        winner_id="109999999999999999999",
        turn_number=engine.game_state.turn_number,
        active_player_id="109999999999999999999",
        phase="End",
        game_state={},
        created_at=started_at,
    ))
    seed.commit()
    seed.close()

    mock_stats = MagicMock()
    mock_stats.get_player_stats.return_value = None

    svc.use_database = True
    with patch("api.game_service.get_session_local", return_value=TestSession), \
         patch("api.game_service.SessionLocal", TestSession), \
         patch("api.game_service.get_stats_service", return_value=mock_stats):
        svc._save_game_stats(game_id, engine)

    # Before the fix, the string/UUID mismatch raised inside the playback
    # try-block, so record_game_playback was never reached
    mock_stats.record_game_playback.assert_called_once()
    kwargs = mock_stats.record_game_playback.call_args.kwargs
    assert kwargs["game_started_at"] is not None
    assert kwargs["game_started_at"].replace(tzinfo=timezone.utc) == started_at

    # And duration must be derived from created_at, not the 0 fallback
    duration = mock_stats.update_player_stats.call_args_list[0].kwargs[
        "game_duration_seconds"
    ]
    assert duration >= 90
