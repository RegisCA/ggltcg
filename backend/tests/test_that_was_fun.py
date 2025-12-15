"""
Tests for the 'That was fun' card.

That was fun is an Action card with:
- Cost: 0
- Effect: Unsleep an action card (returns 1 Action from Sleep Zone to hand)

Related to Issue #235: https://github.com/RegisCA/ggltcg/issues/235
"""

import pytest
from pathlib import Path

from conftest import create_game_with_cards, get_card_template
from game_engine.rules.effects.effect_registry import EffectRegistry
from game_engine.rules.effects.action_effects import UnsleepEffect
from game_engine.effects_constants import EffectDefinitions


class TestThatWasFunEffectParsing:
    """Tests for effect parsing of 'That was fun' card."""
    
    def test_effect_definition_constant_exists(self):
        """Verify UNSLEEP_ACTIONS_1 constant is defined."""
        assert hasattr(EffectDefinitions, "UNSLEEP_ACTIONS_1")
        assert EffectDefinitions.UNSLEEP_ACTIONS_1 == "unsleep:actions:1"
    
    def test_that_was_fun_effect_parsing(self):
        """Test that 'That was fun' effect is parsed correctly from CSV."""
        card = get_card_template("That was fun")
        
        assert card.effect_definitions == "unsleep:actions:1"
        
        effects = EffectRegistry.get_effects(card)
        assert len(effects) == 1
        assert isinstance(effects[0], UnsleepEffect)
        assert effects[0].count == 1
        assert effects[0].card_type_filter == "actions"
    
    def test_card_is_action_type(self):
        """Verify 'That was fun' is an Action card."""
        card = get_card_template("That was fun")
        assert card.is_action()
        assert card.cost == 0


class TestThatWasFunTargeting:
    """Tests for target selection of 'That was fun'."""
    
    def test_only_action_cards_are_valid_targets(self):
        """That was fun should only target Action cards in sleep zone."""
        setup, cards = create_game_with_cards(
            player1_hand=["That was fun"],
            player1_sleep=["Rush", "Ka", "Wake"],  # Rush and Wake are Actions, Ka is a Toy
            active_player="player1",
        )
        
        that_was_fun = cards["p1_hand_That was fun"]
        rush = cards["p1_sleep_Rush"]
        ka = cards["p1_sleep_Ka"]
        wake = cards["p1_sleep_Wake"]
        
        effects = EffectRegistry.get_effects(that_was_fun)
        unsleep_effect = effects[0]
        
        valid_targets = unsleep_effect.get_valid_targets(
            setup.game_state, setup.player1
        )
        
        # Only Action cards should be valid targets
        assert rush in valid_targets
        assert wake in valid_targets
        assert ka not in valid_targets
        assert len(valid_targets) == 2
    
    def test_no_valid_targets_when_no_actions_in_sleep(self):
        """No valid targets when sleep zone has only Toys."""
        setup, cards = create_game_with_cards(
            player1_hand=["That was fun"],
            player1_sleep=["Ka", "Knight"],  # Only Toys
            active_player="player1",
        )
        
        that_was_fun = cards["p1_hand_That was fun"]
        
        effects = EffectRegistry.get_effects(that_was_fun)
        unsleep_effect = effects[0]
        
        valid_targets = unsleep_effect.get_valid_targets(
            setup.game_state, setup.player1
        )
        
        assert len(valid_targets) == 0
    
    def test_no_valid_targets_when_sleep_zone_empty(self):
        """No valid targets when sleep zone is empty."""
        setup, cards = create_game_with_cards(
            player1_hand=["That was fun"],
            active_player="player1",
        )
        
        that_was_fun = cards["p1_hand_That was fun"]
        
        effects = EffectRegistry.get_effects(that_was_fun)
        unsleep_effect = effects[0]
        
        valid_targets = unsleep_effect.get_valid_targets(
            setup.game_state, setup.player1
        )
        
        assert len(valid_targets) == 0


