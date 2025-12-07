"""
Tests for new cards from Issue #204.

This file tests the new cards added in the Beta release.
Cards are tested in phases based on implementation complexity.

Phase 1: Surge, Dwumm, Twombon (use existing effect patterns)
Phase 2: Drop, Jumpscare (new targeted effects)
Phase 3: Sock Sorcerer (team protection)
Phase 4: VeryVeryAppleJuice (turn-scoped effects)
Phase 5: Belchaletta, Hind Leg Kicker (triggered effects)
"""

import pytest
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards, create_card, GameSetup
from game_engine.rules.effects.effect_registry import EffectFactory, EffectRegistry
from game_engine.rules.effects.action_effects import GainCCEffect
from game_engine.rules.effects.continuous_effects import StatBoostEffect
from game_engine.models.card import Zone


# ============================================================================
# PHASE 1: SURGE, DWUMM, TWOMBON
# These cards use existing effect patterns and should work immediately.
# ============================================================================

class TestSurge:
    """
    Surge: "Gain 1 CC."
    
    Simple CC gain effect, similar to Rush but without turn restriction.
    Uses existing GainCCEffect class.
    """
    
    def test_surge_effect_parses_correctly(self):
        """Surge's effect definition should parse to GainCCEffect."""
        card = create_card("Surge", owner="p1")
        
        effects = EffectFactory.parse_effects(card.effect_definitions, card)
        
        assert len(effects) == 1
        assert isinstance(effects[0], GainCCEffect)
        assert effects[0].amount == 1
        assert effects[0].not_first_turn is False  # Can be played turn 1
    
    def test_surge_grants_1_cc(self):
        """Playing Surge should grant 1 CC to the player."""
        setup, cards = create_game_with_cards(
            player1_hand=["Surge"],
            active_player="player1",
            player1_cc=3,
        )
        
        surge = cards["p1_hand_Surge"]
        initial_cc = setup.player1.cc
        
        # Play Surge (costs 0 CC)
        setup.engine.play_card(setup.player1, surge)
        
        # Should have gained 1 CC (0 cost + 1 gain = net +1)
        assert setup.player1.cc == initial_cc + 1, \
            f"Expected {initial_cc + 1} CC, got {setup.player1.cc}"
    
    def test_surge_can_be_played_on_turn_1(self):
        """Unlike Rush, Surge can be played on turn 1."""
        setup, cards = create_game_with_cards(
            player1_hand=["Surge"],
            active_player="player1",
            player1_cc=2,  # Turn 1 starting CC
        )
        
        # Ensure it's turn 1
        setup.game_state.turn_number = 1
        
        surge = cards["p1_hand_Surge"]
        
        can_play, reason = setup.engine.can_play_card(surge, setup.player1)
        assert can_play, f"Surge should be playable on turn 1, but: {reason}"
    
    def test_surge_goes_to_sleep_zone_after_play(self):
        """Action cards go to sleep zone after being played."""
        setup, cards = create_game_with_cards(
            player1_hand=["Surge"],
            active_player="player1",
            player1_cc=3,
        )
        
        surge = cards["p1_hand_Surge"]
        
        setup.engine.play_card(setup.player1, surge)
        
        assert surge in setup.player1.sleep_zone
        assert surge not in setup.player1.hand
        assert surge.zone == Zone.SLEEP


class TestDwumm:
    """
    Dwumm: "Your cards have 2 more speed."
    
    Continuous stat boost effect, similar to Ka but for speed.
    Uses existing StatBoostEffect class.
    """
    
    def test_dwumm_effect_parses_correctly(self):
        """Dwumm's effect definition should parse to StatBoostEffect for speed."""
        card = create_card("Dwumm", owner="p1")
        
        effects = EffectFactory.parse_effects(card.effect_definitions, card)
        
        assert len(effects) == 1
        assert isinstance(effects[0], StatBoostEffect)
        assert effects[0].stat_name == "speed"
        assert effects[0].amount == 2
    
    def test_dwumm_boosts_own_speed(self):
        """Dwumm should boost its own speed by 2."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Dwumm"],
            active_player="player1",
        )
        
        dwumm = cards["p1_inplay_Dwumm"]
        
        # Base speed is 2, with effect should be 4
        base_speed = 2
        effective_speed = setup.engine.get_card_stat(dwumm, "speed")
        
        assert effective_speed == base_speed + 2, \
            f"Dwumm should have {base_speed + 2} speed, got {effective_speed}"
    
    def test_dwumm_boosts_other_toys_speed(self):
        """Dwumm should boost other friendly toys' speed by 2."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Dwumm", "Knight"],
            active_player="player1",
        )
        
        knight = cards["p1_inplay_Knight"]
        
        # Knight base speed is 4, with Dwumm should be 6
        knight_base_speed = 4
        effective_speed = setup.engine.get_card_stat(knight, "speed")
        
        assert effective_speed == knight_base_speed + 2, \
            f"Knight should have {knight_base_speed + 2} speed with Dwumm, got {effective_speed}"
    
    def test_dwumm_does_not_affect_opponent(self):
        """Dwumm should not boost opponent's cards."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Dwumm"],
            player2_in_play=["Knight"],
            active_player="player1",
        )
        
        opponent_knight = cards["p2_inplay_Knight"]
        
        # Opponent's Knight should have base speed (4)
        effective_speed = setup.engine.get_card_stat(opponent_knight, "speed")
        
        assert effective_speed == 4, \
            f"Opponent's Knight should have base speed 4, got {effective_speed}"
    
    def test_dwumm_does_not_affect_strength_or_stamina(self):
        """Dwumm only boosts speed, not other stats."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Dwumm", "Knight"],
            active_player="player1",
        )
        
        knight = cards["p1_inplay_Knight"]
        
        # Knight's strength and stamina should be unaffected
        assert setup.engine.get_card_stat(knight, "strength") == 4  # Base strength
        assert setup.engine.get_effective_stamina(knight) == 3  # Base stamina


