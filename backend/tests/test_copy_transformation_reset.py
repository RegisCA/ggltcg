"""
Test for Copy card transformation reset bug (Issue #224).

Bug: When Copy transforms into "Copy of [Card]" and then gets sleeped or 
returned to hand, it should revert to the original "Copy" card with cost "?".

Expected behavior: Copy card should reset its transformation when leaving 
IN_PLAY zone or when moving to SLEEP zone.

Issue: https://github.com/RegisCA/ggltcg/issues/224
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


class TestCopyCardTransformationReset(unittest.TestCase):
    """Test suite for Copy card transformation reset."""
    
    def setUp(self):
        """Set up test game state."""
        self.player1 = Player(player_id="test_player1", name="Player 1")
        self.player2 = Player(player_id="test_player2", name="Player 2")
        
        self.game_state = GameState(
            game_id="test_game",
            players={
                self.player1.player_id: self.player1, 
                self.player2.player_id: self.player2
            },
            active_player_id=self.player1.player_id
        )
        self.game_state.phase = Phase.MAIN
        
        self.game_engine = GameEngine(self.game_state)
    
    def _create_copy_card(self) -> Card:
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
    
    def _create_ka_card(self) -> Card:
        """Helper to create a Ka card."""
        return Card(
            name="Ka",
            card_type=CardType.TOY,
            cost=2,
            speed=5,
            strength=11,
            stamina=1,
            effect_text="Your cards have +2 strength.",
            effect_definitions="stat_boost:strength:2",
            owner=self.player1.player_id,
            controller=self.player1.player_id,
            primary_color="#C74444",
            accent_color="#C74444",
            zone=Zone.HAND
        )
    
    def _transform_copy_into_ka(self, copy_card: Card, ka_card: Card) -> None:
        """Helper to transform Copy into a copy of Ka."""
        # Simulate what CopyEffect.apply() does
        copy_card._original_name = "Copy"
        copy_card._original_cost = -1
        copy_card._is_transformed = True
        
        copy_card.name = f"Copy of {ka_card.name}"
        copy_card.card_type = ka_card.card_type
        copy_card.cost = ka_card.cost
        copy_card.effect_text = ka_card.effect_text
        copy_card.effect_definitions = ka_card.effect_definitions
        copy_card.speed = ka_card.speed
        copy_card.strength = ka_card.strength
        copy_card.stamina = ka_card.stamina
        copy_card.current_stamina = ka_card.stamina
        copy_card.primary_color = ka_card.primary_color
        copy_card.accent_color = ka_card.accent_color
    
    def test_copy_resets_when_sleeped_from_play(self):
        """
        Test that Copy resets transformation when sleeped from IN_PLAY.
        
        Scenario:
        1. Player has Ka in play
        2. Player plays Copy, copying Ka
        3. Copy transforms into "Copy of Ka"
        4. Copy gets sleeped (defeated in tussle, etc.)
        5. Copy should revert to original "Copy" card
        """
        # Setup: Ka in play, Copy in hand
        ka_card = self._create_ka_card()
        ka_card.zone = Zone.IN_PLAY
        self.player1.in_play.append(ka_card)
        
        copy_card = self._create_copy_card()
        copy_card.zone = Zone.IN_PLAY  # Simulate Copy being played
        self.player1.in_play.append(copy_card)
        
        # Transform Copy into Copy of Ka
        self._transform_copy_into_ka(copy_card, ka_card)
        
        # Verify transformation occurred
        self.assertEqual(copy_card.name, "Copy of Ka")
        self.assertEqual(copy_card.cost, 2)
        self.assertTrue(hasattr(copy_card, '_is_transformed'))
        self.assertTrue(copy_card._is_transformed)
        
        # Sleep the Copy card (IN_PLAY → SLEEP)
        self.player1.move_card(copy_card, Zone.IN_PLAY, Zone.SLEEP)
        
        # Verify Copy reverted to original state
        self.assertEqual(copy_card.name, "Copy")
        self.assertEqual(copy_card.cost, -1)
        self.assertFalse(hasattr(copy_card, '_is_transformed'))
        self.assertFalse(hasattr(copy_card, '_original_name'))
        self.assertFalse(hasattr(copy_card, '_original_cost'))
        self.assertEqual(copy_card.zone, Zone.SLEEP)
    
    def test_copy_resets_when_returned_to_hand(self):
        """
        Test that Copy resets transformation when returned to hand from IN_PLAY.
        
        Scenario:
        1. Player has Ka in play
        2. Player plays Copy, copying Ka
        3. Copy transforms into "Copy of Ka"
        4. Copy gets returned to hand (e.g., via Wake effect)
        5. Copy should revert to original "Copy" card
        """
        # Setup: Ka in play, Copy in play (transformed)
        ka_card = self._create_ka_card()
        ka_card.zone = Zone.IN_PLAY
        self.player1.in_play.append(ka_card)
        
        copy_card = self._create_copy_card()
        copy_card.zone = Zone.IN_PLAY
        self.player1.in_play.append(copy_card)
        
        # Transform Copy into Copy of Ka
        self._transform_copy_into_ka(copy_card, ka_card)
        
        # Verify transformation occurred
        self.assertEqual(copy_card.name, "Copy of Ka")
        self.assertEqual(copy_card.cost, 2)
        
        # Return Copy to hand (IN_PLAY → HAND)
        self.player1.move_card(copy_card, Zone.IN_PLAY, Zone.HAND)
        
        # Verify Copy reverted to original state
        self.assertEqual(copy_card.name, "Copy")
        self.assertEqual(copy_card.cost, -1)
        self.assertFalse(hasattr(copy_card, '_is_transformed'))
        self.assertEqual(copy_card.zone, Zone.HAND)
    
    def test_copy_resets_when_discarded_from_hand(self):
        """
        Test that Copy resets transformation when discarded from hand.
        
        Scenario:
        1. Copy was previously transformed and returned to hand
        2. Copy gets discarded from hand (HAND → SLEEP)
        3. Copy should remain in original state (already reset when returning to hand)
        
        This tests the HAND → SLEEP transition explicitly.
        """
        # Setup: Copy in hand (simulate it was already returned and reset)
        copy_card = self._create_copy_card()
        copy_card.zone = Zone.HAND
        self.player1.hand.append(copy_card)
        
        # But let's say the transformation attributes somehow persisted
        # (edge case testing)
        copy_card._is_transformed = True
        copy_card._original_name = "Copy"
        copy_card._original_cost = -1
        copy_card.name = "Copy of Something"
        copy_card.cost = 3
        
        # Discard from hand (HAND → SLEEP)
        self.player1.move_card(copy_card, Zone.HAND, Zone.SLEEP)
        
        # Verify transformation is cleared
        self.assertEqual(copy_card.name, "Copy")
        self.assertEqual(copy_card.cost, -1)
        self.assertFalse(hasattr(copy_card, '_is_transformed'))
        self.assertEqual(copy_card.zone, Zone.SLEEP)
    
    def test_copy_reset_clears_all_transformation_attributes(self):
        """
        Test that all transformation-related attributes are removed.
        """
        copy_card = self._create_copy_card()
        ka_card = self._create_ka_card()
        
        copy_card.zone = Zone.IN_PLAY
        self.player1.in_play.append(copy_card)
        
        # Transform Copy
        self._transform_copy_into_ka(copy_card, ka_card)
        
        # Add some extra attributes that might be set
        copy_card._copied_effects = ["some", "effects"]
        
        # Verify all transformation attributes exist
        self.assertTrue(hasattr(copy_card, '_is_transformed'))
        self.assertTrue(hasattr(copy_card, '_original_name'))
        self.assertTrue(hasattr(copy_card, '_original_cost'))
        self.assertTrue(hasattr(copy_card, '_copied_effects'))
        
        # Sleep the card
        self.player1.move_card(copy_card, Zone.IN_PLAY, Zone.SLEEP)
        
        # Verify ALL transformation attributes are removed
        self.assertFalse(hasattr(copy_card, '_is_transformed'))
        self.assertFalse(hasattr(copy_card, '_original_name'))
        self.assertFalse(hasattr(copy_card, '_original_cost'))
        self.assertFalse(hasattr(copy_card, '_copied_effects'))
    
    def test_copy_preserves_owner_and_controller(self):
        """
        Test that Copy's owner and controller are preserved during reset.
        """
        copy_card = self._create_copy_card()
        ka_card = self._create_ka_card()
        
        copy_card.zone = Zone.IN_PLAY
        self.player1.in_play.append(copy_card)
        
        # Transform Copy
        self._transform_copy_into_ka(copy_card, ka_card)
        
        # Store original owner/controller
        original_owner = copy_card.owner
        original_controller = copy_card.controller
        
        # Sleep the card
        self.player1.move_card(copy_card, Zone.IN_PLAY, Zone.SLEEP)
        
        # Verify owner/controller unchanged
        self.assertEqual(copy_card.owner, original_owner)
        self.assertEqual(copy_card.controller, original_controller)
    
    def test_sleep_to_hand_does_not_reset(self):
        """
        Test that moving from SLEEP to HAND does NOT reset modifications.
        
        This is the unsleep/wake mechanic - cards return from sleep to hand
        without resetting.
        """
        copy_card = self._create_copy_card()
        copy_card.zone = Zone.SLEEP
        self.player1.sleep_zone.append(copy_card)
        
        # Add some modifications to test they're preserved
        copy_card.modifications = {"strength": 2}
        
        # Move from SLEEP to HAND (unsleep)
        self.player1.move_card(copy_card, Zone.SLEEP, Zone.HAND)
        
        # Verify modifications NOT cleared (SLEEP → HAND doesn't reset)
        # Actually, based on the current code, it WOULD reset because to_zone is HAND
        # and from_zone is SLEEP. Let me check the logic...
        # The condition is: if from_zone == Zone.IN_PLAY or to_zone == Zone.SLEEP
        # So SLEEP → HAND would NOT trigger reset (correct)
        self.assertEqual(copy_card.modifications, {"strength": 2})
        self.assertEqual(copy_card.zone, Zone.HAND)


if __name__ == "__main__":
    unittest.main()
