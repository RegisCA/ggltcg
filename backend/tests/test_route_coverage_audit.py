"""
HTTP-level regression tests for routes_actions.py / routes_games.py.

Audit (docs/plans/TEST_SUITE_AUDIT_REPORT.md, 2026-06-28) found that most
action routes are exercised only at the engine/validator layer — never
through the actual FastAPI route handler. That's exactly how a renamed
`spend_cc` -> `spend_charge` call sat undetected in `/activate-ability` for
two weeks (see test_archer_issue_201.py::test_activate_ability_route_spends_charge,
the template this file follows). These tests close the highest-priority
gaps identified by that audit: /play-card, /tussle, /ai-turn dispatch, and
GET /{game_id} hand-visibility.
"""

import sys
import uuid
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from fastapi.testclient import TestClient

from game_engine.game_engine import GameEngine
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Zone
from game_engine.data.card_loader import CardLoader

CSV_PATH = Path(__file__).parent.parent / "data" / "cards.csv"


def _load_card(name: str):
    loader = CardLoader(str(CSV_PATH))
    all_cards = loader.load_cards()
    return next(c for c in all_cards if c.name == name)


def _client_for(engine: GameEngine):
    """Inject a prepared engine into the service cache, bypassing a real
    POST /games (and its DB row), mirroring test_archer_issue_201.py."""
    from api.game_service import get_game_service

    service = get_game_service()
    service._cache[engine.game_state.game_id] = engine
    return service


def test_play_card_route_basic():
    """POST /play-card: happy path through the real route handler.

    Surge is a 0-cost action card that grants +1 Charge and goes to the
    break zone on play - a deterministic, target-free effect that lets
    this test isolate the route's own logic (player/turn checks,
    ActionExecutor call, play-by-play log, DB-save call) from effect
    correctness (already covered elsewhere).
    """
    from api.app import app

    surge = _load_card("Surge")
    surge.owner = "player1"
    surge.controller = "player1"
    surge.zone = Zone.HAND

    player1 = Player(player_id="player1", name="Player 1", charge=2, hand=[surge], in_play=[])
    player2 = Player(player_id="player2", name="Player 2", charge=2, hand=[], in_play=[])

    game_state = GameState(
        game_id=str(uuid.uuid4()),
        players={"player1": player1, "player2": player2},
        turn_number=1,
        phase=Phase.MAIN,
        active_player_id="player1",
        first_player_id="player1",
    )
    engine = GameEngine(game_state)
    service = _client_for(engine)

    original_use_database = service.use_database
    service.use_database = False
    try:
        client = TestClient(app)
        response = client.post(
            f"/games/{game_state.game_id}/play-card",
            json={"player_id": "player1", "card_id": surge.id},
        )
    finally:
        service.use_database = original_use_database

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True

    assert player1.charge == 3, f"Surge should grant +1 Charge, player1.charge={player1.charge}"
    assert surge not in player1.hand, "Surge should leave hand after being played"
    assert any(c.id == surge.id for c in player1.break_zone), "Surge should land in the break zone"
    assert game_state.play_by_play, "Route should log the play to play-by-play"


def test_play_card_route_invalid_card_returns_400():
    """POST /play-card with a card_id not in hand: route-layer status-code
    mapping (ValueError -> 400) is otherwise untested at the HTTP level."""
    from api.app import app

    player1 = Player(player_id="player1", name="Player 1", charge=2, hand=[], in_play=[])
    player2 = Player(player_id="player2", name="Player 2", charge=2, hand=[], in_play=[])

    game_state = GameState(
        game_id=str(uuid.uuid4()),
        players={"player1": player1, "player2": player2},
        turn_number=1,
        phase=Phase.MAIN,
        active_player_id="player1",
        first_player_id="player1",
    )
    engine = GameEngine(game_state)
    service = _client_for(engine)

    original_use_database = service.use_database
    service.use_database = False
    try:
        client = TestClient(app)
        response = client.post(
            f"/games/{game_state.game_id}/play-card",
            json={"player_id": "player1", "card_id": "not-a-real-card-id"},
        )
    finally:
        service.use_database = original_use_database

    assert response.status_code == 400, response.text


def test_tussle_route_basic():
    """POST /tussle: happy path through the real route handler.

    Knight (4 STR / 3 STA) attacking Paper Plane (2 STR / 1 STA) is a
    deterministic, one-sided trade: Paper Plane breaks, Knight survives
    with 1 STA remaining. Exercises the route's own cost calculation,
    state-based-action check, and play-by-play log.
    """
    from api.app import app

    knight = _load_card("Knight")
    knight.owner = "player1"
    knight.controller = "player1"
    knight.zone = Zone.IN_PLAY

    paper_plane = _load_card("Paper Plane")
    paper_plane.owner = "player2"
    paper_plane.controller = "player2"
    paper_plane.zone = Zone.IN_PLAY

    player1 = Player(player_id="player1", name="Player 1", charge=2, hand=[], in_play=[knight])
    player2 = Player(player_id="player2", name="Player 2", charge=2, hand=[], in_play=[paper_plane])

    game_state = GameState(
        game_id=str(uuid.uuid4()),
        players={"player1": player1, "player2": player2},
        turn_number=3,
        phase=Phase.MAIN,
        active_player_id="player1",
        first_player_id="player1",
    )
    engine = GameEngine(game_state)
    service = _client_for(engine)

    original_use_database = service.use_database
    service.use_database = False
    try:
        client = TestClient(app)
        response = client.post(
            f"/games/{game_state.game_id}/tussle",
            json={"player_id": "player1", "attacker_id": knight.id, "defender_id": paper_plane.id},
        )
    finally:
        service.use_database = original_use_database

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True

    assert player1.charge == 0, f"Tussle should cost 2 Charge, player1.charge={player1.charge}"
    assert any(c.id == paper_plane.id for c in player2.break_zone), "Paper Plane should be broken"
    assert knight in player1.in_play, "Knight should survive the trade"
    assert game_state.play_by_play, "Route should log the tussle to play-by-play"


