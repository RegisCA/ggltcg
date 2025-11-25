"""
Tests for Copy card refactor (Issue #77)

Validates that Copy transforms itself instead of creating duplicate cards,
preventing the card duplication exploit.
"""

import unittest
import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from game_engine.game_engine import GameEngine
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Card, CardType, Zone
from game_engine.rules.effects import EffectRegistry


class TestCopyRefactor(unittest.TestCase):
    """Test suite for Copy card transformation refactor."""

    def setUp(self):
        """Set up a game with Copy card for testing."""
        # Create players
        self.player1 = Player(player_id="p1", name="Player 1")
        self.player2 = Player(player_id="p2", name="Player 2")
        
        # Create game state
        self.game_state = GameState(
            game_id="test",
            players={"p1": self.player1, "p2": self.player2},
            active_player_id="p1",
            first_player_id="p1",
            turn_number=1
        )
        self.game_engine = GameEngine(self.game_state)
        
        # Set phase
        self.game_state.phase = Phase.MAIN
        
    def _create_toy_card(self, name, speed=2, strength=2, stamina=2, owner=None):
        """Helper to create a Toy card."""
        if owner is None:
            owner = self.player1
            
        card = Card(
            name=name,
            card_type=CardType.TOY,
            cost=3,
            speed=speed,
            strength=strength,
            stamina=stamina,
            current_stamina=stamina,
            effect_text="",
            owner=owner.player_id,
            controller=owner.player_id,
            primary_color="yellow",
            accent_color="blue"
        )
        return card
    
    def _create_action_card(self, name, owner=None):
        """Helper to create an Action card."""
        if owner is None:
            owner = self.player1
            
        card = Card(
            name=name,
            card_type=CardType.ACTION,
            cost=2,
            effect_text="Test action",
            owner=owner.player_id,
            controller=owner.player_id,
            primary_color="red",
            accent_color="white"
        )
        return card

    def _create_copy_card(self, owner=None):
        """Helper to create a Copy card."""
        if owner is None:
            owner = self.player1
            
        copy_card = Card(
            name="Copy",
            card_type=CardType.ACTION,
            cost=-1,
            effect_text="Transform this card into a copy of any card in play",
            owner=owner.player_id,
            controller=owner.player_id,
            primary_color="gray",
            accent_color="gray"
        )
        
        # Register Copy effect (manually instantiate and attach it)
        from game_engine.rules.effects.action_effects import CopyEffect
        copy_effect = CopyEffect(copy_card)
        # Store effect directly on card for test purposes
        if not hasattr(copy_card, '_test_effects'):
            copy_card._test_effects = []
        copy_card._test_effects.append(copy_effect)
        
        return copy_card

    def test_copy_transforms_itself_not_duplicate(self):
        """Test that Copy transforms itself instead of creating a duplicate card."""
        player = self.player1
        
        # Create target Toy in play
        target = self._create_toy_card("Demideca", speed=3, strength=3, stamina=3)
        player.in_play.append(target)
        
        # Create Copy card
        copy_card = self._create_copy_card()
        player.in_play.append(copy_card)
        
        # Record initial card count
        initial_count = len(player.in_play)
        self.assertEqual(initial_count, 2, "Should start with 2 cards in play")
        
        # Get Copy effect and apply it
        effects = copy_card._test_effects
        self.assertEqual(len(effects), 1, "Copy should have one effect")
        
        copy_effect = effects[0]
        copy_effect.apply(self.game_state, target=target)
        
        # Verify no duplicate created
        final_count = len(player.in_play)
        self.assertEqual(final_count, initial_count, 
                        "Card count should remain the same (no duplicate created)")
        
        # Verify Copy card is still in play (transformed, not replaced)
        self.assertIn(copy_card, player.in_play, 
                     "Copy card should still be in play")

    def test_copy_name_becomes_copy_of_target(self):
        """Test that Copy's name becomes 'Copy of [Target Name]'."""
        player = self.player1
        
        # Create target
        target = self._create_toy_card("Demideca")
        player.in_play.append(target)
        
        # Create and apply Copy
        copy_card = self._create_copy_card()
        player.in_play.append(copy_card)
        
        effects = copy_card._test_effects
        copy_effect = effects[0]
        copy_effect.apply(self.game_state, target=target)
        
        # Verify name transformation
        self.assertEqual(copy_card.name, "Copy of Demideca",
                        "Copy should be renamed to 'Copy of [Target]'")

    def test_copy_transforms_all_properties(self):
        """Test that Copy copies all relevant properties from target."""
        player = self.player1
        
        # Create target with specific properties
        target = self._create_toy_card("Demideca", speed=3, strength=4, stamina=5)
        target.effect_text = "Test effect"
        target.effect_definitions = "stat_boost:strength:1"
        player.in_play.append(target)
        
        # Create and apply Copy
        copy_card = self._create_copy_card()
        player.in_play.append(copy_card)
        
        # Store original Copy properties for comparison
        original_cost = copy_card.cost
        original_type = copy_card.card_type
        
        effects = copy_card._test_effects
        copy_effect = effects[0]
        copy_effect.apply(self.game_state, target=target)
        
        # Verify properties were copied
        self.assertEqual(copy_card.card_type, CardType.TOY, "Card type should be copied")
        self.assertEqual(copy_card.cost, 3, "Cost should be copied")
        self.assertEqual(copy_card.speed, 3, "Speed should be copied")
        self.assertEqual(copy_card.strength, 4, "Strength should be copied")
        self.assertEqual(copy_card.stamina, 5, "Stamina should be copied")
        self.assertEqual(copy_card.current_stamina, 5, "Current stamina should be copied")
        self.assertEqual(copy_card.effect_text, "Test effect", "Effect text should be copied")
        self.assertEqual(copy_card.effect_definitions, "stat_boost:strength:1", 
                        "Effect definitions should be copied")

    def test_copy_preserves_owner_and_zone(self):
        """Test that Copy preserves its owner and zone (doesn't copy those)."""
        player1 = self.player1
        player2 = self.player2
        
        # Create target owned by player2
        target = self._create_toy_card("Demideca", owner=player2)
        player2.in_play.append(target)
        
        # Create Copy owned by player1
        copy_card = self._create_copy_card(owner=player1)
        player1.in_play.append(copy_card)
        
        effects = copy_card._test_effects
        copy_effect = effects[0]
        copy_effect.apply(self.game_state, target=target)
        
        # Verify owner and controller are preserved
        self.assertEqual(copy_card.owner, player1.player_id, 
                        "Copy should keep its original owner")
        self.assertEqual(copy_card.controller, player1.player_id, 
                        "Copy should keep its original controller")
        
        # Verify it's still in player1's in_play zone
        self.assertIn(copy_card, player1.in_play, 
                     "Copy should stay in its owner's in_play zone")
        self.assertNotIn(copy_card, player2.in_play, 
                        "Copy should not be in target's owner's zone")

    def test_copy_stores_original_properties(self):
        """Test that Copy stores original properties for reverting."""
        player = self.player1
        
        # Create target and Copy
        target = self._create_toy_card("Demideca")
        player.in_play.append(target)
        
        copy_card = self._create_copy_card()
        player.in_play.append(copy_card)
        
        effects = copy_card._test_effects
        copy_effect = effects[0]
        copy_effect.apply(self.game_state, target=target)
        
        # Verify original properties are stored
        self.assertTrue(hasattr(copy_card, '_original_name'), 
                       "Should store original name")
        self.assertEqual(copy_card._original_name, "Copy", 
                        "Original name should be 'Copy'")
        
        self.assertTrue(hasattr(copy_card, '_original_cost'), 
                       "Should store original cost")
        self.assertEqual(copy_card._original_cost, -1, 
                        "Original cost should be -1")
        
        self.assertTrue(hasattr(copy_card, '_is_transformed'), 
                       "Should mark as transformed")
        self.assertTrue(copy_card._is_transformed, 
                       "Should be marked as transformed")

    def test_copy_works_on_action_cards(self):
        """Test that Copy can copy Action cards (not just Toys)."""
        player = self.player1
        
        # Create an Action card target
        target = self._create_action_card("Test Action")
        target.effect_text = "Do something cool"
        player.in_play.append(target)
        
        # Create Copy
        copy_card = self._create_copy_card()
        player.in_play.append(copy_card)
        
        # Get valid targets
        effects = copy_card._test_effects
        copy_effect = effects[0]
        valid_targets = copy_effect.get_valid_targets(self.game_state, player)
        
        # Verify Action card is a valid target
        self.assertIn(target, valid_targets, 
                     "Action cards should be valid targets for Copy")
        
        # Apply Copy
        copy_effect.apply(self.game_state, target=target)
        
        # Verify transformation worked
        self.assertEqual(copy_card.card_type, CardType.ACTION, 
                        "Should copy Action card type")
        self.assertEqual(copy_card.name, "Copy of Test Action", 
                        "Should have correct name")
        self.assertEqual(copy_card.effect_text, "Do something cool", 
                        "Should copy effect text")

    def test_copy_no_duplicate_with_multiple_uses(self):
        """Test that using Copy multiple times doesn't create duplicates."""
        player = self.player1
        
        # Create multiple targets
        target1 = self._create_toy_card("Demideca")
        target2 = self._create_toy_card("Raggy")
        player.in_play.extend([target1, target2])
        
        # Create two Copy cards
        copy1 = self._create_copy_card()
        copy2 = self._create_copy_card()
        player.in_play.extend([copy1, copy2])
        
        # Initial count: 4 cards (2 targets + 2 Copies)
        initial_count = len(player.in_play)
        self.assertEqual(initial_count, 4, "Should start with 4 cards")
        
        # Apply first Copy
        effects1 = copy1._test_effects
        effects1[0].apply(self.game_state, target=target1)
        
        # Apply second Copy
        effects2 = copy2._test_effects
        effects2[0].apply(self.game_state, target=target2)
        
        # Verify no duplicates created
        final_count = len(player.in_play)
        self.assertEqual(final_count, initial_count, 
                        "Card count should remain 4 (no duplicates)")
        
        # Verify both Copies transformed correctly
        self.assertEqual(copy1.name, "Copy of Demideca")
        self.assertEqual(copy2.name, "Copy of Raggy")

    def test_copy_stays_in_play_after_transformation(self):
        """Test that Copy stays in play after being played (integration test with GameEngine)."""
        player = self.player1
        
        # Create and play a Toy target
        target = self._create_toy_card("Ka", speed=5, strength=11, stamina=1)
        target.zone = Zone.IN_PLAY
        player.in_play.append(target)
        
        # Create Copy card in hand
        copy_card = self._create_copy_card()
        copy_card.zone = Zone.HAND
        player.hand.append(copy_card)
        
        # Give player enough CC
        player.cc = 10
        
        # Play Copy through GameEngine
        success = self.game_engine.play_card(player, copy_card, target=target)
        
        # Verify Copy was successfully played
        self.assertTrue(success, "Copy should be successfully played")
        
        # Verify Copy is in IN_PLAY zone, not SLEEP
        self.assertIn(copy_card, player.in_play, 
                     "Copy should be IN_PLAY after transformation")
        self.assertNotIn(copy_card, player.sleep_zone, 
                        "Copy should NOT be in sleep zone")
        self.assertNotIn(copy_card, player.hand, 
                        "Copy should no longer be in hand")
        
        # Verify transformation occurred
        self.assertEqual(copy_card.name, "Copy of Ka", 
                        "Copy should have transformed name")
        self.assertEqual(copy_card.card_type, CardType.TOY, 
                        "Copy should have Toy card type")
        self.assertEqual(copy_card.speed, 5, "Copy should have Ka's speed")
        self.assertEqual(copy_card.strength, 11, "Copy should have Ka's strength")
        
        # Verify _is_transformed flag is set
        self.assertTrue(hasattr(copy_card, '_is_transformed'), 
                       "Copy should have _is_transformed attribute")
        self.assertTrue(copy_card._is_transformed, 
                       "Copy should be marked as transformed")

    def test_copy_of_ka_gets_ka_effects(self):
        """Test that Copy of Ka gets Ka's continuous effect (+2 strength for each other card)."""
        from game_engine.rules.effects import EffectRegistry
        from game_engine.data.card_loader import CardLoader
        from pathlib import Path
        
        player = self.player1
        
        # Load real Ka card from CSV
        csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
        loader = CardLoader(str(csv_path))
        all_cards = loader.load_cards()
        ka = next(c for c in all_cards if c.name == "Ka")
        
        # Set Ka's owner and put in play
        ka.owner = player.player_id
        ka.controller = player.player_id
        ka.zone = Zone.IN_PLAY
        player.in_play.append(ka)
        
        # Create Copy card
        copy_card = self._create_copy_card()
        copy_card.zone = Zone.HAND
        player.hand.append(copy_card)
        player.cc = 10
        
        # Play Copy targeting Ka through GameEngine
        success = self.game_engine.play_card(player, copy_card, target=ka)
        self.assertTrue(success, "Copy should be successfully played")
        
        # Verify Copy transformed into Ka
        self.assertEqual(copy_card.name, "Copy of Ka")
        self.assertEqual(copy_card.effect_text, ka.effect_text)
        self.assertEqual(copy_card.effect_definitions, "stat_boost:strength:2")
        
        # Verify Copy has the effect instances
        self.assertTrue(hasattr(copy_card, '_copied_effects'), 
                       "Copy should have _copied_effects attribute")
        self.assertEqual(len(copy_card._copied_effects), 1, 
                        "Copy should have 1 effect")
        
        # Verify EffectRegistry returns the copied effects
        copy_effects = EffectRegistry.get_effects(copy_card)
        self.assertEqual(len(copy_effects), 1, 
                        "EffectRegistry should return 1 effect for Copy of Ka")
        
        # Verify Ka's effect applies to Copy
        ka_effects = EffectRegistry.get_effects(ka)
        self.assertEqual(len(ka_effects), 1, "Ka should have 1 effect")
        
        # Both Ka and Copy of Ka should boost each other's strength by +2
        # Get modified strength through game engine
        ka_strength = self.game_engine.get_card_stat(ka, "strength")
        copy_strength = self.game_engine.get_card_stat(copy_card, "strength")
        
        # Base strength is 11, with one other card in play (+2)
        self.assertEqual(ka_strength, 13, 
                        "Ka should have 11 (base) + 2 (Copy of Ka's effect) = 13 strength")
        self.assertEqual(copy_strength, 13, 
                        "Copy of Ka should have 11 (base) + 2 (Ka's effect) = 13 strength")


if __name__ == '__main__':
    unittest.main()
