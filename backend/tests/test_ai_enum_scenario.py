"""
Phase 4.2 (WP-4): standard scenario in `enum` planner mode (LIVE).

Mirrors test_ai_standard_scenario.py but drives the deterministic-enumerator
planner mode. Gate: the canonical openers plan correctly in enum mode with
CC waste ≤ the dual baseline (≤1). Request 1 is engine-side (no LLM); only
Request 2 (strategic selection) calls the LLM, so this is ~1 call/turn.

Skipped without a real provider key (like the other live AI tests).
"""

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards
from ai_test_support import has_valid_ai_api_key, build_turn_planner
from game_engine.ai.quality_metrics import TurnMetrics, clear_session_metrics


pytestmark = pytest.mark.skipif(
    not has_valid_ai_api_key(),
    reason="No valid AI provider API key found - skipping live LLM tests",
)


@pytest.fixture
def enum_planner():
    return build_turn_planner(planner_mode="enum")


@pytest.fixture(autouse=True)
def clear_metrics():
    clear_session_metrics()
    yield


def test_turn1_surge_knight_enum(enum_planner):
    """Turn 1 Surge+Knight opener in enum mode: ≤1 CC wasted, ≥1 slept."""
    setup, _ = create_game_with_cards(
        player1_hand=["Surge", "Knight", "Umbruh", "Wake"],
        player1_in_play=[],
        player2_hand=["Knight", "Ka", "Archer", "Wizard", "Drop", "Surge"],
        player2_in_play=[],
        player1_cc=2,
        player2_cc=0,
        active_player="player1",
        turn_number=1,
    )
    plan = enum_planner.create_plan(setup.game_state, "player1", setup.engine)
    assert plan is not None, "enum mode should produce a plan"

    metrics = TurnMetrics.from_plan(plan, setup.game_state, "player1")
    print(f"\n[enum] Turn1 cc_wasted={metrics.cc_wasted} slept={metrics.cards_slept}")
    assert metrics.cc_wasted <= 1, f"enum wasted {metrics.cc_wasted} CC (dual baseline ≤1)"
    assert metrics.cards_slept >= 1


def test_turn2_aggressive_enum(enum_planner):
    """Turn 2 with a board in enum mode: efficient, no wasted-CC regression."""
    setup, _ = create_game_with_cards(
        player1_in_play=["Knight"],
        player2_in_play=["Knight"],
        player2_hand=["Umbruh", "Wake", "Archer"],
        player1_cc=0,
        player2_cc=4,
        active_player="player2",
        turn_number=2,
    )
    plan = enum_planner.create_plan(setup.game_state, "player2", setup.engine)
    assert plan is not None

    metrics = TurnMetrics.from_plan(plan, setup.game_state, "player2")
    print(f"\n[enum] Turn2 cc_wasted={metrics.cc_wasted} slept={metrics.cards_slept}")
    assert metrics.cc_wasted <= 1