class TestThatWasFunExecution:
    """Tests for playing 'That was fun' card."""
    
    def test_unsleep_action_card(self):
        """Playing 'That was fun' returns an Action from sleep zone to hand."""
        setup, cards = create_game_with_cards(
            player1_hand=["That was fun"],
            player1_sleep=["Rush"],
            active_player="player1",
            player1_cc=5,
        )
        
        that_was_fun = cards["p1_hand_That was fun"]
        rush = cards["p1_sleep_Rush"]
        
        # Play That was fun targeting Rush
        setup.engine.play_card(setup.player1, that_was_fun, target_ids=[rush.id])
        
        # Rush should be in hand now
        assert rush in setup.player1.hand
        assert rush not in setup.player1.sleep_zone
        
        # That was fun (Action) should be in sleep zone
        assert that_was_fun in setup.player1.sleep_zone
        assert that_was_fun not in setup.player1.hand
    
    def test_costs_zero_cc(self):
        """Playing 'That was fun' costs 0 CC."""
        setup, cards = create_game_with_cards(
            player1_hand=["That was fun"],
            player1_sleep=["Rush"],
            active_player="player1",
            player1_cc=5,
        )
        
        initial_cc = setup.player1.cc
        that_was_fun = cards["p1_hand_That was fun"]
        rush = cards["p1_sleep_Rush"]
        
        setup.engine.play_card(setup.player1, that_was_fun, target_ids=[rush.id])
        
        # CC should be unchanged (0 cost)
        assert setup.player1.cc == initial_cc
    
    def test_can_play_without_targets(self):
        """Can play 'That was fun' even with no valid targets (does nothing)."""
        setup, cards = create_game_with_cards(
            player1_hand=["That was fun"],
            player1_sleep=["Ka"],  # Only a Toy, not valid for That was fun
            active_player="player1",
        )
        
        that_was_fun = cards["p1_hand_That was fun"]
        ka = cards["p1_sleep_Ka"]
        
        # Play without targets (since no Action cards in sleep zone)
        setup.engine.play_card(setup.player1, that_was_fun, target_ids=[])
        
        # Ka should still be in sleep zone (not affected)
        assert ka in setup.player1.sleep_zone
        
        # That was fun should be in sleep zone
        assert that_was_fun in setup.player1.sleep_zone


class TestWakeVsThatWasFun:
    """Comparison tests between Wake and That was fun."""
    
    def test_wake_can_target_toys(self):
        """Wake can target both Toys and Actions."""
        setup, cards = create_game_with_cards(
            player1_hand=["Wake"],
            player1_sleep=["Ka", "Rush"],
            active_player="player1",
        )
        
        wake = cards["p1_hand_Wake"]
        ka = cards["p1_sleep_Ka"]
        rush = cards["p1_sleep_Rush"]
        
        effects = EffectRegistry.get_effects(wake)
        unsleep_effect = effects[0]
        
        valid_targets = unsleep_effect.get_valid_targets(
            setup.game_state, setup.player1
        )
        
        # Wake can target both Toys and Actions
        assert ka in valid_targets
        assert rush in valid_targets
    
    def test_that_was_fun_cannot_target_toys(self):
        """That was fun can only target Actions, not Toys."""
        setup, cards = create_game_with_cards(
            player1_hand=["That was fun"],
            player1_sleep=["Ka", "Rush"],
            active_player="player1",
        )
        
        that_was_fun = cards["p1_hand_That was fun"]
        ka = cards["p1_sleep_Ka"]
        rush = cards["p1_sleep_Rush"]
        
        effects = EffectRegistry.get_effects(that_was_fun)
        unsleep_effect = effects[0]
        
        valid_targets = unsleep_effect.get_valid_targets(
            setup.game_state, setup.player1
        )
        
        # That was fun can only target Actions
        assert rush in valid_targets
        assert ka not in valid_targets
