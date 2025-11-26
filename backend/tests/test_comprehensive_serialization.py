"""
Comprehensive serialization tests for Card, Player, and GameState.

Tests that all fields survive the save/load cycle and regression tests
for bugs discovered in issue #77.

Test Coverage:
1. All Card fields (base stats, colors, zones, etc.)
2. Card modifications and transformations
3. Effect definitions preservation
4. Cards in different zones (hand, in_play, sleep_zone)
5. Multi-effect cards
6. Edge cases from issue #77
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from game_engine.models.card import Card, CardType, Zone
from game_engine.models.player import Player
from game_engine.models.game_state import GameState, Phase
from game_engine.game_engine import GameEngine
from game_engine.data.card_loader import CardLoader
from api.serialization import (
    serialize_card,
    deserialize_card,
    serialize_player,
    deserialize_player,
    serialize_game_state,
    deserialize_game_state,
)
from game_engine.rules.effects.effect_registry import EffectFactory


# Load cards from CSV once for all tests
cards_csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
loader = CardLoader(str(cards_csv_path))
all_cards = loader.load_cards_dict()


class TestCardSerialization:
    """Test that all Card fields survive serialization."""
    
    def test_basic_toy_card_fields(self):
        """Test all fields of a basic Toy card are preserved."""
        original = Card(
            id="test-id-123",
            name="Ka",
            card_type=CardType.TOY,
            cost=3,
            effect_text="Buff adjacent toys",
            effect_definitions="stat_boost:strength:2",
            speed=5,
            strength=9,
            stamina=9,
            primary_color="#FF0000",
            accent_color="#AA0000",
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
            modifications={"strength": 2, "speed": -1},
        )
        # Set damaged stamina after __post_init__
        original.current_stamina = 7
        
        serialized = serialize_card(original)
        restored = deserialize_card(serialized)
        
        # Check all fields
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.card_type == original.card_type
        assert restored.cost == original.cost
        assert restored.effect_text == original.effect_text
        assert restored.effect_definitions == original.effect_definitions
        assert restored.speed == original.speed
        assert restored.strength == original.strength
        assert restored.stamina == original.stamina
        assert restored.primary_color == original.primary_color
        assert restored.accent_color == original.accent_color
        assert restored.owner == original.owner
        assert restored.controller == original.controller
        assert restored.zone == original.zone
        assert restored.current_stamina == original.current_stamina
        assert restored.modifications == original.modifications
    
    def test_action_card_fields(self):
        """Test Action cards (no stats) are preserved."""
        original = Card(
            name="Wake",
            card_type=CardType.ACTION,
            cost=1,
            effect_text="Unsleep up to 2 cards",
            effect_definitions="unsleep:2",
            speed=None,
            strength=None,
            stamina=None,
            owner="player2",
            controller="player2",
            zone=Zone.HAND,
        )
        
        serialized = serialize_card(original)
        restored = deserialize_card(serialized)
        
        assert restored.name == original.name
        assert restored.card_type == CardType.ACTION
        assert restored.speed is None
        assert restored.strength is None
        assert restored.stamina is None
        assert restored.zone == Zone.HAND
    
    def test_empty_effect_definitions(self):
        """Test cards with no effect_definitions (e.g., vanilla toys)."""
        original = Card(
            name="Plain Toy",
            card_type=CardType.TOY,
            cost=2,
            effect_text="No special effect",
            effect_definitions="",  # Empty string
            speed=5,
            strength=5,
            stamina=5,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
        )
        
        serialized = serialize_card(original)
        restored = deserialize_card(serialized)
        
        assert restored.effect_definitions == ""
        assert restored.name == original.name
    
    def test_missing_effect_definitions_attribute(self):
        """Test cards that might not have effect_definitions attribute (legacy)."""
        original = Card(
            name="Legacy Card",
            card_type=CardType.TOY,
            cost=2,
            effect_text="Legacy effect",
            speed=5,
            strength=5,
            stamina=5,
            owner="player1",
            controller="player1",
        )
        # Explicitly ensure it has the attribute (even if empty)
        # This tests the getattr() fallback in serialize_card
        
        serialized = serialize_card(original)
        restored = deserialize_card(serialized)
        
        # Should default to empty string
        assert restored.effect_definitions == ""
    
    def test_card_in_different_zones(self):
        """Test cards are preserved correctly in different zones."""
        zones = [Zone.HAND, Zone.IN_PLAY, Zone.SLEEP]
        
        for zone in zones:
            original = Card(
                name="Test Card",
                card_type=CardType.TOY,
                cost=1,
                effect_text="Test",
                speed=3,
                strength=3,
                stamina=3,
                owner="player1",
                controller="player1",
                zone=zone,
            )
            
            serialized = serialize_card(original)
            restored = deserialize_card(serialized)
            
            assert restored.zone == zone
    
    def test_modifications_not_mutated_during_serialization(self):
        """Regression test for issue #77 bug #3: Dict mutation bug."""
        original = Card(
            name="Test Card",
            card_type=CardType.TOY,
            cost=1,
            effect_text="Test",
            speed=3,
            strength=3,
            stamina=3,
            owner="player1",
            controller="player1",
            modifications={"strength": 2},
        )
        
        # Store original modifications reference
        original_mods = original.modifications
        original_mods_copy = original.modifications.copy()
        
        # Serialize (this should NOT mutate original.modifications)
        serialized = serialize_card(original)
        
        # Verify original wasn't mutated
        assert original.modifications == original_mods_copy
        assert original.modifications is original_mods  # Same object
        assert '_is_transformed' not in original.modifications


