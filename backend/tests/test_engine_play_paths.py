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


def test_activate_ability_rejects_own_card_target():
    setup, p1, _ = _archer_game()
    archer, ka = _card(p1.in_play, "Archer"), _card(p1.in_play, "Ka")

    with pytest.raises(ValueError, match="Invalid target"):
        ActionExecutor(setup.engine).execute_activate_ability("player1", archer.id, target_id=ka.id)
    assert p1.charge == 5
    assert ka.current_stamina == ka.stamina


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
    setup, p1, _ = _archer_game()
    archer, ka = _card(p1.in_play, "Archer"), _card(p1.in_play, "Ka")
    client, saved = _route_client(setup, monkeypatch)

    response = client.post(
        f"/games/{setup.game_state.game_id}/activate-ability",
        json={"player_id": "player1", "card_id": archer.id, "target_id": ka.id, "amount": 1},
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
