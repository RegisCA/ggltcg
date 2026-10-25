"""
get_ai_player(game_id) returns one LLMPlayer per game.

LLMPlayer keeps the current turn plan keyed only by turn number. With a
single shared instance, two AI games on the same turn number would execute
each other's plan.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

import game_engine.ai.llm_player as llm_player


class _StubPlayer:
    """Stands in for LLMPlayer (no Gemini client)."""


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch):
    monkeypatch.setattr(llm_player, "LLMPlayer", _StubPlayer)
    monkeypatch.setattr(llm_player, "_ai_player", None)
    monkeypatch.setattr(llm_player, "_game_ai_players", llm_player.OrderedDict())


def test_each_game_gets_its_own_ai_player():
    a = llm_player.get_ai_player("game-a")
    b = llm_player.get_ai_player("game-b")

    assert a is not b
    assert llm_player.get_ai_player("game-a") is a


def test_shared_instance_without_game_id():
    shared = llm_player.get_ai_player()

    assert llm_player.get_ai_player() is shared
    assert llm_player.get_ai_player("game-a") is not shared


def test_least_recently_used_game_is_evicted(monkeypatch):
    monkeypatch.setattr(llm_player, "MAX_CACHED_GAME_AI_PLAYERS", 2)
    a = llm_player.get_ai_player("game-a")
    llm_player.get_ai_player("game-b")
    llm_player.get_ai_player("game-a")  # touch a, so b is the oldest
    llm_player.get_ai_player("game-c")

    assert list(llm_player._game_ai_players) == ["game-a", "game-c"]
    assert llm_player.get_ai_player("game-a") is a
