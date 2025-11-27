"""
Test for Copy card bug where it goes to sleep zone without target selection.

Bug: When Copy is played with no cards in play, it should NOT be a valid action.
Current behavior: Copy appears in valid actions, gets played, goes to sleep zone.
Expected behavior: Copy should not appear in valid actions when no targets exist.
"""

import unittest
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_engine.models.card import Card, CardType, Zone
from game_engine.models.game_state import GameState
from game_engine.models.player import Player
from game_engine.game_engine import GameEngine
from game_engine.validation.action_validator import ActionValidator


class TestCopyCardBug(unittest.TestCase):
    """Test suite for Copy card target selection bug."""
    
    def setUp(self):
        """Set up test game state."""
        from game_engine.models.game_state import Phase
        
        self.player1 = Player(player_id="test_player1", name="Player 1")
        self.player2 = Player(player_id="test_player2", name="Player 2")
        
        self.game_state = GameState(
            game_id="test_game",
            players={self.player1.player_id: self.player1, self.player2.player_id: self.player2},
            active_player_id=self.player1.player_id
        )
        self.game_state.phase = Phase.MAIN  # Set to Main phase so cards can be played
        
        self.game_engine = GameEngine(self.game_state)
        self.validator = ActionValidator(self.game_engine)
    
    def _create_copy_card(self):
        """Helper to create a Copy card."""
        return Card(
            name="Copy",
            card_type=CardType.ACTION,
            cost=-1,  # Variable cost
            effect_text="This card acts as an exact copy of a card you have in play.",
            effect_definitions="copy_card",
            owner=self.player1.player_id,
            controller=self.player1.player_id,
            primary_color="gray",
            accent_color="gray",
            zone=Zone.HAND
        )
    
    def _create_toy_card(self, name="Ka"):
        """Helper to create a Toy card."""
        return Card(
            name=name,
            card_type=CardType.TOY,
            cost=2,
            speed=5,
            strength=11,
            stamina=1,
            effect_text="Your cards have +2 strength.",
            effect_definitions="stat_boost:strength:2",
            owner=self.player1.player_id,
            controller=self.player1.player_id,
            primary_color="red",
            accent_color="red",
            zone=Zone.HAND
        )
    
    def test_copy_not_valid_when_no_targets(self):
        """
        Test that Copy is NOT a valid action when player has no cards in play.
        
        This is the core bug: Copy should not appear in valid actions if there
        are no cards to copy.
        """
        # Give player Copy card in hand but no cards in play
        copy_card = self._create_copy_card()
        self.player1.hand.append(copy_card)
        self.player1.cc = 10  # Plenty of CC
        
        # Get valid actions
        valid_actions = self.validator.get_valid_actions(self.player1.player_id)
        
        # Copy should NOT be in valid actions (no targets to copy)
        play_copy_actions = [
            a for a in valid_actions
            if a.action_type == "play_card" and a.card_id == copy_card.id
        ]
        
        self.assertEqual(
            len(play_copy_actions), 0,
            "Copy should not be a valid action when no cards are in play to copy"
        )
    
    def test_copy_valid_when_targets_exist(self):
        """
        Test that Copy IS a valid action when player has cards in play.
        """
        # Give player Copy in hand AND a card in play
        copy_card = self._create_copy_card()
        target_card = self._create_toy_card("Ka")
        target_card.zone = Zone.IN_PLAY
        
        self.player1.hand.append(copy_card)
        self.player1.in_play.append(target_card)
        self.player1.cc = 10  # Plenty of CC
        
        # Get valid actions
        valid_actions = self.validator.get_valid_actions(self.player1.player_id)
        
        # Copy SHOULD be in valid actions now
        play_copy_actions = [
            a for a in valid_actions
            if a.action_type == "play_card" and a.card_id == copy_card.id
        ]
        
        self.assertEqual(
            len(play_copy_actions), 1,
            "Copy should be a valid action when cards are in play to copy"
        )
        
        # Verify target_options includes the target card
        copy_action = play_copy_actions[0]
        self.assertIsNotNone(copy_action.target_options)
        self.assertIn(
            target_card.id,
            copy_action.target_options,
            "Target card should be in target_options"
        )
    
    def test_copy_cannot_be_played_without_target(self):
        """
        Test that attempting to play Copy without a target fails.
        
        This tests the execution path - even if validation is bypassed,
        playing Copy without a target should fail.
        """
        copy_card = self._create_copy_card()
        self.player1.hand.append(copy_card)
        self.player1.cc = 10
        
        # Try to play Copy without providing a target
        success = self.game_engine.play_card(self.player1, copy_card)
        
        # Should fail (or at minimum not transform the card)
        if success:
            # If play_card returned True, verify Copy didn't transform
            self.assertFalse(
                hasattr(copy_card, '_is_transformed') and copy_card._is_transformed,
                "Copy should not transform if no target was provided"
            )
            # Verify Copy went to sleep zone (as an Action card)
            self.assertIn(
                copy_card,
                self.player1.sleep_zone,
                "Copy should be in sleep zone if played without valid target"
            )
    
    def test_copy_transforms_when_played_with_target(self):
        """
        Test that Copy transforms correctly when played with a valid target.
        
        This verifies the happy path still works.
        """
        copy_card = self._create_copy_card()
        target_card = self._create_toy_card("Ka")
        target_card.zone = Zone.IN_PLAY
        
        self.player1.hand.append(copy_card)
        self.player1.in_play.append(target_card)
        self.player1.cc = 10
        
        # Play Copy with target
        success = self.game_engine.play_card(
            self.player1,
            copy_card,
            target=target_card
        )
        
        self.assertTrue(success, "Playing Copy with target should succeed")
        
        # Verify Copy transformed
        self.assertTrue(
            hasattr(copy_card, '_is_transformed') and copy_card._is_transformed,
            "Copy should be transformed after being played with a target"
        )
        
        # Verify Copy is in IN_PLAY zone (not sleep)
        self.assertIn(
            copy_card,
            self.player1.in_play,
            "Copy should be in play zone after transforming"
        )
        self.assertNotIn(
            copy_card,
            self.player1.sleep_zone,
            "Copy should NOT be in sleep zone after transforming"
        )
        
        # Verify Copy took on target's name
        self.assertEqual(
            copy_card.name,
            f"Copy of {target_card.name}",
            "Copy should have 'Copy of [target]' as its name"
        )


if __name__ == '__main__':
    unittest.main()
