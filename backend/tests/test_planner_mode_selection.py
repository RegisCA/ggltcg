"""
Phase 4.2 (WP-4): planner-mode selection + KNOWN_ISSUES #1 resolution.

Before this work the live path (`get_ai_player`) derived the planner mode from
``AI_VERSION`` and never consulted ``AI_PLANNER_MODE`` — so setting
``AI_PLANNER_MODE`` had no effect in the running app (KNOWN_ISSUES Active Issue
#1). These tests pin the fixed behavior:

- ``AI_PLANNER_MODE`` is now authoritative in ``get_ai_player`` (single/dual/enum).
- **Back-compat is preserved**: ``AI_VERSION=4`` with no ``AI_PLANNER_MODE`` still
  resolves to ``dual`` (prod behavior must not shift).

These run with a dummy key — construction does not call the LLM.
"""

import pytest

from game_engine.ai.turn_planner import get_planner_mode
from game_engine.ai import llm_player
from game_engine.ai.llm_player import get_ai_player


@pytest.fixture(autouse=True)
def clean_ai_env(monkeypatch):
    """Isolate planner env vars and the singleton cache for each test.

    .env sets AI_PLANNER_MODE locally, so delete both vars by default and let
    each test opt in to the combination it exercises.
    """
    monkeypatch.delenv("AI_PLANNER_MODE", raising=False)
    monkeypatch.delenv("AI_VERSION", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    llm_player._ai_players.clear()
    yield
    llm_player._ai_players.clear()


# --- get_planner_mode: pure env resolution -------------------------------

def test_default_is_single(monkeypatch):
    assert get_planner_mode() == "single"


@pytest.mark.parametrize("mode", ["single", "dual", "enum"])
def test_ai_planner_mode_is_honored(monkeypatch, mode):
    monkeypatch.setenv("AI_PLANNER_MODE", mode)
    assert get_planner_mode() == mode


def test_invalid_ai_planner_mode_falls_back_to_single(monkeypatch):
    monkeypatch.setenv("AI_PLANNER_MODE", "nonsense")
    assert get_planner_mode() == "single"


def test_ai_version_4_back_compat(monkeypatch):
    """AI_VERSION=4 with no AI_PLANNER_MODE → dual (prod's selector)."""
    monkeypatch.setenv("AI_VERSION", "4")
    assert get_planner_mode() == "dual"


def test_ai_planner_mode_overrides_ai_version(monkeypatch):
    monkeypatch.setenv("AI_VERSION", "4")        # would be dual
    monkeypatch.setenv("AI_PLANNER_MODE", "enum")  # but enum wins
    assert get_planner_mode() == "enum"


# --- get_ai_player: live-path resolution (the actual bug fix) -------------

@pytest.mark.parametrize("mode", ["single", "dual", "enum"])
def test_get_ai_player_honors_ai_planner_mode(monkeypatch, mode):
    """The live path must now honor AI_PLANNER_MODE (KNOWN_ISSUES #1)."""
    monkeypatch.setenv("AI_PLANNER_MODE", mode)
    player = get_ai_player()
    assert player.planner_mode == mode
    assert player.turn_planner.planner_mode == mode


def test_get_ai_player_back_compat_version4(monkeypatch):
    """Deployed prod (AI_VERSION=4, no AI_PLANNER_MODE) still gets dual."""
    monkeypatch.setenv("AI_VERSION", "4")
    player = get_ai_player()
    assert player.planner_mode == "dual"