class TestTwombon:
    """
    Twombon: "Your cards have 2 more strength."
    
    Continuous stat boost effect, identical to Ka.
    Uses existing StatBoostEffect class.
    """
    
    def test_twombon_effect_parses_correctly(self):
        """Twombon's effect definition should parse to StatBoostEffect for strength."""
        card = create_card("Twombon", owner="p1")
        
        effects = EffectFactory.parse_effects(card.effect_definitions, card)
        
        assert len(effects) == 1
        assert isinstance(effects[0], StatBoostEffect)
        assert effects[0].stat_name == "strength"
        assert effects[0].amount == 2
    
    def test_twombon_boosts_own_strength(self):
        """Twombon should boost its own strength by 2."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Twombon"],
            active_player="player1",
        )
        
        twombon = cards["p1_inplay_Twombon"]
        
        # Base strength is 2, with effect should be 4
        base_strength = 2
        effective_strength = setup.engine.get_card_stat(twombon, "strength")
        
        assert effective_strength == base_strength + 2, \
            f"Twombon should have {base_strength + 2} strength, got {effective_strength}"
    
    def test_twombon_boosts_other_toys_strength(self):
        """Twombon should boost other friendly toys' strength by 2."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Twombon", "Knight"],
            active_player="player1",
        )
        
        knight = cards["p1_inplay_Knight"]
        
        # Knight base strength is 4, with Twombon should be 6
        knight_base_strength = 4
        effective_strength = setup.engine.get_card_stat(knight, "strength")
        
        assert effective_strength == knight_base_strength + 2, \
            f"Knight should have {knight_base_strength + 2} strength with Twombon, got {effective_strength}"
    
    def test_twombon_stacks_with_ka(self):
        """Twombon and Ka both boost strength, they should stack."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Twombon", "Ka", "Knight"],
            active_player="player1",
        )
        
        knight = cards["p1_inplay_Knight"]
        
        # Knight base strength is 4, with Twombon (+2) and Ka (+2) should be 8
        knight_base_strength = 4
        effective_strength = setup.engine.get_card_stat(knight, "strength")
        
        assert effective_strength == knight_base_strength + 4, \
            f"Knight should have {knight_base_strength + 4} strength with Twombon + Ka, got {effective_strength}"


class TestDwummAndTwombonCombined:
    """Test Dwumm and Twombon working together."""
    
    def test_dwumm_and_twombon_both_apply(self):
        """Both Dwumm (+2 speed) and Twombon (+2 strength) should apply."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Dwumm", "Twombon", "Knight"],
            active_player="player1",
        )
        
        knight = cards["p1_inplay_Knight"]
        
        # Knight should have +2 speed from Dwumm and +2 strength from Twombon
        assert setup.engine.get_card_stat(knight, "speed") == 4 + 2  # 6
        assert setup.engine.get_card_stat(knight, "strength") == 4 + 2  # 6
        assert setup.engine.get_effective_stamina(knight) == 3  # Unchanged
    
    def test_multiple_dwumm_stack(self):
        """Multiple Dwumm cards should stack their speed bonus."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Dwumm", "Knight"],
            active_player="player1",
        )
        
        # Create second Dwumm in play
        dwumm2 = create_card("Dwumm", owner="player1", controller="player1", zone=Zone.IN_PLAY)
        setup.player1.in_play.append(dwumm2)
        
        knight = cards["p1_inplay_Knight"]
        
        # Knight should have +4 speed from two Dwumms
        assert setup.engine.get_card_stat(knight, "speed") == 4 + 4  # 8


# ============================================================================
# PHASE 2-5 TESTS WILL BE ADDED AS EFFECTS ARE IMPLEMENTED
# ============================================================================

class TestPhase2Placeholder:
    """Placeholder for Drop and Jumpscare tests."""
    
    @pytest.mark.skip(reason="Drop effect not yet implemented")
    def test_drop_effect_parses(self):
        """Drop should parse to SleepTargetEffect."""
        pass
    
    @pytest.mark.skip(reason="Jumpscare effect not yet implemented")
    def test_jumpscare_effect_parses(self):
        """Jumpscare should parse to ReturnTargetToHandEffect."""
        pass


class TestPhase3Placeholder:
    """Placeholder for Sock Sorcerer tests."""
    
    @pytest.mark.skip(reason="Sock Sorcerer effect not yet implemented")
    def test_sock_sorcerer_protects_team(self):
        """Sock Sorcerer should protect all friendly cards from opponent effects."""
        pass


class TestPhase4Placeholder:
    """Placeholder for VeryVeryAppleJuice tests."""
    
    @pytest.mark.skip(reason="VeryVeryAppleJuice effect not yet implemented")
    def test_vvaj_boosts_stats_this_turn(self):
        """VeryVeryAppleJuice should boost all stats but only for the current turn."""
        pass


class TestPhase5Placeholder:
    """Placeholder for Belchaletta and Hind Leg Kicker tests."""
    
    @pytest.mark.skip(reason="Belchaletta effect not yet implemented")
    def test_belchaletta_gains_cc_at_turn_start(self):
        """Belchaletta should gain 2 CC at the start of its controller's turn."""
        pass
    
    @pytest.mark.skip(reason="Hind Leg Kicker effect not yet implemented")
    def test_hind_leg_kicker_gains_cc_on_play(self):
        """Hind Leg Kicker should gain 1 CC when another card is played."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