class TestTransformedCardSerialization:
    """Test serialization of transformed/copied cards."""
    
    def test_transformed_copy_card(self):
        """Test that transformed Copy cards preserve _is_transformed flag."""
        original = Card(
            name="Copy of Ka",
            card_type=CardType.TOY,
            cost=3,
            effect_text="Buff adjacent toys",
            effect_definitions="stat_boost:strength:2",  # Single effect
            speed=5,
            strength=9,
            stamina=9,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
        )
        
        # Mark as transformed
        original._is_transformed = True
        original._copied_effects = EffectFactory.parse_effects(
            original.effect_definitions,
            original
        )
        
        serialized = serialize_card(original)
        restored = deserialize_card(serialized)
        
        # Check transformation preserved
        assert hasattr(restored, '_is_transformed')
        assert restored._is_transformed is True
        
        # Check _copied_effects recreated
        assert hasattr(restored, '_copied_effects')
        assert len(restored._copied_effects) > 0
        
        # Check effect_definitions preserved (source of truth)
        assert restored.effect_definitions == original.effect_definitions
    
    def test_non_transformed_card_no_flag(self):
        """Test that normal cards don't get _is_transformed flag."""
        original = Card(
            name="Ka",
            card_type=CardType.TOY,
            cost=3,
            effect_text="Buff adjacent toys",
            effect_definitions="stat_boost:strength:2",
            speed=5,
            strength=9,
            stamina=9,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
        )
        
        serialized = serialize_card(original)
        restored = deserialize_card(serialized)
        
        # Should not have transformation flag
        assert not hasattr(restored, '_is_transformed') or restored._is_transformed is False


class TestMultiEffectCards:
    """Test cards with multiple effects in effect_definitions."""
    
    def test_multi_effect_parsing(self):
        """Test cards with multiple semicolon-separated effects."""
        original = Card(
            name="Multi Effect Card",
            card_type=CardType.TOY,
            cost=4,
            effect_text="Multiple buffs",
            effect_definitions="stat_boost:strength:2;stat_boost:speed:1;stat_boost:stamina:3",  # Semicolon-separated
            speed=5,
            strength=7,
            stamina=8,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
        )
        
        serialized = serialize_card(original)
        restored = deserialize_card(serialized)
        
        # Parse effects from restored card
        effects = EffectFactory.parse_effects(restored.effect_definitions, restored)
        
        # Should have 3 effects
        assert len(effects) == 3
        assert restored.effect_definitions == original.effect_definitions


