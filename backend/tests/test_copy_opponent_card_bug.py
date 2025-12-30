"""
Test for Copy card bug where it can copy opponent's cards.

Bug: Copy is showing opponent's cards as valid targets.
Expected: Copy should only be able to copy the player's own cards.
"""

import unittest
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_engine.models.card import Card, CardType, Zone
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.game_engine import GameEngine
from game_engine.validation.action_validator import ActionValidator


class TestCopyOpponentCardBug(unittest.TestCase):
    """Test suite for Copy card opponent targeting bug."""
    
    def setUp(self):
        """Set up test game state."""
        self.player1 = Player(player_id="player1", name="Player 1")
        self.player2 = Player(player_id="player2", name="Player 2")
        
        self.game_state = GameState(
            game_id="test_game",
            players={self.player1.player_id: self.player1, self.player2.player_id: self.player2},
            active_player_id=self.player1.player_id
        )
        self.game_state.phase = Phase.MAIN
        
        self.game_engine = GameEngine(self.game_state)
        self.validator = ActionValidator(self.game_engine)
    
    def _create_copy_card(self, owner_id):
        """Helper to create a Copy card."""
        return Card(
            name="Copy",
            card_type=CardType.ACTION,
            cost=-1,
            effect_text="This card acts as an exact copy of a card you have in play.",
            effect_definitions="copy_card",
            owner=owner_id,
            controller=owner_id,
            primary_color="gray",
            accent_color="gray",
            zone=Zone.HAND
        )
    
    def _create_toy_card(self, name, owner_id):
        """Helper to create a Toy card."""
        return Card(
            name=name,
            card_type=CardType.TOY,
            cost=2,
            speed=5,
            strength=3,
            stamina=3,
            effect_text="",
            effect_definitions="",
            owner=owner_id,
            controller=owner_id,
            primary_color="red",
            accent_color="red",
            zone=Zone.IN_PLAY
        )
    
    def test_copy_cannot_target_opponent_cards(self):
        """
        Test that Copy cannot target cards in opponent's play zone.
        
        Setup:
        - Player 1 has Copy in hand
        - Player 1 has no cards in play
        - Player 2 has a card in play
        
        Expected: Copy should have NO valid targets (should not show opponent's cards)
        """
        # Player 1 has Copy in hand
        copy_card = self._create_copy_card(self.player1.player_id)
        self.player1.hand.append(copy_card)
        self.player1.cc = 10
        
        # Player 2 has a toy in play
        opponent_toy = self._create_toy_card("Ka", self.player2.player_id)
        self.player2.in_play.append(opponent_toy)
        
        # Get valid actions for player 1
        valid_actions = self.validator.get_valid_actions(self.player1.player_id)
        
        # Copy should NOT be a valid action (no own cards to copy)
        play_copy_actions = [
            a for a in valid_actions
            if a.action_type == "play_card" and a.card_id == copy_card.id
        ]
        
        self.assertEqual(
            len(play_copy_actions), 0,
            f"Copy should not be valid when only opponent has cards in play. "
            f"Found {len(play_copy_actions)} actions"
        )
    
    def test_copy_only_targets_own_cards_when_both_have_cards(self):
        """
        Test that Copy only targets player's own cards even when opponent has cards.
        
        Setup:
        - Player 1 has Copy in hand
        - Player 1 has Knight in play
        - Player 2 has Ka in play
        
        Expected: Copy should only show Knight as a valid target, not Ka
        """
        # Player 1 has Copy in hand and Knight in play
        copy_card = self._create_copy_card(self.player1.player_id)
        self.player1.hand.append(copy_card)
        self.player1.cc = 10
        
        player1_toy = self._create_toy_card("Knight", self.player1.player_id)
        self.player1.in_play.append(player1_toy)
        
        # Player 2 has Ka in play
        player2_toy = self._create_toy_card("Ka", self.player2.player_id)
        self.player2.in_play.append(player2_toy)
        
        # Get valid actions for player 1
        valid_actions = self.validator.get_valid_actions(self.player1.player_id)
        
        # Copy should be valid with ONE target
        play_copy_actions = [
            a for a in valid_actions
            if a.action_type == "play_card" and a.card_id == copy_card.id
        ]
        
        self.assertEqual(
            len(play_copy_actions), 1,
            "Copy should be a valid action when player has cards in play"
        )
        
        # Check target options - should only include Knight, not Ka
        copy_action = play_copy_actions[0]
        self.assertIsNotNone(copy_action.target_options)
        self.assertEqual(
            len(copy_action.target_options), 1,
            f"Copy should have exactly 1 target option (Knight), got {len(copy_action.target_options)}"
        )
        self.assertIn(
            player1_toy.id,
            copy_action.target_options,
            "Copy should include player's Knight as a valid target"
        )
        self.assertNotIn(
            player2_toy.id,
            copy_action.target_options,
            "Copy should NOT include opponent's Ka as a valid target"
        )


if __name__ == '__main__':
    unittest.main()
