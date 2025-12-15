"""
Tests for the 'Paper Plane' card.

Paper Plane is a Toy card with:
- Cost: 1
- Effect: Can direct attack opponent's hand even when they have cards in play
- Stats: 2/2/1 (speed/strength/stamina)

This tests the DirectAttackEffect which allows bypassing the normal requirement
that direct attacks can only happen when opponent's play zone is empty.
"""

import pytest
from pathlib import Path

from conftest import create_game_with_cards, get_card_template
from game_engine.rules.effects.effect_registry import EffectRegistry
from game_engine.rules.effects.continuous_effects import DirectAttackEffect
from game_engine.effects_constants import EffectDefinitions
from game_engine.validation.action_validator import ActionValidator


class TestPaperPlaneEffectParsing:
    """Tests for effect parsing of Paper Plane card."""
    
    def test_effect_definition_constant_exists(self):
        """Verify DIRECT_ATTACK constant is defined."""
        assert hasattr(EffectDefinitions, "DIRECT_ATTACK")
        assert EffectDefinitions.DIRECT_ATTACK == "direct_attack"
    
    def test_paper_plane_effect_parsing(self):
        """Test that Paper Plane effect is parsed correctly from CSV."""
        card = get_card_template("Paper Plane")
        
        assert card.effect_definitions == "direct_attack"
        
        effects = EffectRegistry.get_effects(card)
        assert len(effects) == 1
        assert isinstance(effects[0], DirectAttackEffect)
    
    def test_card_is_toy_type(self):
        """Verify Paper Plane is a Toy card."""
        card = get_card_template("Paper Plane")
        assert card.is_toy()
        assert card.cost == 1
        assert card.speed == 2
        assert card.strength == 2
        assert card.stamina == 1


class TestPaperPlaneDirectAttack:
    """Tests for Paper Plane's direct attack ability."""
    
    def test_paper_plane_can_direct_attack_when_opponent_has_cards(self):
        """Paper Plane should be able to direct attack even when opponent has cards in play."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Paper Plane"],
            player2_in_play=["Ka"],  # Opponent has a card in play
            player2_hand=["Rush"],   # Opponent has cards in hand to attack
            active_player="player1",
            player1_cc=5,
        )
        
        paper_plane = cards["p1_inplay_Paper Plane"]
        
        # Check can_tussle returns True for direct attack
        can_attack, reason = setup.engine.can_tussle(paper_plane, None, setup.player1)
        assert can_attack, f"Paper Plane should be able to direct attack, but got: {reason}"
    
    def test_normal_toy_cannot_direct_attack_when_opponent_has_cards(self):
        """Normal Toys should NOT be able to direct attack when opponent has cards in play."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Ka"],
            player2_in_play=["Knight"],  # Opponent has a card in play
            player2_hand=["Rush"],
            active_player="player1",
            player1_cc=5,
        )
        
        ka = cards["p1_inplay_Ka"]
        
        # Check can_tussle returns False for direct attack
        can_attack, reason = setup.engine.can_tussle(ka, None, setup.player1)
        assert not can_attack
        assert "cards in play" in reason.lower()
    
    def test_paper_plane_direct_attack_in_valid_actions(self):
        """Paper Plane should have direct attack as a valid action when opponent has cards in play."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Paper Plane"],
            player2_in_play=["Ka"],
            player2_hand=["Rush"],
            active_player="player1",
            player1_cc=5,
        )
        
        paper_plane = cards["p1_inplay_Paper Plane"]
        
        validator = ActionValidator(setup.engine)
        valid_actions = validator.get_valid_actions(setup.player1.player_id)
        
        # Find direct attack action for Paper Plane
        direct_attack_actions = [
            a for a in valid_actions
            if a.action_type == "tussle"
            and a.card_id == paper_plane.id
            and a.target_options == ["direct_attack"]
        ]
        
        assert len(direct_attack_actions) == 1, "Paper Plane should have direct attack as valid action"
    
    def test_normal_toy_no_direct_attack_when_opponent_has_cards(self):
        """Normal Toys should NOT have direct attack in valid actions when opponent has cards."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Ka"],
            player2_in_play=["Knight"],
            player2_hand=["Rush"],
            active_player="player1",
            player1_cc=5,
        )
        
        ka = cards["p1_inplay_Ka"]
        
        validator = ActionValidator(setup.engine)
        valid_actions = validator.get_valid_actions(setup.player1.player_id)
        
        # Find direct attack action for Ka
        direct_attack_actions = [
            a for a in valid_actions
            if a.action_type == "tussle"
            and a.card_id == ka.id
            and a.target_options == ["direct_attack"]
        ]
        
        assert len(direct_attack_actions) == 0, "Ka should NOT have direct attack when opponent has cards"