class TestPlayerSerialization:
    """Test Player serialization with cards in different zones."""
    
    def test_player_with_cards_in_all_zones(self):
        """Test player with cards in hand, in_play, and sleep_zone."""
        hand_card = Card(
            name="Hand Card",
            card_type=CardType.TOY,
            cost=1,
            effect_text="In hand",
            effect_definitions="",
            speed=3,
            strength=3,
            stamina=3,
            owner="player1",
            controller="player1",
            zone=Zone.HAND,
        )
        
        play_card = Card(
            name="Play Card",
            card_type=CardType.TOY,
            cost=2,
            effect_text="In play",
            effect_definitions="stat_boost:strength:1",
            speed=4,
            strength=4,
            stamina=4,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
        )
        
        sleep_card = Card(
            name="Sleep Card",
            card_type=CardType.ACTION,
            cost=1,
            effect_text="Sleeped",
            effect_definitions="unsleep:1",
            owner="player1",
            controller="player1",
            zone=Zone.SLEEP,
        )
        
        original_player = Player(
            player_id="player1",
            name="Test Player",
            cc=10,
            hand=[hand_card],
            in_play=[play_card],
            sleep_zone=[sleep_card],
            direct_attacks_this_turn=1,
        )
        
        serialized = serialize_player(original_player)
        restored = deserialize_player(serialized)
        
        # Check player fields
        assert restored.player_id == original_player.player_id
        assert restored.name == original_player.name
        assert restored.cc == original_player.cc
        assert restored.direct_attacks_this_turn == original_player.direct_attacks_this_turn
        
        # Check all zones preserved
        assert len(restored.hand) == 1
        assert len(restored.in_play) == 1
        assert len(restored.sleep_zone) == 1
        
        # Check cards preserved correctly
        assert restored.hand[0].name == "Hand Card"
        assert restored.hand[0].zone == Zone.HAND
        
        assert restored.in_play[0].name == "Play Card"
        assert restored.in_play[0].zone == Zone.IN_PLAY
        assert restored.in_play[0].effect_definitions == "stat_boost:strength:1"
        
        assert restored.sleep_zone[0].name == "Sleep Card"
        assert restored.sleep_zone[0].zone == Zone.SLEEP


class TestGameStateSerialization:
    """Test complete GameState serialization."""
    
    def test_complete_game_state_cycle(self):
        """Test full game state with two players and multiple cards."""
        # Create cards for player 1
        p1_card1 = Card(
            name="Ka",
            card_type=CardType.TOY,
            cost=3,
            effect_text="Buff",
            effect_definitions="stat_boost:strength:2",
            speed=5,
            strength=9,
            stamina=9,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
        )
        
        p1_card2 = Card(
            name="Wake",
            card_type=CardType.ACTION,
            cost=1,
            effect_text="Unsleep",
            effect_definitions="unsleep:2",
            owner="player1",
            controller="player1",
            zone=Zone.HAND,
        )
        
        # Create cards for player 2
        p2_card1 = Card(
            name="Knight",
            card_type=CardType.TOY,
            cost=4,
            effect_text="Defender",
            effect_definitions="",
            speed=7,
            strength=8,
            stamina=10,
            owner="player2",
            controller="player2",
            zone=Zone.IN_PLAY,
        )
        
        player1 = Player(
            player_id="player1",
            name="Alice",
            cc=8,
            hand=[p1_card2],
            in_play=[p1_card1],
            sleep_zone=[],
            direct_attacks_this_turn=0,
        )
        
        player2 = Player(
            player_id="player2",
            name="Bob",
            cc=5,
            hand=[],
            in_play=[p2_card1],
            sleep_zone=[],
            direct_attacks_this_turn=1,
        )
        
        original_state = GameState(
            game_id="test-game-123",
            players={"player1": player1, "player2": player2},
            active_player_id="player1",
            turn_number=3,
            phase=Phase.MAIN,
            first_player_id="player2",
            winner_id=None,
            game_log=["Game started", "Turn 1", "Turn 2"],
            play_by_play=["Alice played Ka", "Bob played Knight"],
        )
        
        serialized = serialize_game_state(original_state)
        restored = deserialize_game_state(serialized)
        
        # Check game state fields
        assert restored.game_id == original_state.game_id
        assert restored.active_player_id == original_state.active_player_id
        assert restored.turn_number == original_state.turn_number
        assert restored.phase == original_state.phase
        assert restored.first_player_id == original_state.first_player_id
        assert restored.winner_id == original_state.winner_id
        assert restored.game_log == original_state.game_log
        assert restored.play_by_play == original_state.play_by_play
        
        # Check players preserved
        assert len(restored.players) == 2
        assert "player1" in restored.players
        assert "player2" in restored.players
        
        # Check player 1
        p1 = restored.players["player1"]
        assert p1.name == "Alice"
        assert p1.cc == 8
        assert len(p1.hand) == 1
        assert len(p1.in_play) == 1
        assert p1.hand[0].name == "Wake"
        assert p1.in_play[0].name == "Ka"
        assert p1.in_play[0].effect_definitions == "stat_boost:strength:2"
        
        # Check player 2
        p2 = restored.players["player2"]
        assert p2.name == "Bob"
        assert p2.cc == 5
        assert len(p2.in_play) == 1
        assert p2.in_play[0].name == "Knight"
        assert p2.direct_attacks_this_turn == 1


