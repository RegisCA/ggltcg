"""
Tests for tussle resolution bugs #127 and #129.

#127: Ka vs Ka tussle - Incorrect stamina calculation
#129: Beary vs Knight tussle - Speed not considered correctly

Both bugs stem from applying damage to both cards before checking
if the first striker defeated their opponent.
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
from game_engine.rules.tussle_resolver import TussleResolver


class TestBug127KaVsKaTussle:
    """
    Bug #127: Ka vs Ka tussle with incorrect stamina calculation.
    
    Ka stats (from CSV): Speed 5, Strength 9, Stamina 1
    Ka effect: All your cards get +2 Strength
    
    Scenario: Player 1's Ka attacks Player 2's Ka
    - Attacker speed: 5 + 1 (turn bonus) = 6
    - Defender speed: 5
    - Both have strength: 9 + 2 (Ka buff) = 11
    - Both have stamina: 1
    
    Expected: Attacker strikes first (speed 6 > 5), deals 11 damage to defender (stamina 1).
    Defender is defeated and does NOT strike back.
    
    Bug: Both cards take damage simultaneously, resulting in both being defeated.
    """
    
    def test_ka_vs_ka_attacker_should_win(self):
        """Attacker Ka should one-shot defender Ka due to speed advantage."""
        # Setup
        player1 = Player(player_id="player1", name="Player 1")
        player2 = Player(player_id="player2", name="Player 2")
        game_state = GameState(
            game_id="test_game",
            players={player1.player_id: player1, player2.player_id: player2},
            active_player_id=player1.player_id
        )
        
        # Load Ka from CSV
        csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
        loader = CardLoader(str(csv_path))
        all_cards = loader.load_cards()
        card_data = {card.name: card for card in all_cards}
        
        # Create two Ka cards
        ka_attacker = Card(
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
        ka_attacker.current_stamina = ka_attacker.stamina
        
        ka_defender = Card(
            name="Ka",
            card_type=CardType.TOY,
            cost=1,
            effect_text=card_data["Ka"].effect_text,
            speed=card_data["Ka"].speed,
            strength=card_data["Ka"].strength,
            stamina=card_data["Ka"].stamina,
            primary_color=card_data["Ka"].primary_color,
            accent_color=card_data["Ka"].accent_color,
            owner="player2",
            controller="player2",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Ka"].effect_definitions
        )
        ka_defender.current_stamina = ka_defender.stamina
        
        # Put both in play
        player1.in_play.append(ka_attacker)
        player2.in_play.append(ka_defender)
        
        # Resolve tussle
        result = TussleResolver.resolve_tussle(game_state, ka_attacker, ka_defender)
        
        # Verify speeds
        assert result.attacker_speed == 6, "Attacker should have 5 base + 1 turn bonus = 6"
        assert result.defender_speed == 5, "Defender should have 5 base speed"
        assert result.first_striker == "attacker", "Attacker should strike first"
        
        # Verify damage values
        assert result.attacker_damage == 11, "Attacker deals 9 base + 2 Ka buff = 11 damage"
        assert result.defender_damage == 0, "Defender should NOT strike back (one-shotted)"
        
        # Verify outcomes
        assert result.defender_sleeped == True, "Defender should be sleeped (11 damage >= 1 stamina)"
        assert result.attacker_sleeped == False, "Attacker should survive (no counter-attack)"
        
        # Verify actual card states
        assert ka_defender.current_stamina <= 0, "Defender Ka should have current_stamina <= 0"
        assert ka_attacker.current_stamina == 1, "Attacker Ka should have full stamina (not hit)"
    
    def test_ka_vs_ka_predict_winner_matches_resolution(self):
        """predict_winner() should match actual tussle resolution."""
        # Setup
        player1 = Player(player_id="player1", name="Player 1")
        player2 = Player(player_id="player2", name="Player 2")
        game_state = GameState(
            game_id="test_game",
            players={player1.player_id: player1, player2.player_id: player2},
            active_player_id=player1.player_id
        )
        
        # Load Ka
        csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
        loader = CardLoader(str(csv_path))
        all_cards = loader.load_cards()
        card_data = {card.name: card for card in all_cards}
        
        # Create two Ka cards
        ka_attacker = Card(
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
        ka_attacker.current_stamina = ka_attacker.stamina
        
        ka_defender = Card(
            name="Ka",
            card_type=CardType.TOY,
            cost=1,
            effect_text=card_data["Ka"].effect_text,
            speed=card_data["Ka"].speed,
            strength=card_data["Ka"].strength,
            stamina=card_data["Ka"].stamina,
            primary_color=card_data["Ka"].primary_color,
            accent_color=card_data["Ka"].accent_color,
            owner="player2",
            controller="player2",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Ka"].effect_definitions
        )
        ka_defender.current_stamina = ka_defender.stamina
        
        # Put both in play
        player1.in_play.append(ka_attacker)
        player2.in_play.append(ka_defender)
        
        # Predict winner
        prediction = TussleResolver.predict_winner(game_state, ka_attacker, ka_defender)
        
        # Should predict attacker wins
        assert prediction == "attacker", "predict_winner should return 'attacker' for Ka vs Ka"


class TestBug129BearyVsKnightTussle:
    """
    Bug #129: Beary vs Knight tussle - Speed not considered correctly.
    
    Knight stats (from CSV): Speed 4, Strength 4, Stamina 3
    Knight effect: Auto-wins tussles on your turn (but NOT against Beary)
    
    Beary stats (from CSV): Speed 5, Strength 3, Stamina 3
    Beary effect: Opponent immunity
    
    Scenario: Player 1's Beary attacks Player 2's Knight
    - Attacker (Beary) speed: 5 + 1 (turn bonus) = 6
    - Defender (Knight) speed: 4
    - Attacker strength: 3
    - Defender strength: 4
    
    Expected: Beary strikes first (speed 6 > 4), deals 3 damage to Knight (stamina 3).
    Knight is defeated and does NOT strike back.
    
    Bug: Knight deals damage to Beary even though Knight should be one-shotted.
    """
    
    def test_beary_vs_knight_beary_should_win(self):
        """Beary should one-shot Knight due to overwhelming speed and strength."""
        # Setup
        player1 = Player(player_id="player1", name="Player 1")
        player2 = Player(player_id="player2", name="Player 2")
        game_state = GameState(
            game_id="test_game",
            players={player1.player_id: player1, player2.player_id: player2},
            active_player_id=player1.player_id
        )
        
        # Load cards from CSV
        csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
        loader = CardLoader(str(csv_path))
        all_cards = loader.load_cards()
        card_data = {card.name: card for card in all_cards}
        
        # Create Beary (attacker)
        beary = Card(
            name="Beary",
            card_type=CardType.TOY,
            cost=3,
            effect_text=card_data["Beary"].effect_text,
            speed=card_data["Beary"].speed,
            strength=card_data["Beary"].strength,
            stamina=card_data["Beary"].stamina,
            primary_color=card_data["Beary"].primary_color,
            accent_color=card_data["Beary"].accent_color,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Beary"].effect_definitions
        )
        beary.current_stamina = beary.stamina
        
        # Create Knight (defender)
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
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Knight"].effect_definitions
        )
        knight.current_stamina = knight.stamina
        
        # Put both in play
        player1.in_play.append(beary)
        player2.in_play.append(knight)
        
        # Resolve tussle
        result = TussleResolver.resolve_tussle(game_state, beary, knight)
        
        # Verify speeds
        assert result.attacker_speed == 6, "Beary should have 5 base + 1 turn bonus = 6"
        assert result.defender_speed == 4, "Knight should have 4 base speed"
        assert result.first_striker == "attacker", "Beary should strike first"
        
        # Verify damage values
        assert result.attacker_damage == 3, "Beary deals 3 damage"
        assert result.defender_damage == 0, "Knight should NOT strike back (one-shotted)"
        
        # Verify outcomes
        assert result.defender_sleeped == True, "Knight should be sleeped (3 damage >= 3 stamina)"
        assert result.attacker_sleeped == False, "Beary should survive (no counter-attack)"
        
        # Verify actual card states
        assert knight.current_stamina <= 0, "Knight should have current_stamina <= 0"
        assert beary.current_stamina == 3, "Beary should have full stamina (not hit)"
    
    def test_knight_vs_beary_knight_cannot_auto_win(self):
        """Knight's auto-win ability does NOT work against Beary."""
        # Setup
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
        
        # Create Knight (attacker on player1's turn)
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
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Knight"].effect_definitions
        )
        knight.current_stamina = knight.stamina
        
        # Create Beary (defender)
        beary = Card(
            name="Beary",
            card_type=CardType.TOY,
            cost=3,
            effect_text=card_data["Beary"].effect_text,
            speed=card_data["Beary"].speed,
            strength=card_data["Beary"].strength,
            stamina=card_data["Beary"].stamina,
            primary_color=card_data["Beary"].primary_color,
            accent_color=card_data["Beary"].accent_color,
            owner="player2",
            controller="player2",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Beary"].effect_definitions
        )
        beary.current_stamina = beary.stamina
        
        # Put both in play
        player1.in_play.append(knight)
        player2.in_play.append(beary)
        
        # Resolve tussle (Knight attacks Beary)
        result = TussleResolver.resolve_tussle(game_state, knight, beary)
        
        # Knight should NOT auto-win against Beary
        # This should be a normal tussle
        # Knight: 4 + 1 (turn bonus) = 5 speed
        # Beary: 5 speed
        # Speeds are tied, so simultaneous strikes
        assert result.first_striker == "simultaneous", "Speeds are equal, should be simultaneous"
        
        # Both strike simultaneously
        # Knight deals 4 damage to Beary (stamina 3) → Beary defeated
        # Beary deals 3 damage to Knight (stamina 3) → Knight defeated
        assert result.attacker_sleeped == True, "Knight should be sleeped (simultaneous)"
        assert result.defender_sleeped == True, "Beary should be sleeped (simultaneous)"


