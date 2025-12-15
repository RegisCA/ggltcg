"""
Tests for Gibbers card - Opponent cost increase effect.

Gibbers: Cost 1, Stats 1/1/1, Effect: "Your opponent's cards cost 1 more."

Tests verify:
1. Gibbers effect increases opponent's card costs by 1
2. Effect only applies while Gibbers is in play
3. Effect stacks with multiple Gibbers in play
4. Effect doesn't affect the Gibbers controller's cards
5. Effect interacts correctly with other cost modifiers (Dream, etc.)
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from conftest import create_game_with_cards, create_card, GameSetup


class TestGibbersBasicEffect:
    """Test Gibbers' basic cost increase effect."""
    
    def test_gibbers_increases_opponent_card_cost(self):
        """Gibbers in play should make opponent's cards cost 1 more."""
        # Arrange: P1 has Gibbers in play, P2 has a card in hand
        setup, cards = create_game_with_cards(
            player1_in_play=["Gibbers"],
            player2_hand=["Rush"],  # Rush normally costs 0
            active_player="player2",
            player2_cc=10,
        )
        
        # Get reference to P2's Rush
        rush = cards["p2_hand_Rush"]
        
        # Act: Calculate cost for P2's Rush with Gibbers in play
        cost = setup.engine.calculate_card_cost(rush, setup.player2)
        
        # Assert: Rush should cost 1 (0 base + 1 from Gibbers)
        assert cost == 1, f"Rush should cost 1 with Gibbers in play, got {cost}"
    
    def test_gibbers_does_not_affect_controllers_cards(self):
        """Gibbers should NOT increase its controller's card costs."""
        # Arrange: P1 has Gibbers in play and a card in hand
        setup, cards = create_game_with_cards(
            player1_in_play=["Gibbers"],
            player1_hand=["Rush"],  # Rush normally costs 0
            active_player="player1",
            player1_cc=10,
        )
        
        # Get reference to P1's Rush
        rush = cards["p1_hand_Rush"]
        
        # Act: Calculate cost for P1's Rush
        cost = setup.engine.calculate_card_cost(rush, setup.player1)
        
        # Assert: Rush should still cost 0 (Gibbers only affects opponent)
        assert cost == 0, f"Rush should cost 0 for Gibbers controller, got {cost}"
    
    def test_gibbers_effect_stops_when_sleeped(self):
        """Gibbers effect should stop when it leaves play."""
        # Arrange: P1 has Gibbers in play, P2 has a card in hand
        setup, cards = create_game_with_cards(
            player1_in_play=["Gibbers"],
            player2_hand=["Rush"],
            active_player="player1",
            player1_cc=10,
        )
        
        gibbers = cards["p1_inplay_Gibbers"]
        rush = cards["p2_hand_Rush"]
        
        # Verify cost is increased while Gibbers is in play
        cost_before = setup.engine.calculate_card_cost(rush, setup.player2)
        assert cost_before == 1, "Rush should cost 1 while Gibbers is in play"
        
        # Act: Sleep Gibbers
        setup.engine._sleep_card(gibbers, setup.player1, was_in_play=True)
        
        # Assert: Rush should cost 0 after Gibbers is sleeped
        cost_after = setup.engine.calculate_card_cost(rush, setup.player2)
        assert cost_after == 0, f"Rush should cost 0 after Gibbers is sleeped, got {cost_after}"


class TestGibbersStacking:
    """Test that multiple Gibbers effects stack."""
    
    def test_two_gibbers_increase_cost_by_two(self):
        """Two Gibbers in play should increase opponent's costs by 2."""
        # Arrange: P1 has 2 Gibbers in play
        setup, cards = create_game_with_cards(
            player1_in_play=["Gibbers", "Gibbers"],
            player2_hand=["Rush"],
            active_player="player2",
        )
        
        rush = cards["p2_hand_Rush"]
        
        # Act: Calculate cost
        cost = setup.engine.calculate_card_cost(rush, setup.player2)
        
        # Assert: Rush should cost 2 (0 base + 1 + 1 from two Gibbers)
        assert cost == 2, f"Rush should cost 2 with two Gibbers in play, got {cost}"


