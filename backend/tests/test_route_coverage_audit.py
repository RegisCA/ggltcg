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


def test_ai_turn_route_dispatches_tussle():
    """POST /ai-turn: the tussle dispatch branch (routes_actions.py:741-793) -
    only the play_card branch was previously exercised at the HTTP level.

    Knight attacking Paper Plane is the same deterministic, one-sided trade
    used by test_tussle_route_basic, so this isolates the /ai-turn route's
    own tussle dispatch/execution/victory-check logic from combat-math
    correctness (covered elsewhere).
    """
    import api.routes_actions as routes_actions
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

    class _FakeAIPlayer:
        """Picks the tussle action targeting Paper Plane from whatever
        ActionValidator actually produced, so the route's own dispatch runs
        unmodified against real validator output."""

        def select_action(self, game_state, player_id, valid_actions, game_engine=None):
            for i, action in enumerate(valid_actions):
                if action.action_type == "tussle" and action.card_id == knight.id:
                    return (i, "fake: tussle Paper Plane")
            raise AssertionError("expected a tussle action for Knight in valid_actions")

        def get_action_details(self, selected_action):
            return {
                "action_type": "tussle",
                "attacker_id": selected_action.card_id,
                "defender_id": paper_plane.id,
            }

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
    assert body["ai_turn_summary"]["action"] == "tussle"

    assert player1.charge == 0, f"Tussle should cost 2 Charge, player1.charge={player1.charge}"
    assert any(c.id == paper_plane.id for c in player2.break_zone), "Paper Plane should be broken"
    assert knight in player1.in_play, "Knight should survive the trade"


def test_ai_turn_route_dispatches_activate_ability():
    """POST /ai-turn: the activate_ability dispatch branch
    (routes_actions.py:815-944) - untested at the HTTP level until now.

    Mirrors test_activate_ability_route_spends_charge's Archer-targets-Ka
    setup (test_archer_issue_201.py), but through the AI dispatch path
    instead of the dedicated /activate-ability route.
    """
    import api.routes_actions as routes_actions
    from api.app import app

    archer = _load_card("Archer")
    archer.owner = "player1"
    archer.controller = "player1"
    archer.zone = Zone.IN_PLAY

    ka = _load_card("Ka")
    ka.owner = "player2"
    ka.controller = "player2"
    ka.zone = Zone.IN_PLAY

    player1 = Player(player_id="player1", name="Player 1", charge=5, hand=[], in_play=[archer])
    player2 = Player(player_id="player2", name="Player 2", charge=5, hand=[], in_play=[ka])

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
        """Picks the activate_ability action for Archer targeting Ka from
        whatever ActionValidator actually produced."""

        def select_action(self, game_state, player_id, valid_actions, game_engine=None):
            for i, action in enumerate(valid_actions):
                if action.action_type == "activate_ability" and action.card_id == archer.id:
                    return (i, "fake: activate Archer on Ka")
            raise AssertionError("expected an activate_ability action for Archer in valid_actions")

        def get_action_details(self, selected_action):
            return {
                "action_type": "activate_ability",
                "card_id": selected_action.card_id,
                "target_id": ka.id,
                "amount": 1,
            }

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
    assert body["ai_turn_summary"]["action"] == "activate_ability"
    assert player1.charge == 4, f"Archer's ability should cost 1 Charge, player1.charge={player1.charge}"


def test_ai_turn_route_falls_back_to_end_turn_when_ai_selects_none():
    """POST /ai-turn: the AI-failed-to-select fallback branch
    (routes_actions.py:505-556) - untested at the HTTP level until now.

    When select_action returns None (e.g. the LLM call failed entirely),
    the route must not 500 - it falls back to engine.end_turn() and reports
    a "pass" action.
    """
    import api.routes_actions as routes_actions
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

    class _FakeAIPlayer:
        """Simulates a total AI selection failure."""

        def select_action(self, game_state, player_id, valid_actions, game_engine=None):
            return None

        def get_endpoint_name(self):
            return "FakeAI"

        def get_last_decision_info(self):
            return {
                "model_name": "fake",
                "prompts_version": "fake",
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
    assert body["ai_turn_summary"]["action"] == "pass"

    assert game_state.turn_number == 2, "Fallback should end the turn"
    assert game_state.active_player_id == "player2", "Fallback should pass turn to the opponent"


def test_tussle_route_direct_attack():
    """POST /tussle with no defender_id: the direct-attack branch
    (routes_actions.py:161-170, defender stays None) - only the
    defender-provided happy path was previously exercised at the HTTP
    level.

    Opponent has no cards in play (direct attack legal) and exactly one
    card in hand, so the broken card is deterministic.
    """
    from api.app import app

    knight = _load_card("Knight")
    knight.owner = "player1"
    knight.controller = "player1"
    knight.zone = Zone.IN_PLAY

    opponent_hand_card = _load_card("Surge")
    opponent_hand_card.owner = "player2"
    opponent_hand_card.controller = "player2"
    opponent_hand_card.zone = Zone.HAND

    player1 = Player(player_id="player1", name="Player 1", charge=2, hand=[], in_play=[knight])
    player2 = Player(player_id="player2", name="Player 2", charge=2, hand=[opponent_hand_card], in_play=[])

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
            json={"player_id": "player1", "attacker_id": knight.id},
        )
    finally:
        service.use_database = original_use_database

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True

    assert player1.charge == 0, f"Direct attack should still cost 2 Charge, player1.charge={player1.charge}"
    assert opponent_hand_card not in player2.hand, "Direct attack should break the opponent's only hand card"
    assert any(c.id == opponent_hand_card.id for c in player2.break_zone)
    assert player1.direct_attacks_this_turn == 1


