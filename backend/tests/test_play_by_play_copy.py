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

from conftest import create_game_with_cards
from game_engine.models.game_state import Phase
from game_engine.validation.action_executor import (
    ActionExecutor,
    build_tussle_description,
    card_label,
)


class TestBuildTussleDescription:
    """The shared helper used by both the human route and the AI executor."""

    def test_tussle_named_defender(self):
        assert (
            build_tussle_description(2, "Block", defender_label="Violin")
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


class TestOwnershipAnnotation:
    """
    Stolen cards (Twist: controller != owner) are annotated with the owner's
    name in the log — "Ka (Player 1's)" — so a board with two same-name cards
    stays readable. Labels are captured before the action resolves, because
    breaking a card resets its controller to its owner.
    """

    def test_card_label_plain_when_controller_is_owner(self):
        setup, cards = create_game_with_cards(player1_in_play=["Ka"])
        ka = cards["p1_inplay_Ka"]
        assert card_label(ka, setup.game_state) == "Ka"

    def test_card_label_annotated_when_stolen(self):
        setup, cards = create_game_with_cards(player1_in_play=["Ka"])
        ka = cards["p1_inplay_Ka"]
        setup.game_state.change_control(ka, setup.player2)
        assert card_label(ka, setup.game_state) == "Ka (Player 1's)"

    def test_tussle_with_stolen_attacker_names_original_owner(self):
        # Player 2 stole Player 1's Ka (Twist) and attacks Player 1's Knight
        # with it: the log should read "Ka (Player 1's) tussled Knight ...".
        setup, cards = create_game_with_cards(
            player1_in_play=["Ka", "Knight"],
            active_player="player2",
            turn_number=2,
            player2_charge=10,
        )
        setup.game_state.phase = Phase.MAIN
        ka = cards["p1_inplay_Ka"]
        knight = cards["p1_inplay_Knight"]
        setup.game_state.change_control(ka, setup.player2)

        executor = ActionExecutor(setup.engine)
        result = executor.execute_tussle(
            player_id=setup.player2.player_id,
            attacker_id=ka.id,
            defender_id=knight.id,
        )

        assert result.success
        assert result.description == (
            f"Ka (Player 1's) tussled Knight ({result.cost} Charge)"
        )

    def test_break_action_on_stolen_card_names_original_owner(self):
        # Player 1 Stomps their own Ka that Player 2 twisted away: the log
        # should read "Played Stomp, broke Ka (Player 1's) ..." even though
        # breaking resets the card's controller back to its owner.
        setup, cards = create_game_with_cards(
            player1_hand=["Stomp"],
            player1_in_play=["Ka"],
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        setup.game_state.phase = Phase.MAIN
        stomp = cards["p1_hand_Stomp"]
        ka = cards["p1_inplay_Ka"]
        setup.game_state.change_control(ka, setup.player2)

        executor = ActionExecutor(setup.engine)
        result = executor.execute_play_card(
            player_id=setup.player1.player_id,
            card_id=stomp.id,
            target_card_id=ka.id,
        )

        assert result.success
        assert result.description == (
            f"Played Stomp, broke Ka (Player 1's) ({result.cost} Charge)"
        )