class TestGibbersInteractions:
    """Test Gibbers interactions with other effects."""
    
    def test_gibbers_stacks_with_dream_cost_reduction(self):
        """Gibbers cost increase should combine with Dream's cost reduction."""
        # Arrange: P1 has Gibbers in play, P2 has Dream in hand and cards in sleep zone
        setup, cards = create_game_with_cards(
            player1_in_play=["Gibbers"],
            player2_hand=["Dream"],  # Dream costs 4, reduced by sleeping cards
            player2_sleep=["Ka", "Knight"],  # 2 sleeping cards = -2 cost
            active_player="player2",
        )
        
        dream = cards["p2_hand_Dream"]
        
        # Act: Calculate cost
        # Dream base: 4, minus 2 for sleeping cards = 2, plus 1 for Gibbers = 3
        cost = setup.engine.calculate_card_cost(dream, setup.player2)
        
        # Assert: Dream should cost 3 (4 - 2 + 1)
        assert cost == 3, f"Dream should cost 3 (4-2+1), got {cost}"
    
    def test_gibbers_affects_high_cost_cards(self):
        """Gibbers should affect cards of any cost."""
        # Arrange: P1 has Gibbers in play, P2 has Clean (cost 3) in hand
        setup, cards = create_game_with_cards(
            player1_in_play=["Gibbers"],
            player2_hand=["Clean"],  # Clean costs 3
            active_player="player2",
        )
        
        clean = cards["p2_hand_Clean"]
        
        # Act: Calculate cost
        cost = setup.engine.calculate_card_cost(clean, setup.player2)
        
        # Assert: Clean should cost 4 (3 + 1)
        assert cost == 4, f"Clean should cost 4 with Gibbers in play, got {cost}"

    def test_gibbers_does_not_affect_immune_cards(self):
        """Cards with opponent_immunity (like Beary) should not have cost increased."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Gibbers"],
            player2_hand=["Beary", "Knight"],  # Beary has opponent_immunity, Knight (cost 1) doesn't
            active_player="player2",
        )
        
        beary = cards["p2_hand_Beary"]
        knight = cards["p2_hand_Knight"]
        
        # Both have base cost 1, but only Beary has opponent_immunity
        
        # Act: Calculate costs
        beary_cost = setup.engine.calculate_card_cost(beary, setup.player2)
        knight_cost = setup.engine.calculate_card_cost(knight, setup.player2)
        
        # Assert: Beary should NOT be affected (has opponent_immunity)
        assert beary_cost == 1, f"Beary should cost 1 (immune to Gibbers), got {beary_cost}"
        # Knight (base 1) should be affected: 1 + 1 = 2
        assert knight_cost == 2, f"Knight should cost 2 with Gibbers in play (1 + 1), got {knight_cost}"


class TestGibbersPlayability:
    """Test that Gibbers can be played and has correct stats."""
    
    def test_gibbers_can_be_played(self):
        """Gibbers should be playable for 1 CC."""
        setup, cards = create_game_with_cards(
            player1_hand=["Gibbers"],
            active_player="player1",
            player1_cc=1,
        )
        
        gibbers = cards["p1_hand_Gibbers"]
        
        # Act: Check if can play
        can_play, reason = setup.engine.can_play_card(gibbers, setup.player1)
        
        # Assert
        assert can_play, f"Should be able to play Gibbers: {reason}"
    
    def test_gibbers_has_correct_stats(self):
        """Gibbers should have 1/1/1 stats."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Gibbers"],
            active_player="player1",
        )
        
        gibbers = cards["p1_inplay_Gibbers"]
        
        # Assert
        assert setup.engine.get_card_stat(gibbers, "speed") == 1
        assert setup.engine.get_card_stat(gibbers, "strength") == 1
        assert setup.engine.get_card_stat(gibbers, "stamina") == 1
    
    def test_play_gibbers_and_verify_effect_activates(self):
        """Playing Gibbers should immediately affect opponent's costs."""
        setup, cards = create_game_with_cards(
            player1_hand=["Gibbers"],
            player2_hand=["Rush"],
            active_player="player1",
            player1_cc=5,
        )
        
        gibbers = cards["p1_hand_Gibbers"]
        rush = cards["p2_hand_Rush"]
        
        # Verify cost before playing Gibbers
        cost_before = setup.engine.calculate_card_cost(rush, setup.player2)
        assert cost_before == 0, "Rush should cost 0 before Gibbers is played"
        
        # Act: Play Gibbers
        setup.engine.play_card(setup.player1, gibbers)
        
        # Assert: Rush should now cost 1
        cost_after = setup.engine.calculate_card_cost(rush, setup.player2)
        assert cost_after == 1, f"Rush should cost 1 after Gibbers is played, got {cost_after}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