def test_tussle_route_victory_ends_game():
    """POST /tussle: the victory branch (routes_actions.py:206-219) returns
    a distinct response shape ({"winner": ...}, no "turn" key) that was
    never asserted on at the HTTP level - test_tussle_route_basic's
    opponent happened to have no other cards either, but didn't check this.

    Breaking Paper Plane, the opponent's only card anywhere, ends the game.
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
    player2 = Player(player_id="player2", name="Player 2", charge=2, hand=[], in_play=[paper_plane], break_zone=[])

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
    assert "wins" in body["message"]
    assert body["game_state"]["winner"] == "player1"
    assert "turn" not in body["game_state"], "Victory response shape has no 'turn' key"


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


def test_ai_turn_route_announces_plan_strategy_once_per_turn():
    """POST /ai-turn: the once-per-turn 'strategy' play-by-play entry (live
    opponent-turn playback, PR #369).

    The fake AI mirrors production reality: by the time the route reads
    get_last_decision_info(), select_action has already advanced the plan's
    current_action index past 0 (llm_player._advance_plan runs before
    returning). The original implementation guarded the announcement with
    `current_action == 0` and never fired — this test pins the behavior:
    the strategy lands exactly once across the turn's requests, before the
    first action entry.
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
        """Request 1 plays Surge, request 2 ends the turn — both report the
        same turn plan with current_action already advanced (as the real
        LLMPlayer does)."""

        def __init__(self):
            self.requests = 0

        def select_action(self, game_state, player_id, valid_actions, game_engine=None):
            self.requests += 1
            wanted = "play_card" if self.requests == 1 else "end_turn"
            for i, action in enumerate(valid_actions):
                if action.action_type == wanted and (wanted == "end_turn" or action.card_id == surge.id):
                    return (i, f"[plan] fake step {self.requests}")
            raise AssertionError(f"expected a {wanted} action in valid_actions")

        def get_action_details(self, selected_action):
            if selected_action.action_type == "end_turn":
                return {"action_type": "end_turn"}
            return {"action_type": "play_card", "card_id": selected_action.card_id, "target_ids": None}

        def get_endpoint_name(self):
            return "FakeAI"

        def get_last_decision_info(self):
            return {
                "model_name": "fake",
                "prompts_version": "fake",
                "action_number": self.requests,
                "reasoning": "fake",
                "prompt": "",
                "response": "",
                "plan": {
                    "planner": "enum",
                    "strategy": "Play Surge for Charge, then end the turn.",
                    "total_actions": 2,
                    # Mirrors llm_player: _advance_plan runs before
                    # select_action returns, so this is never 0 here
                    "current_action": self.requests,
                },
            }

    fake_ai = _FakeAIPlayer()
    original_get_ai_player = routes_actions.get_ai_player
    routes_actions.get_ai_player = lambda: fake_ai
    original_use_database = service.use_database
    service.use_database = False
    try:
        client = TestClient(app)
        r1 = client.post(f"/games/{game_state.game_id}/ai-turn", params={"player_id": "player1"})
        r2 = client.post(f"/games/{game_state.game_id}/ai-turn", params={"player_id": "player1"})
    finally:
        routes_actions.get_ai_player = original_get_ai_player
        service.use_database = original_use_database

    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text

    strategy_entries = [e for e in game_state.play_by_play if e.get("action_type") == "strategy"]
    assert len(strategy_entries) == 1, (
        f"Expected exactly one strategy announcement for the turn, got "
        f"{len(strategy_entries)}: {game_state.play_by_play}"
    )
    assert strategy_entries[0]["description"] == "Play Surge for Charge, then end the turn."
    assert strategy_entries[0]["turn"] == 1

    entry_types = [e.get("action_type") for e in game_state.play_by_play]
    assert entry_types.index("strategy") < entry_types.index("play_card"), (
        f"Strategy should be announced before the first action entry: {entry_types}"
    )