class TestPaperPlaneExecution:
    """Tests for executing Paper Plane's direct attack."""
    
    def test_paper_plane_direct_attack_sleeps_opponent_hand_card(self):
        """Paper Plane direct attack should sleep a random card from opponent's hand."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Paper Plane"],
            player2_in_play=["Ka"],
            player2_hand=["Rush"],
            active_player="player1",
            player1_cc=5,
        )
        
        paper_plane = cards["p1_inplay_Paper Plane"]
        rush = cards["p2_hand_Rush"]
        
        initial_hand_count = len(setup.player2.hand)
        initial_sleep_count = len(setup.player2.sleep_zone)
        
        # Execute direct attack
        setup.engine.initiate_tussle(paper_plane, None, setup.player1)
        
        # Opponent should have one fewer card in hand, one more in sleep zone
        assert len(setup.player2.hand) == initial_hand_count - 1
        assert len(setup.player2.sleep_zone) == initial_sleep_count + 1
    
    def test_paper_plane_direct_attack_costs_cc(self):
        """Paper Plane direct attack should cost CC like normal tussles."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Paper Plane"],
            player2_in_play=["Ka"],
            player2_hand=["Rush"],
            active_player="player1",
            player1_cc=5,
        )
        
        paper_plane = cards["p1_inplay_Paper Plane"]
        initial_cc = setup.player1.cc
        
        tussle_cost = setup.engine.calculate_tussle_cost(paper_plane, setup.player1)
        
        # Execute direct attack
        setup.engine.initiate_tussle(paper_plane, None, setup.player1)
        
        # CC should be reduced by tussle cost
        assert setup.player1.cc == initial_cc - tussle_cost
    
    def test_paper_plane_respects_direct_attack_limit(self):
        """Paper Plane should still respect the 2 direct attacks per turn limit."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Paper Plane"],
            player2_in_play=["Ka"],
            player2_hand=["Rush", "Clean", "Wake"],  # Multiple cards to attack
            active_player="player1",
            player1_cc=20,  # Plenty of CC
        )
        
        paper_plane = cards["p1_inplay_Paper Plane"]
        
        # First direct attack - should work
        can_attack_1, _ = setup.engine.can_tussle(paper_plane, None, setup.player1)
        assert can_attack_1
        setup.engine.initiate_tussle(paper_plane, None, setup.player1)
        
        # Second direct attack - should work
        can_attack_2, _ = setup.engine.can_tussle(paper_plane, None, setup.player1)
        assert can_attack_2
        setup.engine.initiate_tussle(paper_plane, None, setup.player1)
        
        # Third direct attack - should be blocked
        can_attack_3, reason = setup.engine.can_tussle(paper_plane, None, setup.player1)
        assert not can_attack_3
        assert "2 direct attacks" in reason.lower()


class TestPaperPlaneCanAlsoTussleNormally:
    """Tests that Paper Plane can still tussle defenders normally."""
    
    def test_paper_plane_can_tussle_defender(self):
        """Paper Plane should also be able to tussle opponent's cards in play."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Paper Plane"],
            player2_in_play=["Ka"],
            player2_hand=["Rush"],
            active_player="player1",
            player1_cc=5,
        )
        
        paper_plane = cards["p1_inplay_Paper Plane"]
        ka = cards["p2_inplay_Ka"]
        
        # Can tussle Ka directly
        can_tussle, _ = setup.engine.can_tussle(paper_plane, ka, setup.player1)
        assert can_tussle
    
    def test_paper_plane_has_both_tussle_and_direct_attack_options(self):
        """Paper Plane should have both tussle and direct attack as valid actions."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Paper Plane"],
            player2_in_play=["Ka"],
            player2_hand=["Rush"],
            active_player="player1",
            player1_cc=5,
        )
        
        paper_plane = cards["p1_inplay_Paper Plane"]
        ka = cards["p2_inplay_Ka"]
        
        validator = ActionValidator(setup.engine)
        valid_actions = validator.get_valid_actions(setup.player1.player_id)
        
        # Find tussle actions for Paper Plane
        paper_plane_tussles = [
            a for a in valid_actions
            if a.action_type == "tussle" and a.card_id == paper_plane.id
        ]
        
        # Should have 2 options: direct attack AND tussle Ka
        assert len(paper_plane_tussles) == 2
        
        target_options = [a.target_options for a in paper_plane_tussles]
        assert ["direct_attack"] in target_options
        assert [ka.id] in target_options


class TestPaperPlaneEdgeCases:
    """Edge case tests for Paper Plane."""
    
    def test_paper_plane_cannot_direct_attack_empty_hand(self):
        """Paper Plane cannot direct attack if opponent has no cards in hand."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Paper Plane"],
            player2_in_play=["Ka"],
            # player2_hand is empty
            active_player="player1",
            player1_cc=5,
        )
        
        paper_plane = cards["p1_inplay_Paper Plane"]
        
        can_attack, reason = setup.engine.can_tussle(paper_plane, None, setup.player1)
        assert not can_attack
        assert "no cards in hand" in reason.lower()
    
    def test_paper_plane_direct_attack_when_opponent_board_empty(self):
        """Paper Plane can still direct attack when opponent has no cards in play (normal case)."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Paper Plane"],
            # player2_in_play is empty
            player2_hand=["Rush"],
            active_player="player1",
            player1_cc=5,
        )
        
        paper_plane = cards["p1_inplay_Paper Plane"]
        
        can_attack, _ = setup.engine.can_tussle(paper_plane, None, setup.player1)
        assert can_attack
