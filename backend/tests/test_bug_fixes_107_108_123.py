"""
Tests for bug fixes #107, #108, and #123.

#107: Sleeping cards should move to owner's Sleep zone (not controller's)
#123: Buffed stats should only apply to cards in IN_PLAY zone
#108: Frontend layout (not tested here - manual verification)
"""

import pytest
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_engine.game_engine import GameEngine
from game_engine.models.game_state import GameState
from game_engine.models.player import Player
from game_engine.models.card import Card, CardType, Zone
from game_engine.data.card_loader import CardLoader



class TestBug107SleepToOwnerZone:
    """
    Test that cards are always sleeped to their owner's zone, not controller's zone.
    
    This is critical for Twist + Tussle/Toynado interactions.
    """
    
    def test_twist_then_tussle_sleeps_to_original_owner(self):
        """
        Issue #107: When a card is stolen via Twist, then sleeped via tussle,
        it should return to the original owner's sleep zone.
        
        Steps:
        1. Player 2 plays Clean (Owner: P2, Controller: P2)
        2. Player 1 plays Twist to steal Clean (Owner: P2, Controller: P1)
        3. Player 2 plays Knight and tussles Clean
        4. Knight wins (6 STR vs 2 STA)
        5. Clean should sleep to Player 2's zone (the owner)
        """
        # Setup game
        player1 = Player(player_id="player1", name="Player 1")
        player2 = Player(player_id="player2", name="Player 2")
        game_state = GameState(
            game_id="test_game",
            players={player1.player_id: player1, player2.player_id: player2},
            active_player_id=player2.player_id
        )
        
        # Load cards from CSV
        csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
        loader = CardLoader(str(csv_path))
        all_cards = loader.load_cards()
        card_data = {card.name: card for card in all_cards}
        
        # Create cards
        snuggles = Card(
            name="Clean",
            card_type=CardType.TOY,
            cost=1,
            effect_text=card_data["Clean"].effect_text,
            speed=card_data["Clean"].speed,
            strength=card_data["Clean"].strength,
            stamina=card_data["Clean"].stamina,
            primary_color=card_data["Clean"].primary_color,
            accent_color=card_data["Clean"].accent_color,
            owner="player2",
            controller="player2",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Clean"].effect_definitions
        )
        snuggles.current_stamina = snuggles.stamina
        
        knight = Card(
            name="Knight",
            card_type=CardType.TOY,
            cost=3,
            effect_text=card_data["Knight"].effect_text,
            speed=card_data["Knight"].speed,
            strength=card_data["Knight"].strength,
            stamina=card_data["Knight"].stamina,
            primary_color=card_data["Knight"].primary_color,
            accent_color=card_data["Knight"].accent_color,
            owner="player2",
            controller="player2",
            zone=Zone.HAND,
            effect_definitions=card_data["Knight"].effect_definitions
        )
        knight.current_stamina = knight.stamina
        
        # Setup: Clean is in play (owned by P2, controlled by P1 after Twist)
        player1.cc = 10
        player1.in_play.append(snuggles)
        snuggles.controller = "player1"  # Simulate Twist effect
        
        # Knight is in P2's hand
        player2.cc = 10
        player2.hand.append(knight)
        
        # Create engine
        engine = GameEngine(game_state)
        
        # Player 2 plays Knight
        engine.play_card(player2, knight)
        
        # Verify Knight is in play
        assert knight in player2.in_play
        assert knight.zone == Zone.IN_PLAY
        
        # Player 2 tussles Clean with Knight
        engine.initiate_tussle(player2, knight, snuggles)
        
        # Verify Clean is sleeped to OWNER's (Player 2) sleep zone
        assert snuggles not in player1.in_play
        assert snuggles not in player1.sleep_zone  # BUG: This was happening before fix
        assert snuggles in player2.sleep_zone  # FIX: Should sleep to owner's zone
        assert snuggles.zone == Zone.SLEEP
        
    def test_direct_attack_sleeps_to_owner_zone(self):
        """
        Issue #107: Direct attack should sleep cards to owner's zone.
        
        Edge case: If opponent has a stolen card in hand (via some future card effect),
        direct attack should sleep it to the owner's zone.
        """
        # Setup game
        player1 = Player(player_id="player1", name="Player 1")
        player2 = Player(player_id="player2", name="Player 2")
        game_state = GameState(
            game_id="test_game",
            players={player1.player_id: player1, player2.player_id: player2},
            active_player_id=player1.player_id
        )
        
        # Load cards
        csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
        loader = CardLoader(str(csv_path))
        all_cards = loader.load_cards()
        card_data = {card.name: card for card in all_cards}
        
        # Create attacker (Ka for player 1)
        ka = Card(
            name="Ka",
            card_type=CardType.TOY,
            cost=1,
            effect_text=card_data["Ka"].effect_text,
            speed=card_data["Ka"].speed,
            strength=card_data["Ka"].strength,
            stamina=card_data["Ka"].stamina,
            primary_color=card_data["Ka"].primary_color,
            accent_color=card_data["Ka"].accent_color,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Ka"].effect_definitions
        )
        ka.current_stamina = ka.stamina
        
        # Create target card in opponent's hand
        # This card is owned by player1 but somehow in player2's hand (edge case)
        target_card = Card(
            name="Clean",
            card_type=CardType.TOY,
            cost=1,
            effect_text=card_data["Clean"].effect_text,
            speed=card_data["Clean"].speed,
            strength=card_data["Clean"].strength,
            stamina=card_data["Clean"].stamina,
            primary_color=card_data["Clean"].primary_color,
            accent_color=card_data["Clean"].accent_color,
            owner="player1",  # Owner is player1
            controller="player2",  # But controlled by player2 (edge case)
            zone=Zone.HAND,
            effect_definitions=card_data["Clean"].effect_definitions
        )
        
        # Setup game state
        player1.in_play.append(ka)
        player2.hand.append(target_card)
        player2.in_play = []  # No cards in play
        
        # Create engine
        engine = GameEngine(game_state)
        
        # Execute direct attack
        engine._execute_direct_attack(ka, player1, player2)
        
        # Verify card is sleeped to owner's (player1) zone, not controller's (player2)
        assert target_card not in player2.hand
        assert target_card not in player2.sleep_zone  # Should NOT be here
        assert target_card in player1.sleep_zone  # Should be in owner's zone
        assert target_card.zone == Zone.SLEEP


