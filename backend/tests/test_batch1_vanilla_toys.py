"""
Tests for Batch 1 vanilla Toys: Car, Dino, Block.

These cards have no effects (empty effects field) - stats-only Toys used to
confirm the engine handles vanilla cards correctly before introducing any
new effect patterns.
"""

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from conftest import create_game_with_cards
from game_engine.data.card_loader import CardLoader
from game_engine.models.game_state import Phase


def _load_card(name: str):
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    return next(c for c in all_cards if c.name == name)


class TestVanillaToyStats:
    """Each card loads from the CSV with the correct stats and no effects."""

    def test_car_stats(self):
        car = _load_card("Car")
        assert car.is_toy()
        assert car.cost == 0
        assert car.speed == 7
        assert car.strength == 2
        assert car.stamina == 2
        assert car.effect_definitions == ""

    def test_dino_stats(self):
        dino = _load_card("Dino")
        assert dino.is_toy()
        assert dino.cost == 0
        assert dino.speed == 3
        assert dino.strength == 7
        assert dino.stamina == 1
        assert dino.effect_definitions == ""

    def test_block_stats(self):
        block = _load_card("Block")
        assert block.is_toy()
        assert block.cost == 0
        assert block.speed == 2
        assert block.strength == 3
        assert block.stamina == 5
        assert block.effect_definitions == ""


class TestVanillaToyPlay:
    """Each card can be played for its 0 Charge cost with no side effects."""

    def test_play_car_is_free_and_unmodified(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Car"],
            active_player="player1",
            turn_number=1,
            player1_charge=0,
        )
        car = cards["p1_hand_Car"]

        success = setup.engine.play_card(setup.player1, car)

        assert success
        assert car in setup.player1.in_play
        assert setup.player1.charge == 0
        assert setup.engine.get_card_stat(car, "speed") == 7
        assert setup.engine.get_card_stat(car, "strength") == 2
        assert setup.engine.get_card_stat(car, "stamina") == 2

    def test_play_dino_is_free_and_unmodified(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Dino"],
            active_player="player1",
            turn_number=1,
            player1_charge=0,
        )
        dino = cards["p1_hand_Dino"]

        success = setup.engine.play_card(setup.player1, dino)

        assert success
        assert dino in setup.player1.in_play
        assert setup.engine.get_card_stat(dino, "strength") == 7

    def test_play_block_is_free_and_unmodified(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Block"],
            active_player="player1",
            turn_number=1,
            player1_charge=0,
        )
        block = cards["p1_hand_Block"]

        success = setup.engine.play_card(setup.player1, block)

        assert success
        assert block in setup.player1.in_play
        assert setup.engine.get_card_stat(block, "stamina") == 5


class TestVanillaToyTussle:
    """Stats-only cards still resolve tussles correctly via base combat math."""

    def test_car_outspeeds_dino_and_kills_it(self):
        setup, cards = create_game_with_cards(
            player1_in_play=["Car"],
            player2_in_play=["Dino"],
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        car = cards["p1_inplay_Car"]
        dino = cards["p2_inplay_Dino"]
        setup.game_state.phase = Phase.MAIN

        success, _ = setup.engine.initiate_tussle(car, dino, setup.player1)

        assert success
        # Car (speed 7) strikes first, deals 2 strength damage to Dino (1 stamina) -> broken
        assert dino in setup.player2.break_zone
        assert dino not in setup.player2.in_play

    def test_dino_kills_block_despite_high_stamina(self):
        setup, cards = create_game_with_cards(
            player1_in_play=["Dino"],
            player2_in_play=["Block"],
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        dino = cards["p1_inplay_Dino"]
        block = cards["p2_inplay_Block"]
        setup.game_state.phase = Phase.MAIN

        success, _ = setup.engine.initiate_tussle(dino, block, setup.player1)

        assert success
        # Dino (strength 7) hits Block (stamina 5) for 7 damage -> broken despite high stamina
        assert block in setup.player2.break_zone
