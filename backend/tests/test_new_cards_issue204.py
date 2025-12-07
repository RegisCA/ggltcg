"""
Tests for new cards from Issue #204.

This file tests the new cards added in the Beta release.
Cards are tested in phases based on implementation complexity.

Phase 1: Surge, Dwumm, Twombon (use existing effect patterns)
Phase 2: Drop, Jumpscare (new targeted effects)
Phase 3: Sock Sorcerer (team protection)
Phase 4: VeryVeryAppleJuice (turn-scoped effects)
Phase 5: Belchaletta, Hind Leg Kicker (triggered effects)

IMPORTANT: This test file uses the beta CSV (cards_beta_20251206.csv) which
contains the new cards. The fixture ensures the correct CSV is loaded.
"""

import pytest
import sys
import os
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import clear_card_template_cache
from game_engine.rules.effects.effect_registry import EffectFactory, EffectRegistry
from game_engine.rules.effects.action_effects import GainCCEffect, SleepTargetEffect, ReturnTargetToHandEffect
from game_engine.rules.effects.continuous_effects import StatBoostEffect
from game_engine.models.card import Zone


# Path to the beta CSV with new cards
BETA_CSV_PATH = Path(__file__).parent.parent / "data" / "cards_beta_20251206.csv"


@pytest.fixture(autouse=True)
def use_beta_csv():
    """
    Fixture that sets up the beta CSV for all tests in this module.
    
    This fixture:
    1. Saves the original CARDS_CSV_PATH (if any)
    2. Sets CARDS_CSV_PATH to the beta CSV
    3. Clears the card template cache
    4. Yields to run the test
    5. Restores the original CARDS_CSV_PATH
    6. Clears the cache again for other tests
    """
    # Save original value
    original_path = os.environ.get("CARDS_CSV_PATH")
    
    # Set beta CSV path
    os.environ["CARDS_CSV_PATH"] = str(BETA_CSV_PATH)
    
    # Clear cache to force reload with beta CSV
    clear_card_template_cache()
    
    yield
    
    # Restore original value
    if original_path is not None:
        os.environ["CARDS_CSV_PATH"] = original_path
    else:
        os.environ.pop("CARDS_CSV_PATH", None)
    
    # Clear cache again for other tests
    clear_card_template_cache()


# Import create_game_with_cards and related helpers AFTER setting up the path machinery
# These will use the fixture-controlled CSV path
from conftest import create_game_with_cards, create_card, GameSetup


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
# PHASE 2: DROP AND JUMPSCARE (TARGETED EFFECTS)
# ============================================================================

