"""
Regression tests for play paths that bypassed engine logic.

- Ballaber's alternative cost: the played Toy must get a controller and fire
  when-other-card-played triggers (Hind Leg Kicker), like any normal play.
- Activated abilities (Archer): every caller goes through
  ActionExecutor.execute_activate_ability, which validates the target.
- /tussle and /activate-ability: the victory play-by-play entry must be in
  the state that gets saved (it was appended after update_game).
- Copy/Clone: a transformed Clone reverts to Clone, not Copy; a Copy of
  Umbruh still fires Umbruh's when-broken trigger.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from fastapi.testclient import TestClient

from conftest import create_game_with_cards, steal_card
from game_engine.validation import ActionExecutor
from api.serialization import serialize_card, deserialize_card


def _card(zone_cards, name):
    return next(c for c in zone_cards if c.name == name)


# ---------------------------------------------------------------------------
# Ballaber alternative cost
# ---------------------------------------------------------------------------

def test_ballaber_alternative_cost_runs_play_triggers():
    setup, _ = create_game_with_cards(
        player1_hand=["Ballaber"],
        player1_in_play=["Hind Leg Kicker", "Ka"],
        turn_number=3,
        active_player="player1",
        player1_charge=0,
    )
    p1 = setup.game_state.players["player1"]
    ballaber = _card(p1.hand, "Ballaber")
    ka = _card(p1.in_play, "Ka")

    result = ActionExecutor(setup.engine).execute_play_card(
        "player1", ballaber.id, alternative_cost_card_id=ka.id
    )

    assert result.success
    assert ballaber in p1.in_play
    assert ballaber.controller == "player1"
    assert ka in p1.break_zone
    assert p1.charge == 1  # Hind Leg Kicker: +1 for playing another card
    assert result.description == "Played Ballaber (broke Ka for cost)"


def test_ballaber_cannot_break_itself_for_its_cost():
    setup, _ = create_game_with_cards(
        player1_hand=["Ballaber"],
        turn_number=3,
        active_player="player1",
        player1_charge=0,
    )
    p1 = setup.game_state.players["player1"]
    ballaber = _card(p1.hand, "Ballaber")

    with pytest.raises(ValueError):
        ActionExecutor(setup.engine).execute_play_card(
            "player1", ballaber.id, alternative_cost_card_id=ballaber.id
        )
    assert ballaber in p1.hand


# ---------------------------------------------------------------------------
# Activated abilities
# ---------------------------------------------------------------------------

def _archer_game():
    setup, _ = create_game_with_cards(
        player1_in_play=["Archer", "Ka"],
        player2_in_play=["Beary", "Umbruh"],
        turn_number=3,
        active_player="player1",
        player1_charge=5,
    )
    gs = setup.game_state
    p1, p2 = gs.players["player1"], gs.players["player2"]
    return setup, p1, p2


def test_activate_ability_rejects_protected_target():
    setup, p1, p2 = _archer_game()
    archer, beary = _card(p1.in_play, "Archer"), _card(p2.in_play, "Beary")

    with pytest.raises(ValueError, match="Invalid target"):
        ActionExecutor(setup.engine).execute_activate_ability("player1", archer.id, target_id=beary.id)
    assert p1.charge == 5


def test_activate_ability_valid_target_with_amount():
    setup, p1, p2 = _archer_game()
    archer, umbruh = _card(p1.in_play, "Archer"), _card(p2.in_play, "Umbruh")

    result = ActionExecutor(setup.engine).execute_activate_ability(
        "player1", archer.id, target_id=umbruh.id, amount=2
    )

    assert result.success
    assert result.cost == 2
    assert p1.charge == 3
    assert umbruh.current_stamina == umbruh.stamina - 2
    assert result.description == "Archer used its ability on Umbruh (amount 2)"


def _route_client(setup, monkeypatch):
    """Serve the prepared engine through the real routes; record what
    update_game would have saved."""
    from api.app import app
    from api.game_service import get_game_service

    service = get_game_service()
    service._cache[setup.game_state.game_id] = setup.engine
    monkeypatch.setattr(service, "use_database", False)

    saved = []
    monkeypatch.setattr(
        service, "update_game",
        lambda game_id, engine: saved.append([e["action_type"] for e in engine.game_state.play_by_play]),
    )
    return TestClient(app), saved


def test_activate_ability_route_rejects_invalid_target(monkeypatch):
    setup, p1, p2 = _archer_game()
    archer, beary = _card(p1.in_play, "Archer"), _card(p2.in_play, "Beary")
    client, saved = _route_client(setup, monkeypatch)

    response = client.post(
        f"/games/{setup.game_state.game_id}/activate-ability",
        json={"player_id": "player1", "card_id": archer.id, "target_id": beary.id, "amount": 1},
    )

    assert response.status_code == 400
    assert p1.charge == 5
    assert saved == []


def test_activate_ability_route_saves_victory_entry(monkeypatch):
    setup, _ = create_game_with_cards(
        player1_in_play=["Archer"],
        player2_in_play=["Hind Leg Kicker"],
        turn_number=3,
        active_player="player1",
        player1_charge=5,
    )
    gs = setup.game_state
    archer = _card(gs.players["player1"].in_play, "Archer")
    hlk = _card(gs.players["player2"].in_play, "Hind Leg Kicker")
    client, saved = _route_client(setup, monkeypatch)

    response = client.post(
        f"/games/{gs.game_id}/activate-ability",
        json={"player_id": "player1", "card_id": archer.id, "target_id": hlk.id, "amount": 1},
    )

    assert response.status_code == 200, response.text
    assert response.json()["game_state"]["winner"] == "player1"
    assert saved[-1][-2:] == ["activate_ability", "victory"]


def test_tussle_route_saves_victory_entry(monkeypatch):
    setup, _ = create_game_with_cards(
        player1_in_play=["Knight"],
        player2_in_play=["Hind Leg Kicker"],
        turn_number=3,
        active_player="player1",
        player1_charge=5,
    )
    gs = setup.game_state
    knight = _card(gs.players["player1"].in_play, "Knight")
    hlk = _card(gs.players["player2"].in_play, "Hind Leg Kicker")
    client, saved = _route_client(setup, monkeypatch)

    response = client.post(
        f"/games/{gs.game_id}/tussle",
        json={"player_id": "player1", "attacker_id": knight.id, "defender_id": hlk.id},
    )

    assert response.status_code == 200, response.text
    assert response.json()["game_state"]["winner"] == "player1"
    assert saved[-1][-2:] == ["tussle", "victory"]


# ---------------------------------------------------------------------------
# Copy / Clone
# ---------------------------------------------------------------------------

def _play_copy_of(card_name, copy_name, extra_p2=None):
    setup, _ = create_game_with_cards(
        player1_hand=[copy_name],
        player1_in_play=[card_name],
        player2_in_play=extra_p2,
        turn_number=3,
        active_player="player1",
        player1_charge=5,  # below the Charge cap, so gains are observable
    )
    p1 = setup.game_state.players["player1"]
    copy_card = _card(p1.hand, copy_name)
    target = _card(p1.in_play, card_name)
    result = ActionExecutor(setup.engine).execute_play_card(
        "player1", copy_card.id, target_card_id=target.id
    )
    assert result.success
    assert copy_card.name == f"Copy of {card_name}"
    return setup, p1, copy_card


def test_clone_reverts_to_clone_when_broken():
    setup, p1, clone = _play_copy_of("Ka", "Clone")

    setup.engine._break_card(clone, p1, was_in_play=True)

    assert clone in p1.break_zone
    assert clone.name == "Clone"
    assert clone.cost == 2


def test_clone_reverts_to_clone_after_reload():
    setup, p1, clone = _play_copy_of("Ka", "Clone")

    restored = deserialize_card(serialize_card(clone))
    restored.reset_modifications()

    assert restored.name == "Clone"


def test_copy_still_reverts_to_copy():
    setup, p1, copy_card = _play_copy_of("Ka", "Copy")

    setup.engine._break_card(copy_card, p1, was_in_play=True)

    assert copy_card.name == "Copy"


def test_copy_of_umbruh_fires_when_broken_trigger():
    setup, p1, copy_card = _play_copy_of("Umbruh", "Copy")
    charge_before = p1.charge

    setup.engine._break_card(copy_card, p1, was_in_play=True)

    assert copy_card.name == "Copy"
    assert p1.charge == charge_before + 1


def test_stolen_copy_reverts_when_broken():
    setup, p1, copy_card = _play_copy_of("Ka", "Copy")
    p2 = setup.game_state.players["player2"]
    steal_card(setup.game_state, copy_card, "player2")

    setup.engine._break_card(copy_card, p1, was_in_play=True)

    assert copy_card in p1.break_zone
    assert copy_card not in p2.in_play
    assert copy_card.name == "Copy"
    assert copy_card.controller == "player1"


# ---------------------------------------------------------------------------
# Review follow-ups
# ---------------------------------------------------------------------------

def test_validator_does_not_offer_ballaber_as_its_own_alt_cost():
    """If Ballaber were offered, the AI (or llm_player's first-option
    fallback) could pick it, the executor would reject it, and /ai-turn
    would 500."""
    from game_engine.validation import ActionValidator

    setup, _ = create_game_with_cards(
        player1_hand=["Ballaber"],
        turn_number=3,
        active_player="player1",
        player1_charge=0,
    )
    actions = ActionValidator(setup.engine).get_valid_actions("player1")

    assert not any(a.card_name == "Ballaber" for a in actions if a.action_type == "play_card")


def test_validator_offers_other_cards_as_ballaber_alt_cost():
    from game_engine.validation import ActionValidator

    setup, _ = create_game_with_cards(
        player1_hand=["Ballaber", "Wake"],
        player1_in_play=["Ka"],
        turn_number=3,
        active_player="player1",
        player1_charge=0,
    )
    p1 = setup.game_state.players["player1"]
    ballaber = _card(p1.hand, "Ballaber")
    action = next(
        a for a in ActionValidator(setup.engine).get_valid_actions("player1")
        if a.action_type == "play_card" and a.card_id == ballaber.id
    )

    assert set(action.alternative_cost_options) == {c.id for c in p1.hand + p1.in_play} - {ballaber.id}


def test_play_card_has_no_free_play_flag():
    """Only a card actually broken waives the Charge cost; a caller can't
    claim the alternative cost was already paid."""
    setup, _ = create_game_with_cards(
        player1_hand=["Ballaber"],
        player1_in_play=["Ka"],
        turn_number=3,
        active_player="player1",
        player1_charge=2,
    )
    p1 = setup.game_state.players["player1"]
    ballaber = _card(p1.hand, "Ballaber")

    played = setup.engine.play_card(
        p1, ballaber, alternative_cost_paid=True, alternative_cost_card="Ka"
    )

    assert played is False  # Ballaber costs 3; no card broken, so Charge is due
    assert ballaber in p1.hand
    assert p1.charge == 2
    assert len(p1.in_play) == 1


def test_activate_ability_rejects_target_in_hand():
    setup, _ = create_game_with_cards(
        player1_in_play=["Archer"],
        player2_hand=["Umbruh"],
        turn_number=3,
        active_player="player1",
        player1_charge=5,
    )
    gs = setup.game_state
    archer = _card(gs.players["player1"].in_play, "Archer")
    umbruh = _card(gs.players["player2"].hand, "Umbruh")

    from game_engine.validation import CardNotFoundError
    with pytest.raises(CardNotFoundError):
        ActionExecutor(setup.engine).execute_activate_ability("player1", archer.id, target_id=umbruh.id)
    assert gs.players["player1"].charge == 5


def test_activate_ability_rejects_target_for_untargeted_ability(monkeypatch):
    from game_engine.rules.effects.action_effects import ArcherActivatedAbility

    setup, p1, p2 = _archer_game()
    archer, umbruh = _card(p1.in_play, "Archer"), _card(p2.in_play, "Umbruh")
    monkeypatch.setattr(ArcherActivatedAbility, "requires_targets", lambda self: False)

    with pytest.raises(ValueError, match="doesn't take a target"):
        ActionExecutor(setup.engine).execute_activate_ability("player1", archer.id, target_id=umbruh.id)
    assert p1.charge == 5


@pytest.mark.parametrize("missing", ["card", "target"])
def test_activate_ability_route_not_found_is_404(monkeypatch, missing):
    setup, p1, p2 = _archer_game()
    archer, umbruh = _card(p1.in_play, "Archer"), _card(p2.in_play, "Umbruh")
    client, saved = _route_client(setup, monkeypatch)
    body = {"player_id": "player1", "card_id": archer.id, "target_id": umbruh.id, "amount": 1}
    body["card_id" if missing == "card" else "target_id"] = "no-such-card"

    response = client.post(f"/games/{setup.game_state.game_id}/activate-ability", json=body)

    assert response.status_code == 404
    assert saved == []


class _FakeActivateAI:
    """Stub for /ai-turn: always activates Archer with the given target and
    records what the route reports via record_execution_result."""

    def __init__(self, archer_id, target_id):
        self.archer_id = archer_id
        self.target_id = target_id
        self.results = []

    def select_action(self, game_state, player_id, valid_actions, game_engine=None):
        for i, action in enumerate(valid_actions):
            if action.action_type == "activate_ability":
                return (i, "fake")
        raise AssertionError("expected an activate_ability action")

    def get_action_details(self, selected_action):
        return {"action_type": "activate_ability", "card_id": self.archer_id,
                "target_id": self.target_id, "amount": 1}

    def get_endpoint_name(self):
        return "FakeAI"

    def get_last_decision_info(self):
        return {"model_name": "fake", "prompts_version": "fake", "action_number": 1,
                "reasoning": "fake", "prompt": "", "response": "", "plan": None}

    def record_execution_result(self, success, error_message=None):
        self.results.append((success, error_message))


def _ai_turn(setup, monkeypatch, fake_ai):
    import api.routes_actions as routes_actions

    client, saved = _route_client(setup, monkeypatch)
    monkeypatch.setattr(routes_actions, "get_ai_player", lambda game_id=None: fake_ai)
    response = client.post(f"/games/{setup.game_state.game_id}/ai-turn", params={"player_id": "player1"})
    return response, saved


def test_ai_turn_activate_invalid_target_is_recorded(monkeypatch):
    setup, p1, p2 = _archer_game()
    archer, beary = _card(p1.in_play, "Archer"), _card(p2.in_play, "Beary")
    fake_ai = _FakeActivateAI(archer.id, beary.id)  # protected: not a valid target

    response, saved = _ai_turn(setup, monkeypatch, fake_ai)

    assert response.status_code == 500
    assert "AI activate_ability failed" in response.json()["detail"]
    assert [ok for ok, _ in fake_ai.results] == [False]
    assert p1.charge == 5
    assert saved == []


def test_ai_turn_activate_resolution_error_is_recorded(monkeypatch):
    from game_engine.rules.effects.action_effects import ArcherActivatedAbility

    setup, p1, p2 = _archer_game()
    archer, umbruh = _card(p1.in_play, "Archer"), _card(p2.in_play, "Umbruh")
    fake_ai = _FakeActivateAI(archer.id, umbruh.id)

    def _boom(self, game_state, **kwargs):
        raise RuntimeError("cascade failed")
    monkeypatch.setattr(ArcherActivatedAbility, "apply", _boom)

    response, saved = _ai_turn(setup, monkeypatch, fake_ai)

    assert response.status_code == 500
    assert "cascade failed" in response.json()["detail"]
    assert fake_ai.results == [(False, "cascade failed")]
    assert saved == []


def test_ai_turn_activate_saves_victory_entry(monkeypatch):
    setup, _ = create_game_with_cards(
        player1_in_play=["Archer"],
        player2_in_play=["Hind Leg Kicker"],
        turn_number=3,
        active_player="player1",
        player1_charge=5,
    )
    gs = setup.game_state
    archer = _card(gs.players["player1"].in_play, "Archer")
    hlk = _card(gs.players["player2"].in_play, "Hind Leg Kicker")
    fake_ai = _FakeActivateAI(archer.id, hlk.id)

    response, saved = _ai_turn(setup, monkeypatch, fake_ai)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["game_state"] == {"winner": "player1", "is_game_over": True}
    assert body["ai_turn_summary"]["action"] == "activate_ability"
    assert fake_ai.results == [(True, None)]
    assert saved[-1][-2:] == ["activate_ability", "victory"]