class TestBug123StatBuffsOnlyInPlay:
    """
    Test that stat buffs (Ka, Demideca, etc.) only apply to cards in IN_PLAY zone.
    
    Previously, buffs were showing on cards in hand, which is incorrect.
    """
    
    def test_ka_buffs_only_cards_in_play(self):
        """
        Issue #123: Ka's +2 STR buff should only apply to cards in play,
        not cards in hand.
        """
        # Setup game
        player1 = Player(player_id="player1", name="Player 1")
        player2 = Player(player_id="player2", name="Player 2")
        game_state = GameState(
            game_id="test_game",
            players={player1.player_id: player1, player2.player_id: player2},
            active_player_id=player1.player_id
        )
        
        # Load cards
        csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
        loader = CardLoader(str(csv_path))
        all_cards = loader.load_cards()
        card_data = {card.name: card for card in all_cards}
        
        # Create Ka (in play)
        ka = Card(
            name="Ka",
            card_type=CardType.TOY,
            cost=1,
            effect_text=card_data["Ka"].effect_text,
            speed=card_data["Ka"].speed,
            strength=card_data["Ka"].strength,
            stamina=card_data["Ka"].stamina,
            primary_color=card_data["Ka"].primary_color,
            accent_color=card_data["Ka"].accent_color,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Ka"].effect_definitions
        )
        ka.current_stamina = ka.stamina
        
        # Create Clean in play (should be buffed)
        snuggles_in_play = Card(
            name="Clean",
            card_type=CardType.TOY,
            cost=1,
            effect_text=card_data["Clean"].effect_text,
            speed=card_data["Clean"].speed,
            strength=card_data["Clean"].strength,
            stamina=card_data["Clean"].stamina,
            primary_color=card_data["Clean"].primary_color,
            accent_color=card_data["Clean"].accent_color,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Clean"].effect_definitions
        )
        snuggles_in_play.current_stamina = snuggles_in_play.stamina
        
        # Create Clean in hand (should NOT be buffed)
        snuggles_in_hand = Card(
            name="Clean",
            card_type=CardType.TOY,
            cost=1,
            effect_text=card_data["Clean"].effect_text,
            speed=card_data["Clean"].speed,
            strength=card_data["Clean"].strength,
            stamina=card_data["Clean"].stamina,
            primary_color=card_data["Clean"].primary_color,
            accent_color=card_data["Clean"].accent_color,
            owner="player1",
            controller="player1",
            zone=Zone.HAND,
            effect_definitions=card_data["Clean"].effect_definitions
        )
        
        # Setup game state
        player1.in_play.extend([ka, snuggles_in_play])
        player1.hand.append(snuggles_in_hand)
        
        # Get Ka's effect
        from game_engine.rules.effects.effect_registry import EffectRegistry
        ka_effects = EffectRegistry.get_effects(ka)
        
        # Find the stat boost effect
        stat_boost_effect = None
        for effect in ka_effects:
            if hasattr(effect, 'modify_stat'):
                stat_boost_effect = effect
                break
        
        assert stat_boost_effect is not None, "Ka should have a stat boost effect"
        
        # Test card in play - should be buffed
        base_strength = snuggles_in_play.strength
        modified_strength = stat_boost_effect.modify_stat(
            snuggles_in_play, "strength", base_strength, game_state
        )
        assert modified_strength == base_strength + 2, "Card in play should be buffed"
        
        # Test card in hand - should NOT be buffed
        base_strength_hand = snuggles_in_hand.strength
        modified_strength_hand = stat_boost_effect.modify_stat(
            snuggles_in_hand, "strength", base_strength_hand, game_state
        )
        assert modified_strength_hand == base_strength_hand, "Card in hand should NOT be buffed"
    
    def test_demideca_buffs_only_cards_in_play(self):
        """
        Issue #123: Demideca's +1 to all stats should only apply to cards in play.
        """
        # Setup game
        player1 = Player(player_id="player1", name="Player 1")
        game_state = GameState(
            game_id="test_game",
            players={player1.player_id: player1},
            active_player_id=player1.player_id
        )
        
        # Load cards
        csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
        loader = CardLoader(str(csv_path))
        all_cards = loader.load_cards()
        card_data = {card.name: card for card in all_cards}
        
        # Create Demideca (in play)
        demideca = Card(
            name="Demideca",
            card_type=CardType.TOY,
            cost=2,
            effect_text=card_data["Demideca"].effect_text,
            speed=card_data["Demideca"].speed,
            strength=card_data["Demideca"].strength,
            stamina=card_data["Demideca"].stamina,
            primary_color=card_data["Demideca"].primary_color,
            accent_color=card_data["Demideca"].accent_color,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Demideca"].effect_definitions
        )
        demideca.current_stamina = demideca.stamina
        
        # Create test card in hand
        card_in_hand = Card(
            name="Ka",
            card_type=CardType.TOY,
            cost=1,
            effect_text=card_data["Ka"].effect_text,
            speed=card_data["Ka"].speed,
            strength=card_data["Ka"].strength,
            stamina=card_data["Ka"].stamina,
            primary_color=card_data["Ka"].primary_color,
            accent_color=card_data["Ka"].accent_color,
            owner="player1",
            controller="player1",
            zone=Zone.HAND,
            effect_definitions=card_data["Ka"].effect_definitions
        )
        
        # Setup game state
        player1.in_play.append(demideca)
        player1.hand.append(card_in_hand)
        
        # Get Demideca's effect
        from game_engine.rules.effects.effect_registry import EffectRegistry
        demideca_effects = EffectRegistry.get_effects(demideca)
        
        # Find the stat boost effect
        stat_boost_effect = None
        for effect in demideca_effects:
            if hasattr(effect, 'modify_stat'):
                stat_boost_effect = effect
                break
        
        assert stat_boost_effect is not None, "Demideca should have a stat boost effect"
        
        # Test all stats on card in hand - should NOT be buffed
        for stat_name in ["speed", "strength", "stamina"]:
            base_value = getattr(card_in_hand, stat_name)
            modified_value = stat_boost_effect.modify_stat(
                card_in_hand, stat_name, base_value, game_state
            )
            assert modified_value == base_value, \
                f"Card in hand should NOT have {stat_name} buffed by Demideca"
    
    def test_wizard_tussle_cost_only_when_in_play(self):
        """
        Issue #123: Wizard's tussle cost reduction should only apply when Wizard is in play.
        
        This is more of a consistency check since tussle cost only matters for cards in play,
        but we want to ensure the zone check is in place.
        """
        # Setup game
        player1 = Player(player_id="player1", name="Player 1")
        game_state = GameState(
            game_id="test_game",
            players={player1.player_id: player1},
            active_player_id=player1.player_id
        )
        
        # Load cards
        csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
        loader = CardLoader(str(csv_path))
        all_cards = loader.load_cards()
        card_data = {card.name: card for card in all_cards}
        
        # Create Wizard in play
        wizard_in_play = Card(
            name="Wizard",
            card_type=CardType.TOY,
            cost=2,
            effect_text=card_data["Wizard"].effect_text,
            speed=card_data["Wizard"].speed,
            strength=card_data["Wizard"].strength,
            stamina=card_data["Wizard"].stamina,
            primary_color=card_data["Wizard"].primary_color,
            accent_color=card_data["Wizard"].accent_color,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Wizard"].effect_definitions
        )
        wizard_in_play.current_stamina = wizard_in_play.stamina
        
        # Create Wizard in hand (for comparison)
        wizard_in_hand = Card(
            name="Wizard",
            card_type=CardType.TOY,
            cost=2,
            effect_text=card_data["Wizard"].effect_text,
            speed=card_data["Wizard"].speed,
            strength=card_data["Wizard"].strength,
            stamina=card_data["Wizard"].stamina,
            primary_color=card_data["Wizard"].primary_color,
            accent_color=card_data["Wizard"].accent_color,
            owner="player1",
            controller="player1",
            zone=Zone.HAND,
            effect_definitions=card_data["Wizard"].effect_definitions
        )
        
        player1.in_play.append(wizard_in_play)
        player1.hand.append(wizard_in_hand)
        
        # Get effects
        from game_engine.rules.effects.effect_registry import EffectRegistry
        
        # Wizard in play - should apply cost reduction
        effects_in_play = EffectRegistry.get_effects(wizard_in_play)
        cost_effect_in_play = None
        for effect in effects_in_play:
            if hasattr(effect, 'modify_tussle_cost'):
                cost_effect_in_play = effect
                break
        
        assert cost_effect_in_play is not None
        modified_cost = cost_effect_in_play.modify_tussle_cost(2, game_state, player1)
        assert modified_cost == 1, "Wizard in play should reduce tussle cost to 1"
        
        # Wizard in hand - should NOT apply cost reduction
        effects_in_hand = EffectRegistry.get_effects(wizard_in_hand)
        cost_effect_in_hand = None
        for effect in effects_in_hand:
            if hasattr(effect, 'modify_tussle_cost'):
                cost_effect_in_hand = effect
                break
        
        assert cost_effect_in_hand is not None
        modified_cost_hand = cost_effect_in_hand.modify_tussle_cost(2, game_state, player1)
        assert modified_cost_hand == 2, "Wizard in hand should NOT reduce tussle cost"
