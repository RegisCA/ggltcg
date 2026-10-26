"""Simulation runner: activated abilities (Archer) reach their target.

The runner used to read ``details["target_ids"]``, but
``LLMPlayer.get_action_details`` (inherited by ``ScriptedPlayer``) returns
``target_id`` for activations. So in simulations Archer spent its Charge and
removed no Stamina. It now goes through
``ActionExecutor.execute_activate_ability``, like live games and the enumerator.
"""

import pytest

from conftest import create_game_with_cards
from game_engine.validation import ActionValidator
from simulation.runner import SimulationRunner
from simulation.scripted_player import ScriptedPlayer


@pytest.fixture
def no_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def _activate(opponent_toy):
    setup, _ = create_game_with_cards(
        player1_in_play=["Archer"],
        player2_in_play=[opponent_toy],
        turn_number=3,
        active_player="player1",
        player1_charge=5,
    )
    gs = setup.game_state
    action = next(
        a for a in ActionValidator(setup.engine).get_valid_actions("player1")
        if a.action_type == "activate_ability"
    )
    runner = SimulationRunner(player1_policy="greedy", player2_policy="greedy")
    ended_turn = runner._execute_action(setup.engine, gs, ScriptedPlayer(policy="greedy"), action)
    return gs, runner, ended_turn


def test_archer_removes_stamina_in_simulation(no_api_key):
    gs, runner, ended_turn = _activate("Umbruh")
    umbruh = gs.players["player2"].in_play[0]

    assert ended_turn is False
    assert gs.players["player1"].charge == 4
    assert umbruh.current_stamina == umbruh.stamina - 1
    assert runner.rejected_actions == 0


def test_archer_breaks_target_at_zero_stamina_in_simulation(no_api_key):
    gs, runner, _ = _activate("Hind Leg Kicker")  # 1 Stamina
    p2 = gs.players["player2"]

    assert p2.in_play == []
    assert [c.name for c in p2.break_zone] == ["Hind Leg Kicker"]
    assert gs.players["player1"].charge == 4
    assert runner.rejected_actions == 0