class TestDrop:
    """
    Drop: Action card - "Sleep an in play card."
    
    Targeted effect that sleeps one card in play.
    Can target any card in play (own or opponent's).
    """
    
    def test_drop_effect_parses_correctly(self):
        """Drop's effect definition should parse to SleepTargetEffect."""
        card = create_card("Drop", owner="p1")
        
        effects = EffectFactory.parse_effects(card.effect_definitions, card)
        
        assert len(effects) == 1
        assert isinstance(effects[0], SleepTargetEffect)
        assert effects[0].count == 1
    
    def test_drop_requires_target(self):
        """Drop should require a target to be played."""
        card = create_card("Drop", owner="p1")
        effects = EffectFactory.parse_effects(card.effect_definitions, card)
        
        assert len(effects) == 1
        assert effects[0].requires_targets() is True
    
    def test_drop_sleeps_opponent_card(self):
        """Drop should sleep an opponent's card when played."""
        setup, cards = create_game_with_cards(
            player1_hand=["Drop"],
            player2_in_play=["Knight"],
            active_player="player1",
            player1_cc=1,  # Drop costs 1
        )
        
        drop = cards["p1_hand_Drop"]
        knight = cards["p2_inplay_Knight"]
        
        # Play Drop targeting opponent's Knight
        setup.engine.play_card(setup.player1, drop, target_ids=[knight.id])
        
        # Knight should be sleeped
        assert knight in setup.player2.sleep_zone, "Knight should be in opponent's sleep zone"
        assert knight not in setup.player2.in_play, "Knight should not be in play"
        
        # Drop should be in player1's sleep zone (action card)
        assert drop in setup.player1.sleep_zone, "Drop should be in player1's sleep zone"
    
    def test_drop_sleeps_own_card(self):
        """Drop can target player's own cards (useful with Wake combo)."""
        setup, cards = create_game_with_cards(
            player1_hand=["Drop"],
            player1_in_play=["Ka"],
            active_player="player1",
            player1_cc=1,
        )
        
        drop = cards["p1_hand_Drop"]
        ka = cards["p1_inplay_Ka"]
        
        # Play Drop targeting own Ka
        setup.engine.play_card(setup.player1, drop, target_ids=[ka.id])
        
        # Ka should be sleeped
        assert ka in setup.player1.sleep_zone, "Ka should be in own sleep zone"
        assert ka not in setup.player1.in_play, "Ka should not be in play"
    
    def test_drop_valid_targets_are_cards_in_play(self):
        """Drop's valid targets should be cards in play (except protected cards)."""
        setup, cards = create_game_with_cards(
            player1_hand=["Drop"],
            player1_in_play=["Ka"],
            player1_sleep=["Demideca"],  # Not a valid target
            player2_in_play=["Knight", "Beary"],
            active_player="player1",
            player1_cc=1,
        )
        
        drop = cards["p1_hand_Drop"]
        ka = cards["p1_inplay_Ka"]
        knight = cards["p2_inplay_Knight"]
        beary = cards["p2_inplay_Beary"]
        
        effects = EffectFactory.parse_effects(drop.effect_definitions, drop)
        valid_targets = effects[0].get_valid_targets(setup.game_state, setup.player1)
        
        # Valid targets are cards in play from either player (except protected)
        valid_ids = [t.id for t in valid_targets]
        assert ka.id in valid_ids, "Own cards in play should be valid targets"
        assert knight.id in valid_ids, "Opponent cards in play should be valid targets"
        
        # Beary has opponent_immunity - should NOT be a valid target when Drop is played by opponent
        assert beary.id not in valid_ids, "Beary should be protected from opponent's Drop"
        
        # Sleep zone cards should NOT be valid targets
        demideca = cards["p1_sleep_Demideca"]
        assert demideca.id not in valid_ids, "Sleep zone cards should not be valid targets"
    
    def test_drop_cannot_target_protected_beary(self):
        """Drop cannot target Beary when played by opponent due to opponent_immunity."""
        setup, cards = create_game_with_cards(
            player1_hand=["Drop"],
            player2_in_play=["Beary"],
            active_player="player1",
            player1_cc=1,
        )
        
        drop = cards["p1_hand_Drop"]
        beary = cards["p2_inplay_Beary"]
        
        effects = EffectFactory.parse_effects(drop.effect_definitions, drop)
        valid_targets = effects[0].get_valid_targets(setup.game_state, setup.player1)
        
        # Beary should not be a valid target
        assert beary not in valid_targets, "Beary should be immune to opponent's Drop"


