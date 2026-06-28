"""
Tests for Batch 3 cards: MaBookBook, Plane Plus, Bubble Blocker, Cake.

MaBookBook introduces a new effect, self_cost_increase_by_broken - the
mirror image of Dream's reduce_cost_by_broken. Plane Plus, Bubble Blocker,
and Cake combine/reuse existing effects (direct_attack, set_self_tussle_cost,
team_opponent_immunity, gain_charge) on new stat/cost lines.
"""

from conftest import create_game_with_cards, get_card_template
from game_engine.rules.effects.effect_registry import EffectRegistry
from game_engine.rules.effects.continuous_effects import (
    SelfCostIncreaseByBrokenEffect,
    DirectAttackEffect,
    SetSelfTussleCostEffect,
)
from game_engine.rules.effects.action_effects import GainChargeEffect


class TestMaBookBookCostIncrease:
    """MaBookBook: costs 1 more for each of the controller's broken cards."""

    def test_effect_parsing(self):
        card = get_card_template("MaBookBook")
        assert card.effect_definitions == "self_cost_increase_by_broken"

        effects = EffectRegistry.get_effects(card)
        assert len(effects) == 1
        assert isinstance(effects[0], SelfCostIncreaseByBrokenEffect)

    def test_stats(self):
        card = get_card_template("MaBookBook")
        assert card.is_toy()
        assert card.cost == 0
        assert card.speed == 4
        assert card.strength == 5
        assert card.stamina == 4

    def test_cost_unchanged_with_no_breaking_cards(self):
        setup, cards = create_game_with_cards(
            player1_hand=["MaBookBook"],
            active_player="player1",
        )
        mabookbook = cards["p1_hand_MaBookBook"]

        cost = setup.engine.calculate_card_cost(mabookbook, setup.player1)
        assert cost == 0

    def test_cost_increases_with_breaking_cards(self):
        setup, cards = create_game_with_cards(
            player1_hand=["MaBookBook"],
            player1_break=["Ka", "Wizard", "Beary"],
            active_player="player1",
        )
        mabookbook = cards["p1_hand_MaBookBook"]

        cost = setup.engine.calculate_card_cost(mabookbook, setup.player1)
        assert cost == 3

    def test_cost_only_increases_for_owners_breaking_cards(self):
        setup, cards = create_game_with_cards(
            player1_hand=["MaBookBook"],
            player2_break=["Ka", "Wizard"],
            active_player="player1",
        )
        mabookbook = cards["p1_hand_MaBookBook"]

        cost = setup.engine.calculate_card_cost(mabookbook, setup.player1)
        assert cost == 0


class TestPlanePlus:
    """Plane Plus: tussles cost 1 and can direct attack through blockers."""

    def test_effect_parsing(self):
        card = get_card_template("Plane Plus")
        assert card.effect_definitions == "direct_attack;set_self_tussle_cost:1"

        effects = EffectRegistry.get_effects(card)
        assert len(effects) == 2
        assert any(isinstance(e, DirectAttackEffect) for e in effects)
        assert any(isinstance(e, SetSelfTussleCostEffect) for e in effects)

    def test_stats(self):
        card = get_card_template("Plane Plus")
        assert card.is_toy()
        assert card.cost == 2
        assert card.speed == 4
        assert card.strength == 2
        assert card.stamina == 2

    def test_tussle_cost_is_one(self):
        setup, cards = create_game_with_cards(
            player1_in_play=["Plane Plus"],
            active_player="player1",
            player1_charge=5,
        )
        plane_plus = cards["p1_inplay_Plane Plus"]

        cost = setup.engine.calculate_tussle_cost(plane_plus, setup.player1)
        assert cost == 1

    def test_can_direct_attack_when_opponent_has_cards(self):
        setup, cards = create_game_with_cards(
            player1_in_play=["Plane Plus"],
            player2_in_play=["Ka"],
            player2_hand=["Rush"],
            active_player="player1",
            player1_charge=5,
        )
        plane_plus = cards["p1_inplay_Plane Plus"]

        can_attack, reason = setup.engine.can_tussle(plane_plus, None, setup.player1)
        assert can_attack, f"Plane Plus should be able to direct attack, but got: {reason}"


class TestBubbleBlocker:
    """Bubble Blocker: opponent's effects don't affect the controller's cards."""

    def test_effect_parsing(self):
        card = get_card_template("Bubble Blocker")
        assert card.effect_definitions == "team_opponent_immunity"

        effects = EffectRegistry.get_effects(card)
        assert len(effects) == 1

    def test_stats(self):
        card = get_card_template("Bubble Blocker")
        assert card.is_toy()
        assert card.cost == 0
        assert card.speed == 2
        assert card.strength == 2
        assert card.stamina == 1


class TestCake:
    """Cake: Gain 5 Charge, no turn restriction (unlike Rush)."""

    def test_effect_parsing(self):
        card = get_card_template("Cake")
        assert card.effect_definitions == "gain_charge:5"

        effects = EffectRegistry.get_effects(card)
        assert len(effects) == 1
        assert isinstance(effects[0], GainChargeEffect)

    def test_cost(self):
        card = get_card_template("Cake")
        assert card.cost == 3

    def test_play_gains_five_charge(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Cake"],
            active_player="player1",
            player1_charge=3,
            turn_number=1,
        )
        cake = cards["p1_hand_Cake"]

        success = setup.engine.play_card(setup.player1, cake)

        assert success
        assert setup.player1.charge == 5  # 3 Charge - 3 cost + 5 gained
