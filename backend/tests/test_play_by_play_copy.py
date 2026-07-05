"""
Regression coverage for the play-by-play log copy (UI Refresh Phase 3, item 1).

The game log is the most-watched surface in the game (ticker + live opponent
playback), so its copy uses a subject-verb-object voice with the cost in
trailing parens ("Block tussled Violin (2 Charge)") rather than the older
engine-flavored "Spent 2 Charge for Block to tussle Violin". These tests pin
that shape so it can't silently regress. Rules vocabulary (tussle/Charge/
break/fix) is intentionally preserved.
"""

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from types import SimpleNamespace

from conftest import create_game_with_cards
from game_engine.models.game_state import Phase
from game_engine.validation.action_executor import (
    ActionExecutor,
    build_tussle_description,
)


class TestBuildTussleDescription:
    """The shared helper used by both the human route and the AI executor."""

    def test_tussle_named_defender(self):
        defender = SimpleNamespace(name="Violin")
        assert (
            build_tussle_description(2, "Block", defender=defender)
            == "Block tussled Violin (2 Charge)"
        )

    def test_tussle_break_from_hand(self):
        assert (
            build_tussle_description(2, "Block", broken_from_hand="Knight")
            == "Block tussled Knight from hand (2 Charge)"
        )

    def test_tussle_direct_attack(self):
        assert (
            build_tussle_description(2, "Block")
            == "Block tussled directly (2 Charge)"
        )


class TestPlayCardDescription:
    """Play-card copy: 'Played <card>[, <effect> <target>] (<cost>)'."""

    def test_plain_play_leads_with_played_and_trailing_cost(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Knight"],
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        setup.game_state.phase = Phase.MAIN
        knight = cards["p1_hand_Knight"]

        executor = ActionExecutor(setup.engine)
        result = executor.execute_play_card(
            player_id=setup.player1.player_id,
            card_id=knight.id,
        )

        assert result.success
        # Subject-verb-object voice, cost in trailing parens, no "Spent ...".
        assert result.description == f"Played Knight ({result.cost} Charge)"
        assert "Spent" not in result.description

    def test_break_action_appends_effect_clause_before_cost(self):
        # Stomp is a break_target action; targeting the opponent's Ka should
        # read "Played Stomp, broke Ka (<cost> Charge)".
        setup, cards = create_game_with_cards(
            player1_hand=["Stomp"],
            player2_in_play=["Ka"],
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        setup.game_state.phase = Phase.MAIN
        stomp = cards["p1_hand_Stomp"]
        ka = cards["p2_inplay_Ka"]

        executor = ActionExecutor(setup.engine)
        result = executor.execute_play_card(
            player_id=setup.player1.player_id,
            card_id=stomp.id,
            target_card_id=ka.id,
        )

        assert result.success
        assert result.description == f"Played Stomp, broke Ka ({result.cost} Charge)"