class TestIssue77Regressions:
    """Regression tests for bugs found in issue #77."""
    
    def test_effect_definitions_not_lost_on_serialize(self):
        """
        Regression test for issue #77 bug #2:
        serialize_card() wasn't saving effect_definitions.
        """
        card_with_effects = Card(
            name="Ka",
            card_type=CardType.TOY,
            cost=3,
            effect_text="Buff adjacent toys",
            effect_definitions="stat_boost:strength:2,stat_boost:stamina:2",
            speed=5,
            strength=9,
            stamina=9,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
        )
        
        serialized = serialize_card(card_with_effects)
        
        # Verify effect_definitions is in serialized data
        assert 'effect_definitions' in serialized
        assert serialized['effect_definitions'] == "stat_boost:strength:2,stat_boost:stamina:2"
        
        # Verify it survives deserialization
        restored = deserialize_card(serialized)
        assert restored.effect_definitions == card_with_effects.effect_definitions
    
    def test_copy_effect_full_cycle_with_stats(self):
        """
        Full integration test: Copy effect should preserve stats through save/load.
        This tests the complete fix for issue #77.
        """
        # Create Ka (has stat_boost effects)
        ka = Card(
            name="Ka",
            card_type=CardType.TOY,
            cost=3,
            effect_text="Buff adjacent toys",
            effect_definitions="stat_boost:strength:2",  # Single effect
            speed=5,
            strength=9,
            stamina=9,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
        )
        
        # Create transformed Copy (copies Ka)
        copy_card = Card(
            name="Copy of Ka",
            card_type=CardType.TOY,
            cost=3,
            effect_text="Buff adjacent toys",
            effect_definitions="stat_boost:strength:2",  # Single effect
            speed=5,
            strength=9,
            stamina=9,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
        )
        copy_card._is_transformed = True
        copy_card._copied_effects = EffectFactory.parse_effects(
            copy_card.effect_definitions,
            copy_card
        )
        
        # Create game state
        player1 = Player(
            player_id="player1",
            name="Player 1",
            cc=6,
            hand=[],
            in_play=[ka, copy_card],
            sleep_zone=[],
        )
        
        player2 = Player(
            player_id="player2",
            name="Player 2",
            cc=6,
            hand=[],
            in_play=[],
            sleep_zone=[],
        )
        
        game_state = GameState(
            game_id="test-copy-game",
            players={"player1": player1, "player2": player2},
            active_player_id="player1",
            turn_number=1,
            phase=Phase.MAIN,
            first_player_id="player1",
        )
        
        # Create engine and check stats BEFORE serialization
        engine_before = GameEngine(game_state=game_state)
        ka_strength_before = engine_before.get_card_stat(ka, 'strength')
        
        # Ka should be: 9 base + 2 (from Ka's own effect) + 2 (from Copy's effect) = 13
        # Note: This assumes both Ka and Copy buff adjacent cards
        assert ka_strength_before == 13, f"Expected 13, got {ka_strength_before}"
        
        # Serialize and deserialize
        serialized = serialize_game_state(game_state)
        restored_state = deserialize_game_state(serialized)
        
        # Create new engine with restored state
        engine_after = GameEngine(game_state=restored_state)
        restored_ka = restored_state.players["player1"].in_play[0]
        restored_copy = restored_state.players["player1"].in_play[1]
        
        # Verify Copy is still transformed
        assert hasattr(restored_copy, '_is_transformed')
        assert restored_copy._is_transformed is True
        assert hasattr(restored_copy, '_copied_effects')
        assert len(restored_copy._copied_effects) > 0
        
        # Check Ka's strength AFTER deserialization
        ka_strength_after = engine_after.get_card_stat(restored_ka, 'strength')
        
        # Should still be 13 (9 base + 2 from Ka + 2 from Copy)
        assert ka_strength_after == 13, f"Expected 13 after deserialization, got {ka_strength_after}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
