"""
Test to reproduce the bug where Copy of Ka's effect doesn't apply to other cards.
"""

import unittest
import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from game_engine.game_engine import GameEngine
from game_engine.models.player import Player
from game_engine.models.card import Zone
from game_engine.models.game_state import GameState, Phase
from game_engine.data.card_loader import CardLoader


class TestCopyKaEffectBug(unittest.TestCase):
    """Test Copy of Ka's continuous effect application."""
    
    def setUp(self):
        """Set up test game with real cards."""
        # Load real cards from CSV
        csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
        loader = CardLoader(str(csv_path))
        all_cards = loader.load_cards()
        
        # Get specific cards we need
        self.ka = next(c for c in all_cards if c.name == "Ka")
        self.copy = next(c for c in all_cards if c.name == "Copy")
        
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
        
    def test_ka_buffs_itself_when_first_played(self):
        """Test that Ka's effect buffs itself when played alone."""
        from game_engine.rules.effects import EffectRegistry
        
        player = self.player1
        ka = self.ka
        
        # Set up Ka in hand
        ka.owner = player.player_id
        ka.controller = player.player_id
        ka.zone = Zone.HAND
        player.hand.append(ka)
        player.cc = 10
        
        # Play Ka
        success = self.game_engine.play_card(player, ka)
        self.assertTrue(success, "Ka should be successfully played")
        
        # Verify Ka is in play
        self.assertIn(ka, player.in_play)
        
        # Check Ka's strength - Ka's base strength is 9, with its own effect it becomes 11
        ka_strength = self.game_engine.get_card_stat(ka, "strength")
        print(f"\nKa base strength: {ka.strength}")
        print(f"Ka effective strength: {ka_strength}")
        self.assertEqual(ka_strength, 11,  
                        "Ka should have 11 strength (9 base + 2 from its effect)")
    
    def test_copy_of_ka_buffs_original_ka(self):
        """Test that Copy of Ka's effect buffs the original Ka."""
        from game_engine.rules.effects import EffectRegistry
        
        player = self.player1
        ka = self.ka
        copy = self.copy
        
        # Put Ka in play first
        ka.owner = player.player_id
        ka.controller = player.player_id
        ka.zone = Zone.IN_PLAY
        player.in_play.append(ka)
        
        # Set up Copy in hand
        copy.owner = player.player_id
        copy.controller = player.player_id
        copy.zone = Zone.HAND
        player.hand.append(copy)
        player.cc = 10
        
        # Check Ka's strength before playing Copy
        ka_strength_before = self.game_engine.get_card_stat(ka, "strength")
        print(f"\nKa strength before Copy: {ka_strength_before} (expected 11: 9 base + 2 from Ka)")
        self.assertEqual(ka_strength_before, 11, 
                        "Ka should have 11 strength (9 base + 2 from its own effect)")
        
        # Play Copy targeting Ka
        success = self.game_engine.play_card(player, copy, target=ka)
        self.assertTrue(success, "Copy should be successfully played")
        
        # Verify Copy transformed
        self.assertEqual(copy.name, "Copy of Ka")
        self.assertIn(copy, player.in_play)
        
        # Debug Copy's effects
        copy_effects = EffectRegistry.get_effects(copy)
        print(f"Copy of Ka has {len(copy_effects)} effects")
        for i, effect in enumerate(copy_effects):
            print(f"  Effect {i}: {type(effect).__name__}")
        
        # Now BOTH Ka and Copy of Ka should each buff all friendly cards by +2
        # Ka: 9 (base) + 2 (Ka's effect) + 2 (Copy of Ka's effect) = 13
        # Copy of Ka: 9 (base) + 2 (Ka's effect) + 2 (Copy of Ka's effect) = 13
        ka_strength_after = self.game_engine.get_card_stat(ka, "strength")
        copy_strength = self.game_engine.get_card_stat(copy, "strength")
        
        print(f"Ka strength after Copy: {ka_strength_after} (expected 13: 9 base + 2 from Ka + 2 from Copy)")
        print(f"Copy of Ka strength: {copy_strength} (expected 13: 9 base + 2 from Ka + 2 from Copy)")
        
        self.assertEqual(ka_strength_after, 13,
                        "Ka should have 13 strength (9 base + 2 from Ka + 2 from Copy of Ka)")
        self.assertEqual(copy_strength, 13,
                        "Copy of Ka should have 13 strength (9 base + 2 from Ka + 2 from Copy of Ka)")


if __name__ == '__main__':
    unittest.main()