class TestJumpscare:
    """
    Jumpscare: Action card - "Return an in play card to owner's hand."
    
    Targeted effect that bounces a card back to hand.
    Card returns to OWNER's hand (important for stolen cards).
    """
    
    def test_jumpscare_effect_parses_correctly(self):
        """Jumpscare's effect definition should parse to ReturnTargetToHandEffect."""
        card = create_card("Jumpscare", owner="p1")
        
        effects = EffectFactory.parse_effects(card.effect_definitions, card)
        
        assert len(effects) == 1
        assert isinstance(effects[0], ReturnTargetToHandEffect)
        assert effects[0].count == 1
    
    def test_jumpscare_requires_target(self):
        """Jumpscare should require a target to be played."""
        card = create_card("Jumpscare", owner="p1")
        effects = EffectFactory.parse_effects(card.effect_definitions, card)
        
        assert len(effects) == 1
        assert effects[0].requires_targets() is True
    
    def test_jumpscare_returns_opponent_card_to_hand(self):
        """Jumpscare should return opponent's card to their hand."""
        setup, cards = create_game_with_cards(
            player1_hand=["Jumpscare"],
            player2_in_play=["Knight"],
            active_player="player1",
            player1_cc=1,  # Jumpscare costs 1
        )
        
        jumpscare = cards["p1_hand_Jumpscare"]
        knight = cards["p2_inplay_Knight"]
        
        # Play Jumpscare targeting opponent's Knight
        setup.engine.play_card(setup.player1, jumpscare, target_ids=[knight.id])
        
        # Knight should be in opponent's hand
        assert knight in setup.player2.hand, "Knight should be in opponent's hand"
        assert knight not in setup.player2.in_play, "Knight should not be in play"
        
        # Jumpscare should be in player1's sleep zone (action card)
        assert jumpscare in setup.player1.sleep_zone, "Jumpscare should be in player1's sleep zone"
    
    def test_jumpscare_returns_own_card_to_hand(self):
        """Jumpscare can target player's own cards (to re-play for effects)."""
        setup, cards = create_game_with_cards(
            player1_hand=["Jumpscare"],
            player1_in_play=["Ka"],
            active_player="player1",
            player1_cc=1,
        )
        
        jumpscare = cards["p1_hand_Jumpscare"]
        ka = cards["p1_inplay_Ka"]
        
        # Play Jumpscare targeting own Ka
        setup.engine.play_card(setup.player1, jumpscare, target_ids=[ka.id])
        
        # Ka should be in own hand
        assert ka in setup.player1.hand, "Ka should be in own hand"
        assert ka not in setup.player1.in_play, "Ka should not be in play"
    
    def test_jumpscare_valid_targets_are_cards_in_play(self):
        """Jumpscare's valid targets should be cards in play."""
        setup, cards = create_game_with_cards(
            player1_hand=["Jumpscare"],
            player1_in_play=["Ka"],
            player1_sleep=["Demideca"],  # Not a valid target
            player2_in_play=["Knight"],
            active_player="player1",
            player1_cc=1,
        )
        
        jumpscare = cards["p1_hand_Jumpscare"]
        ka = cards["p1_inplay_Ka"]
        knight = cards["p2_inplay_Knight"]
        
        effects = EffectFactory.parse_effects(jumpscare.effect_definitions, jumpscare)
        valid_targets = effects[0].get_valid_targets(setup.game_state, setup.player1)
        
        # Valid targets are cards in play from either player
        valid_ids = [t.id for t in valid_targets]
        assert ka.id in valid_ids, "Own cards in play should be valid targets"
        assert knight.id in valid_ids, "Opponent cards in play should be valid targets"
        
        # Sleep zone cards should NOT be valid targets
        demideca = cards["p1_sleep_Demideca"]
        assert demideca.id not in valid_ids, "Sleep zone cards should not be valid targets"


# ============================================================================
# PHASE 3: SOCK SORCERER (TEAM PROTECTION)
# ============================================================================


