"""
Access rules for game-scoped endpoints outside /admin.

- GET /games/{id}/ai-plan-summary: public, but only once the game is over,
  and only plan summaries (no prompts/responses). The victory screen used to
  call the admin-only /admin/ai-logs, which fails for normal players.
- GET /games/{id}/debug and /logs: admin only (/debug returns both hands).
- /maintenance/*: fails closed when MAINTENANCE_API_KEY is unset (there used
  to be a hardcoded fallback key).
"""

import os
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_for_ci")

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from conftest import create_game_with_cards


@pytest.fixture
def client_with_game(monkeypatch):
    """TestClient plus a cached, DB-less game the test can finish."""
    from api.app import app
    from api.game_service import get_game_service

    setup, _ = create_game_with_cards(
        player1_in_play=["Ka"],
        turn_number=3,
        active_player="player1",
    )
    service = get_game_service()
    monkeypatch.setattr(service, "use_database", False)
    monkeypatch.setitem(service._cache, setup.game_state.game_id, setup.engine)
    return TestClient(app), setup.game_state


def test_ai_plan_summary_unknown_game(client_with_game, monkeypatch):
    client, _ = client_with_game
    from api.game_service import get_game_service
    monkeypatch.setattr(get_game_service(), "get_game", lambda game_id: None)

    assert client.get(f"/games/{uuid.uuid4()}/ai-plan-summary").status_code == 404


def test_ai_plan_summary_refused_mid_game(client_with_game):
    client, gs = client_with_game

    response = client.get(f"/games/{gs.game_id}/ai-plan-summary")

    assert response.status_code == 409


def test_ai_plan_summary_after_game_over(client_with_game, monkeypatch):
    client, gs = client_with_game
    gs.winner_id = "player1"
    from api import routes_games

    class _Stats:
        def get_ai_plan_summaries(self, game_id):
            assert game_id == gs.game_id
            return [{"turn_number": 2, "player_id": "player2"}]

    monkeypatch.setattr(routes_games, "get_stats_service", lambda: _Stats())

    response = client.get(f"/games/{gs.game_id}/ai-plan-summary")

    assert response.status_code == 200
    assert response.json() == {"count": 1, "logs": [{"turn_number": 2, "player_id": "player2"}]}


def test_get_ai_plan_summaries_omits_prompt_and_response(monkeypatch):
    import api.database as database_module
    from api.db_models import Base, AIDecisionLogModel
    from api.stats_service import StatsService

    db_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(db_engine)
    session_factory = sessionmaker(bind=db_engine)
    monkeypatch.setattr(database_module, "SessionLocal", session_factory)

    game_id = str(uuid.uuid4())
    other_game_id = str(uuid.uuid4())
    t0 = datetime(2026, 10, 25, tzinfo=timezone.utc)
    db = session_factory()
    for gid, turn, minutes in ((game_id, 4, 2), (game_id, 2, 1), (other_game_id, 2, 0)):
        db.add(AIDecisionLogModel(
            game_id=uuid.UUID(gid), turn_number=turn, player_id="ai-gemiknight",
            model_name="gemini", prompts_version="1", prompt="SECRET PROMPT",
            response="SECRET RESPONSE",
            turn_plan={"planner": "enum", "strategy": f"turn {turn}", "action_sequence": []},
            plan_execution_status="complete", created_at=t0 + timedelta(minutes=minutes),
        ))
    db.commit()
    db.close()

    summaries = StatsService(use_database=True).get_ai_plan_summaries(game_id)

    assert [s["turn_number"] for s in summaries] == [2, 4]
    assert summaries[0]["turn_plan"] == {"strategy": "turn 2", "planner": "enum"}
    assert "SECRET" not in repr(summaries)


@pytest.mark.parametrize("path", ["debug", "logs"])
def test_debug_endpoints_require_admin(client_with_game, path):
    client, gs = client_with_game

    response = client.get(f"/games/{gs.game_id}/{path}")

    assert response.status_code == 401


def test_debug_endpoint_works_for_admin(client_with_game):
    from api.app import app
    from api.admin_auth import get_current_admin_user

    client, gs = client_with_game
    app.dependency_overrides[get_current_admin_user] = lambda: "admin-google-id"
    try:
        response = client.get(f"/games/{gs.game_id}/debug")
    finally:
        app.dependency_overrides.pop(get_current_admin_user, None)

    assert response.status_code == 200


class TestMaintenanceApiKey:
    def test_unset_key_fails_closed(self, monkeypatch):
        from api.routes_maintenance import verify_api_key
        monkeypatch.delenv("MAINTENANCE_API_KEY", raising=False)

        for supplied in (None, "dev-maintenance-key", ""):
            with pytest.raises(HTTPException) as exc:
                verify_api_key(supplied)
            assert exc.value.status_code == 503

    def test_wrong_and_missing_key(self, monkeypatch):
        from api.routes_maintenance import verify_api_key
        monkeypatch.setenv("MAINTENANCE_API_KEY", "s3cret")

        with pytest.raises(HTTPException) as exc:
            verify_api_key(None)
        assert exc.value.status_code == 401
        with pytest.raises(HTTPException) as exc:
            verify_api_key("dev-maintenance-key")
        assert exc.value.status_code == 403

    def test_correct_key(self, monkeypatch):
        from api.routes_maintenance import verify_api_key
        monkeypatch.setenv("MAINTENANCE_API_KEY", "s3cret")

        assert verify_api_key("s3cret") is True