def test_ai_turn_route_dispatches_play_card():
    """POST /ai-turn: route's dispatch-by-action-type logic, with the real
    LLM call stubbed out.

    All other AI tests exercise TurnPlanner/LLMPlayer directly; none go
    through this route, which owns its own 500+ line dispatch (end_turn /
    play_card / tussle / activate_ability) with its own ActionExecutor
    calls, play-by-play logging, and error mapping. This pins the
    play_card branch — the richest of the four — against the real route.
    """
    import api.routes_actions as routes_actions
    from api.app import app

    surge = _load_card("Surge")
    surge.owner = "player1"
    surge.controller = "player1"
    surge.zone = Zone.HAND

    player1 = Player(player_id="player1", name="Player 1", charge=2, hand=[surge], in_play=[])
    player2 = Player(player_id="player2", name="Player 2", charge=2, hand=[], in_play=[])

    game_state = GameState(
        game_id=str(uuid.uuid4()),
        players={"player1": player1, "player2": player2},
        turn_number=1,
        phase=Phase.MAIN,
        active_player_id="player1",
        first_player_id="player1",
    )
    engine = GameEngine(game_state)
    service = _client_for(engine)

    class _FakeAIPlayer:
        """Stubs the LLM call: picks the play_card action for Surge from
        whatever ActionValidator actually produced, so the route's own
        dispatch/execution logic runs unmodified against real validator
        output."""

        def select_action(self, game_state, player_id, valid_actions, game_engine=None):
            for i, action in enumerate(valid_actions):
                if action.action_type == "play_card" and action.card_id == surge.id:
                    return (i, "fake: play Surge")
            raise AssertionError("expected a play_card action for Surge in valid_actions")

        def get_action_details(self, selected_action):
            return {"action_type": "play_card", "card_id": selected_action.card_id, "target_ids": None}

        def get_endpoint_name(self):
            return "FakeAI"

        def get_last_decision_info(self):
            return {
                "model_name": "fake",
                "prompts_version": "fake",
                "action_number": 1,
                "reasoning": "fake",
                "prompt": "",
                "response": "",
                "plan": None,
            }

    original_get_ai_player = routes_actions.get_ai_player
    routes_actions.get_ai_player = lambda: _FakeAIPlayer()
    original_use_database = service.use_database
    service.use_database = False
    try:
        client = TestClient(app)
        response = client.post(f"/games/{game_state.game_id}/ai-turn", params={"player_id": "player1"})
    finally:
        routes_actions.get_ai_player = original_get_ai_player
        service.use_database = original_use_database

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["ai_turn_summary"]["action"] == "play_card"

    assert player1.charge == 3, f"Surge should grant +1 Charge, player1.charge={player1.charge}"
    assert surge not in player1.hand
    assert game_state.play_by_play, "Route should log the AI's play to play-by-play"


def test_get_game_state_hides_opponent_hand_and_applies_stat_buffs():
    """GET /{game_id}: hand-visibility-by-player_id and continuous-effect
    stat buffs are computed in the route handler itself (_card_to_state),
    not the engine - and were untested at the HTTP level.

    Ka's stat_boost effect (+2 strength to itself while in play) is a
    convenient deterministic buff to check the route actually applies
    engine.get_card_stat() rather than just echoing base card stats.
    """
    from api.app import app

    knight = _load_card("Knight")
    knight.owner = "player1"
    knight.controller = "player1"
    knight.zone = Zone.HAND

    ka = _load_card("Ka")
    ka.owner = "player1"
    ka.controller = "player1"
    ka.zone = Zone.IN_PLAY
    ka_base_strength = ka.strength

    opponent_secret = _load_card("Surge")
    opponent_secret.owner = "player2"
    opponent_secret.controller = "player2"
    opponent_secret.zone = Zone.HAND

    player1 = Player(player_id="player1", name="Player 1", charge=2, hand=[knight], in_play=[ka])
    player2 = Player(player_id="player2", name="Player 2", charge=2, hand=[opponent_secret], in_play=[])

    game_state = GameState(
        game_id=str(uuid.uuid4()),
        players={"player1": player1, "player2": player2},
        turn_number=1,
        phase=Phase.MAIN,
        active_player_id="player1",
        first_player_id="player1",
    )
    engine = GameEngine(game_state)
    _client_for(engine)

    client = TestClient(app)
    response = client.get(f"/games/{game_state.game_id}", params={"player_id": "player1"})

    assert response.status_code == 200, response.text
    body = response.json()

    p1_state = body["players"]["player1"]
    p2_state = body["players"]["player2"]

    assert p1_state["hand"] is not None and len(p1_state["hand"]) == 1, \
        "Requesting player's own hand should be visible"
    assert p2_state["hand"] is None, "Opponent's hand should be hidden"
    assert p2_state["hand_count"] == 1, "Opponent's hand_count should still be reported"

    ka_state = next(c for c in p1_state["in_play"] if c["id"] == ka.id)
    assert ka_state["strength"] == ka_base_strength + 2, (
        f"Route should report Ka's buffed strength via engine.get_card_stat(), "
        f"got {ka_state['strength']} (base {ka_base_strength})"
    )
    assert ka_state["base_strength"] == ka_base_strength, "base_strength should remain unbuffed"