class TestSockSorcerer:
    """
    Sock Sorcerer: "Your opponent's cards' effects don't affect your cards."
    
    Team-wide protection effect. While Sock Sorcerer is in play, all of your
    cards are protected from opponent's card effects.
    """
    
    def test_sock_sorcerer_effect_parses_correctly(self):
        """Sock Sorcerer's effect definition should parse to TeamOpponentImmunityEffect."""
        from game_engine.rules.effects.continuous_effects import TeamOpponentImmunityEffect
        
        card = create_card("Sock Sorcerer", owner="p1")
        
        effects = EffectFactory.parse_effects(card.effect_definitions, card)
        
        assert len(effects) == 1
        assert isinstance(effects[0], TeamOpponentImmunityEffect)
    
    def test_sock_sorcerer_protects_itself_from_drop(self):
        """Sock Sorcerer should be protected from opponent's Drop."""
        setup, cards = create_game_with_cards(
            player1_hand=["Drop"],
            player2_in_play=["Sock Sorcerer"],
            active_player="player1",
            player1_cc=1,
        )
        
        drop = cards["p1_hand_Drop"]
        sock_sorcerer = cards["p2_inplay_Sock Sorcerer"]
        
        effects = EffectFactory.parse_effects(drop.effect_definitions, drop)
        valid_targets = effects[0].get_valid_targets(setup.game_state, setup.player1)
        
        # Sock Sorcerer should NOT be a valid target
        assert sock_sorcerer not in valid_targets, \
            "Sock Sorcerer should be protected from opponent's Drop"
    
    def test_sock_sorcerer_protects_teammates_from_drop(self):
        """Sock Sorcerer should protect all friendly cards from opponent's Drop."""
        setup, cards = create_game_with_cards(
            player1_hand=["Drop"],
            player2_in_play=["Sock Sorcerer", "Knight"],
            active_player="player1",
            player1_cc=1,
        )
        
        drop = cards["p1_hand_Drop"]
        sock_sorcerer = cards["p2_inplay_Sock Sorcerer"]
        knight = cards["p2_inplay_Knight"]
        
        effects = EffectFactory.parse_effects(drop.effect_definitions, drop)
        valid_targets = effects[0].get_valid_targets(setup.game_state, setup.player1)
        
        # Neither Sock Sorcerer nor Knight should be valid targets
        assert sock_sorcerer not in valid_targets, \
            "Sock Sorcerer should be protected from opponent's Drop"
        assert knight not in valid_targets, \
            "Knight should be protected by Sock Sorcerer from opponent's Drop"
    
    def test_sock_sorcerer_protects_from_clean(self):
        """Sock Sorcerer should protect all friendly cards from opponent's Clean."""
        setup, cards = create_game_with_cards(
            player1_hand=["Clean"],
            player1_in_play=["Ka"],
            player2_in_play=["Sock Sorcerer", "Knight", "Demideca"],
            active_player="player1",
            player1_cc=3,  # Clean costs 3
        )
        
        clean = cards["p1_hand_Clean"]
        sock_sorcerer = cards["p2_inplay_Sock Sorcerer"]
        knight = cards["p2_inplay_Knight"]
        demideca = cards["p2_inplay_Demideca"]
        ka = cards["p1_inplay_Ka"]
        
        # Play Clean
        setup.engine.play_card(setup.player1, clean)
        
        # All of player2's cards should still be in play (protected)
        assert sock_sorcerer in setup.player2.in_play, \
            "Sock Sorcerer should be protected from Clean"
        assert knight in setup.player2.in_play, \
            "Knight should be protected by Sock Sorcerer from Clean"
        assert demideca in setup.player2.in_play, \
            "Demideca should be protected by Sock Sorcerer from Clean"
        
        # Player1's Ka should be sleeped (not protected)
        assert ka in setup.player1.sleep_zone, \
            "Ka should be sleeped (not protected by opponent's Sock Sorcerer)"
    
    def test_sock_sorcerer_does_not_protect_opponent(self):
        """Sock Sorcerer should NOT protect opponent's cards."""
        setup, cards = create_game_with_cards(
            player1_hand=["Drop"],
            player1_in_play=["Sock Sorcerer"],  # P1 has Sock Sorcerer
            player2_in_play=["Knight"],  # P2's Knight is NOT protected
            active_player="player1",
            player1_cc=1,
        )
        
        drop = cards["p1_hand_Drop"]
        knight = cards["p2_inplay_Knight"]
        
        effects = EffectFactory.parse_effects(drop.effect_definitions, drop)
        valid_targets = effects[0].get_valid_targets(setup.game_state, setup.player1)
        
        # Knight should BE a valid target (not protected by P1's Sock Sorcerer)
        assert knight in valid_targets, \
            "Opponent's Knight should not be protected by player's Sock Sorcerer"
    
    def test_sock_sorcerer_owner_can_target_own_cards(self):
        """Sock Sorcerer's controller CAN target their own cards."""
        setup, cards = create_game_with_cards(
            player2_hand=["Drop"],
            player2_in_play=["Sock Sorcerer", "Knight"],
            active_player="player2",
            player2_cc=1,
        )
        
        drop = cards["p2_hand_Drop"]
        sock_sorcerer = cards["p2_inplay_Sock Sorcerer"]
        knight = cards["p2_inplay_Knight"]
        
        effects = EffectFactory.parse_effects(drop.effect_definitions, drop)
        valid_targets = effects[0].get_valid_targets(setup.game_state, setup.player2)
        
        # Player2's own cards SHOULD be valid targets for their own Drop
        # (Sock Sorcerer only protects from OPPONENT's effects)
        assert sock_sorcerer in valid_targets, \
            "Own Sock Sorcerer should be targetable by own effects"
        assert knight in valid_targets, \
            "Own Knight should be targetable by own effects (not protected from self)"
    
    def test_sock_sorcerer_not_in_play_does_not_protect(self):
        """Sock Sorcerer in sleep zone does not provide protection."""
        setup, cards = create_game_with_cards(
            player1_hand=["Drop"],
            player2_in_play=["Knight"],
            player2_sleep=["Sock Sorcerer"],  # Asleep, not protecting
            active_player="player1",
            player1_cc=1,
        )
        
        drop = cards["p1_hand_Drop"]
        knight = cards["p2_inplay_Knight"]
        
        effects = EffectFactory.parse_effects(drop.effect_definitions, drop)
        valid_targets = effects[0].get_valid_targets(setup.game_state, setup.player1)
        
        # Knight should be a valid target (Sock Sorcerer is asleep)
        assert knight in valid_targets, \
            "Knight should be targetable when Sock Sorcerer is asleep"