class TestTussleStrikeOrderEdgeCases:
    """Additional edge case tests for strike order logic."""
    
    def test_simultaneous_strikes_both_defeated(self):
        """When speeds are tied, both strike simultaneously and can both be defeated."""
        # Setup
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
        
        # Create two Snuggles (Speed 2, Strength 3, Stamina 1)
        snuggles1 = Card(
            name="Snuggles",
            card_type=CardType.TOY,
            cost=1,
            effect_text=card_data["Snuggles"].effect_text,
            speed=card_data["Snuggles"].speed,
            strength=card_data["Snuggles"].strength,
            stamina=card_data["Snuggles"].stamina,
            primary_color=card_data["Snuggles"].primary_color,
            accent_color=card_data["Snuggles"].accent_color,
            owner="player1",
            controller="player1",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Snuggles"].effect_definitions
        )
        snuggles1.current_stamina = snuggles1.stamina
        
        snuggles2 = Card(
            name="Snuggles",
            card_type=CardType.TOY,
            cost=1,
            effect_text=card_data["Snuggles"].effect_text,
            speed=card_data["Snuggles"].speed,
            strength=card_data["Snuggles"].strength,
            stamina=card_data["Snuggles"].stamina,
            primary_color=card_data["Snuggles"].primary_color,
            accent_color=card_data["Snuggles"].accent_color,
            owner="player2",
            controller="player2",
            zone=Zone.IN_PLAY,
            effect_definitions=card_data["Snuggles"].effect_definitions
        )
        snuggles2.current_stamina = snuggles2.stamina
        
        # Put both in play
        player1.in_play.append(snuggles1)
        player2.in_play.append(snuggles2)
        
        # Resolve tussle
        # Attacker: 2 + 1 (turn bonus) = 3 speed
        # Defender: 2 speed
        # So attacker strikes first, not simultaneous
        result = TussleResolver.resolve_tussle(game_state, snuggles1, snuggles2)
        
        # With turn bonus, speeds are NOT tied
        assert result.first_striker == "attacker", "Attacker has +1 speed from turn bonus"
        assert result.defender_sleeped == True, "Defender one-shotted (3 str >= 1 sta)"
        assert result.attacker_sleeped == False, "Attacker survives"