# ============================================================================
# PHASE 4: VERYVERYAPPLEJUICE (TURN-SCOPED STAT BOOST)
# ============================================================================


class TestVeryVeryAppleJuice:
    """
    VeryVeryAppleJuice: "This turn, your cards have 1 more of each stat."
    
    Turn-scoped stat boost effect. Boosts ALL stats (speed, strength, stamina)
    for all of the player's toys currently in play, but only for the current turn.
    """
    
    def test_vvaj_effect_parses_correctly(self):
        """VeryVeryAppleJuice's effect definition should parse to TurnStatBoostEffect."""
        from game_engine.rules.effects.action_effects import TurnStatBoostEffect
        
        card = create_card("VeryVeryAppleJuice", owner="p1")
        
        effects = EffectFactory.parse_effects(card.effect_definitions, card)
        
        assert len(effects) == 1
        assert isinstance(effects[0], TurnStatBoostEffect)
        assert effects[0].stat_name == "all"
        assert effects[0].amount == 1
    
    def test_vvaj_boosts_all_stats(self):
        """VeryVeryAppleJuice should boost speed, strength, and stamina by 1."""
        setup, cards = create_game_with_cards(
            player1_hand=["VeryVeryAppleJuice"],
            player1_in_play=["Knight"],
            active_player="player1",
            player1_cc=0,  # VVAJ costs 0
        )
        
        vvaj = cards["p1_hand_VeryVeryAppleJuice"]
        knight = cards["p1_inplay_Knight"]
        
        # Knight base stats: 4/4/3 (speed/strength/stamina)
        base_speed = setup.engine.get_card_stat(knight, "speed")
        base_strength = setup.engine.get_card_stat(knight, "strength")
        base_stamina = setup.engine.get_effective_stamina(knight)
        
        # Play VeryVeryAppleJuice
        setup.engine.play_card(setup.player1, vvaj)
        
        # All stats should be +1
        assert setup.engine.get_card_stat(knight, "speed") == base_speed + 1, \
            "Speed should be boosted by 1"
        assert setup.engine.get_card_stat(knight, "strength") == base_strength + 1, \
            "Strength should be boosted by 1"
        assert setup.engine.get_effective_stamina(knight) == base_stamina + 1, \
            "Stamina should be boosted by 1"
    
    def test_vvaj_boost_expires_next_turn(self):
        """VeryVeryAppleJuice boost should expire at the start of the next turn."""
        setup, cards = create_game_with_cards(
            player1_hand=["VeryVeryAppleJuice"],
            player1_in_play=["Knight"],
            active_player="player1",
            player1_cc=0,
        )
        
        vvaj = cards["p1_hand_VeryVeryAppleJuice"]
        knight = cards["p1_inplay_Knight"]
        
        # Knight base stats: 4/4/3
        base_strength = 4
        
        # Play VeryVeryAppleJuice
        setup.engine.play_card(setup.player1, vvaj)
        
        # Strength should be boosted this turn
        assert setup.engine.get_card_stat(knight, "strength") == base_strength + 1
        
        # End turn (goes to end phase, then opponent's turn)
        setup.engine.end_turn()  # Goes to player2's turn
        setup.engine.end_turn()  # Back to player1's turn (turn 3)
        
        # Now the boost should be expired
        assert setup.engine.get_card_stat(knight, "strength") == base_strength, \
            "VVAJ boost should expire on next turn"
    
    def test_vvaj_affects_all_friendly_toys(self):
        """VeryVeryAppleJuice should boost ALL friendly toys in play."""
        setup, cards = create_game_with_cards(
            player1_hand=["VeryVeryAppleJuice"],
            player1_in_play=["Knight", "Ka", "Demideca"],
            active_player="player1",
            player1_cc=0,
        )
        
        vvaj = cards["p1_hand_VeryVeryAppleJuice"]
        knight = cards["p1_inplay_Knight"]
        ka = cards["p1_inplay_Ka"]
        demideca = cards["p1_inplay_Demideca"]
        
        # Get base speeds (before VVAJ)
        knight_speed_before = setup.engine.get_card_stat(knight, "speed")
        ka_speed_before = setup.engine.get_card_stat(ka, "speed")
        demideca_speed_before = setup.engine.get_card_stat(demideca, "speed")
        
        # Play VeryVeryAppleJuice
        setup.engine.play_card(setup.player1, vvaj)
        
        # All three should have +1 speed
        assert setup.engine.get_card_stat(knight, "speed") == knight_speed_before + 1
        assert setup.engine.get_card_stat(ka, "speed") == ka_speed_before + 1
        assert setup.engine.get_card_stat(demideca, "speed") == demideca_speed_before + 1
    
    def test_vvaj_does_not_affect_opponent_cards(self):
        """VeryVeryAppleJuice should NOT boost opponent's toys."""
        setup, cards = create_game_with_cards(
            player1_hand=["VeryVeryAppleJuice"],
            player2_in_play=["Knight"],
            active_player="player1",
            player1_cc=0,
        )
        
        vvaj = cards["p1_hand_VeryVeryAppleJuice"]
        opponent_knight = cards["p2_inplay_Knight"]
        
        # Get opponent's knight speed before
        knight_speed_before = setup.engine.get_card_stat(opponent_knight, "speed")
        
        # Play VeryVeryAppleJuice
        setup.engine.play_card(setup.player1, vvaj)
        
        # Opponent's knight should NOT be boosted
        assert setup.engine.get_card_stat(opponent_knight, "speed") == knight_speed_before, \
            "VVAJ should not boost opponent's cards"
    
    def test_vvaj_stacks_with_continuous_effects(self):
        """VeryVeryAppleJuice boost should stack with continuous effects like Ka."""
        setup, cards = create_game_with_cards(
            player1_hand=["VeryVeryAppleJuice"],
            player1_in_play=["Ka", "Knight"],
            active_player="player1",
            player1_cc=0,
        )
        
        vvaj = cards["p1_hand_VeryVeryAppleJuice"]
        knight = cards["p1_inplay_Knight"]
        
        # Knight base strength: 4
        # Ka gives: +2 strength
        # So before VVAJ: 4 + 2 = 6
        strength_with_ka = setup.engine.get_card_stat(knight, "strength")
        assert strength_with_ka == 6, "Ka should provide +2 strength"
        
        # Play VeryVeryAppleJuice (+1 all stats)
        setup.engine.play_card(setup.player1, vvaj)
        
        # Now: 4 (base) + 2 (Ka) + 1 (VVAJ) = 7
        assert setup.engine.get_card_stat(knight, "strength") == 7, \
            "VVAJ should stack with Ka's continuous effect"


# ============================================================================
# PHASE 5: BELCHALETTA & HIND LEG KICKER (Triggered Effects)
# ============================================================================


class TestBelchaletta:
    """Tests for Belchaletta - Toy that grants 2 CC at start of turn."""
    
    def test_effect_parses_correctly(self):
        """Belchaletta should have start_of_turn_gain_cc effect parsed."""
        from game_engine.rules.effects.effect_registry import EffectRegistry
        from game_engine.rules.effects.continuous_effects import StartOfTurnGainCCEffect
        
        # Get Belchaletta from card data
        setup, cards = create_game_with_cards(
            player1_in_play=["Belchaletta"],
            active_player="player1",
        )
        
        belchaletta = cards["p1_inplay_Belchaletta"]
        effects = EffectRegistry.get_effects(belchaletta)
        
        # Should have exactly one StartOfTurnGainCCEffect
        start_turn_effects = [e for e in effects if isinstance(e, StartOfTurnGainCCEffect)]
        assert len(start_turn_effects) == 1, "Belchaletta should have one start_of_turn_gain_cc effect"
        assert start_turn_effects[0].amount == 2, "Should gain 2 CC"
    
    def test_gains_cc_at_start_of_turn(self):
        """Belchaletta should grant 2 CC when its controller's turn starts.
        
        Note: CC is capped at 7. Turn start normally grants +4 CC.
        We start player1 at 1 CC so they have room for both turn gain (+4) and Belchaletta (+2).
        After turn cycle: 1 + 4 (turn) + 2 (Belchaletta) = 7 (capped)
        
        To isolate Belchaletta's contribution, we check CC before and after the effect would trigger.
        """
        setup, cards = create_game_with_cards(
            player1_in_play=["Belchaletta"],
            active_player="player1",
            player1_cc=1,  # Start low to have room for gains
        )
        
        # End turn (goes to player2)
        setup.engine.end_turn()
        cc_after_p1_end = setup.player1.cc
        assert cc_after_p1_end == 1, "P1 CC shouldn't change when ending their turn"
        
        # End player2's turn to come back to player1
        # Player1 will gain: +4 (turn gain) + 2 (Belchaletta) = 7 total (from 1)
        setup.engine.end_turn()
        
        # 1 + 4 + 2 = 7, which is exactly the cap
        assert setup.player1.cc == 7, "Should have 7 CC (1 + 4 turn gain + 2 Belchaletta)"
    
    def test_belchaletta_adds_cc_beyond_turn_gain(self):
        """Verify Belchaletta actually adds CC beyond the normal turn gain.
        
        Compare a game with Belchaletta vs theoretical without.
        Start at 0 CC: turn gain would give 4, Belchaletta adds 2 more = 6.
        """
        setup, cards = create_game_with_cards(
            player1_in_play=["Belchaletta"],
            active_player="player1",
            player1_cc=0,  # Start at 0
        )
        
        # Go through a full turn cycle
        setup.engine.end_turn()  # Player2's turn
        setup.engine.end_turn()  # Back to Player1's turn
        
        # Without Belchaletta: 0 + 4 = 4 CC
        # With Belchaletta: 0 + 4 + 2 = 6 CC
        assert setup.player1.cc == 6, "Belchaletta should add 2 CC beyond turn gain (0+4+2=6)"
    
    def test_does_not_trigger_on_opponent_turn(self):
        """Belchaletta should NOT trigger at start of opponent's turn.
        
        Player2's CC should only increase from turn gain, not from P1's Belchaletta.
        """
        setup, cards = create_game_with_cards(
            player1_in_play=["Belchaletta"],
            active_player="player1",
            player1_cc=3,
            player2_cc=0,  # Start at 0 to clearly see the gain
        )
        
        # End player1's turn, now player2's turn starts
        # Player2 gains turn CC (+4) but NOT Belchaletta bonus
        setup.engine.end_turn()
        
        # Player2 should have exactly 4 CC (turn gain only, no Belchaletta)
        assert setup.player2.cc == 4, "Opponent gains only turn CC, not Belchaletta bonus"
    
    def test_multiple_belchalettas_trigger_separately(self):
        """Multiple Belchalettas should each trigger for 2 CC (up to cap)."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Belchaletta", "Belchaletta"],
            active_player="player1",
            player1_cc=0,  # Start at 0
        )
        
        # End turn twice to come back to player1's turn
        setup.engine.end_turn()  # Player2's turn
        setup.engine.end_turn()  # Player1's turn
        
        # Without Belchalettas: 0 + 4 = 4 CC
        # With 2 Belchalettas: 0 + 4 + 2 + 2 = 8, but capped at 7
        assert setup.player1.cc == 7, "Two Belchalettas should max out CC at 7 cap"


class TestHindLegKicker:
    """Tests for Hind Leg Kicker - Toy that grants 1 CC when another card is played."""
    
    def test_effect_parses_correctly(self):
        """Hind Leg Kicker should have on_card_played_gain_cc effect parsed."""
        from game_engine.rules.effects.effect_registry import EffectRegistry
        from game_engine.rules.effects.continuous_effects import OnCardPlayedGainCCEffect
        
        setup, cards = create_game_with_cards(
            player1_in_play=["Hind Leg Kicker"],
            active_player="player1",
        )
        
        hlk = cards["p1_inplay_Hind Leg Kicker"]
        effects = EffectRegistry.get_effects(hlk)
        
        # Should have exactly one OnCardPlayedGainCCEffect
        on_play_effects = [e for e in effects if isinstance(e, OnCardPlayedGainCCEffect)]
        assert len(on_play_effects) == 1, "Hind Leg Kicker should have one on_card_played_gain_cc effect"
        assert on_play_effects[0].amount == 1, "Should gain 1 CC"
    
    def test_gains_cc_when_controller_plays_another_card(self):
        """Hind Leg Kicker should grant 1 CC when controller plays another card.
        
        Ka costs 2 CC. With HLK in play, playing Ka should cost 2 but gain 1 back.
        Net change: -2 + 1 = -1 CC
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Ka"],
            player1_in_play=["Hind Leg Kicker"],
            active_player="player1",
            player1_cc=5,
        )
        
        ka = cards["p1_hand_Ka"]
        ka_cost = ka.cost  # Should be 2
        initial_cc = setup.player1.cc
        
        setup.engine.play_card(setup.player1, ka)
        
        # Net: -cost + 1 (HLK trigger)
        expected_cc = initial_cc - ka_cost + 1
        assert setup.player1.cc == expected_cc, f"Expected {expected_cc} CC (5 - {ka_cost} + 1), got {setup.player1.cc}"
    
    def test_does_not_trigger_for_itself(self):
        """Hind Leg Kicker should NOT trigger when it is played."""
        setup, cards = create_game_with_cards(
            player1_hand=["Hind Leg Kicker"],
            active_player="player1",
            player1_cc=5,
        )
        
        hlk = cards["p1_hand_Hind Leg Kicker"]
        initial_cc = setup.player1.cc
        hlk_cost = hlk.cost
        
        setup.engine.play_card(setup.player1, hlk)
        
        # Should only subtract the cost, not gain CC from itself
        expected_cc = initial_cc - hlk_cost
        assert setup.player1.cc == expected_cc, "HLK should not trigger for itself"
    
    def test_does_not_trigger_for_opponent_plays(self):
        """Hind Leg Kicker should NOT trigger when opponent plays a card."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Hind Leg Kicker"],
            player2_hand=["Ka"],
            active_player="player2",
            player1_cc=5,
            player2_cc=5,
        )
        
        ka = cards["p2_hand_Ka"]
        initial_p1_cc = setup.player1.cc
        
        setup.engine.play_card(setup.player2, ka)
        
        # Player1 should NOT gain CC from opponent's play
        assert setup.player1.cc == initial_p1_cc, "HLK should not trigger for opponent's plays"
    
    def test_multiple_hind_leg_kickers_trigger_separately(self):
        """Multiple Hind Leg Kickers should each trigger for 1 CC.
        
        Ka costs 2. With 2 HLKs, playing Ka costs 2 but gains 2 back (1 each).
        Net change: -2 + 2 = 0 CC
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Ka"],
            player1_in_play=["Hind Leg Kicker", "Hind Leg Kicker"],
            active_player="player1",
            player1_cc=5,
        )
        
        ka = cards["p1_hand_Ka"]
        ka_cost = ka.cost  # Should be 2
        initial_cc = setup.player1.cc
        
        setup.engine.play_card(setup.player1, ka)
        
        # Net: -cost + 1 (HLK1) + 1 (HLK2) = -2 + 2 = 0
        expected_cc = initial_cc - ka_cost + 2
        assert setup.player1.cc == expected_cc, f"Two HLKs should offset Ka cost (5 - {ka_cost} + 2 = {expected_cc})"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
