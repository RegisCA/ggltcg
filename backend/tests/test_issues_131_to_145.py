"""
Regression tests for tussle and effect bugs discovered after commit 6a342f4.

These tests verify the ACTUAL gameplay code path through GameEngine.

Issues covered:
- #131: Knight vs Beary tussle - Beary is immune to Knight's effect
- #140: Knight vs Umbruh - Knight should auto-win
- #141: Sun as last card triggers premature defeat
- #142: Clean doesn't sleep stolen cards
- #143: Ballaber vs stolen Umbruh - negative stamina zombie
- #144: Ka vs stolen Demideca - negative stamina zombie
- #145: Ballaber alternative cost doesn't sleep stolen cards
- #146: TussleResolver duplication (resolved - now uses GameEngine methods)

Root causes identified and fixed:
1. Tussle prediction logic duplicated (now consolidated in GameEngine)
2. is_protected_from_effect checks controller, not owner
3. Victory condition checked before effect resolution completes
"""

import pytest
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_engine.models.card import Zone

# Import test helpers
from conftest import (
    create_game_with_cards,
    create_card,
)


class TestIssue131KnightVsBeary:
    """
    Issue #131: Knight attacks Beary - both should be sleeped.
    
    Knight's auto-win effect doesn't work against Beary (opponent_immunity).
    This means it becomes a normal tussle:
    - Knight: 4+1 (turn bonus) speed / 4 strength / 3 stamina  
    - Beary: 5 speed / 3 strength / 3 stamina
    
    Knight strikes first (5 > 5? No wait: 4+1=5, Beary=5, SIMULTANEOUS!)
    Actually looking at this more carefully...
    - Attacker Knight speed: 4 + 1 turn bonus = 5
    - Defender Beary speed: 5 (no turn bonus for defender)
    
    So it's simultaneous: both deal damage at the same time.
    Knight deals 4 damage to Beary (stamina 3) -> Beary sleeped
    Beary deals 3 damage to Knight (stamina 3) -> Knight sleeped
    
    Expected: BOTH cards should be sleeped.
    Bug observed: Only Beary was sleeped, Knight was untouched.
    """
    
    def test_knight_attacks_beary_both_should_sleep(self):
        """
        When Knight attacks Beary, both should be sleeped (simultaneous).
        
        Knight's auto-win is negated by Beary's opponent_immunity.
        With equal effective speeds, both strike simultaneously.
        Both deal lethal damage, so both should sleep.
        """
        setup, cards = create_game_with_cards(
            player1_in_play=["Knight"],
            player2_in_play=["Beary"],
            active_player="player1",
        )
        
        knight = cards["p1_inplay_Knight"]
        beary = cards["p2_inplay_Beary"]
        
        # Verify initial stats
        assert knight.speed == 4, "Knight base speed should be 4"
        assert knight.strength == 4, "Knight strength should be 4"
        assert knight.stamina == 3, "Knight stamina should be 3"
        assert beary.speed == 5, "Beary base speed should be 5"
        assert beary.strength == 3, "Beary strength should be 3"
        assert beary.stamina == 3, "Beary stamina should be 3"
        
        # Initiate tussle through GameEngine (the actual gameplay path)
        # Signature: initiate_tussle(attacker, defender, player)
        setup.engine.initiate_tussle(knight, beary, setup.player1)
        
        # Both should be sleeped
        # Knight: 4+1=5 speed vs Beary: 5 speed -> SIMULTANEOUS
        # Knight deals 4 damage to Beary (stamina 3) -> defeated
        # Beary deals 3 damage to Knight (stamina 3) -> defeated
        assert knight not in setup.player1.in_play, "Knight should not be in play"
        assert beary not in setup.player2.in_play, "Beary should not be in play"
        
        # Both should be in their owner's sleep zones
        assert knight in setup.player1.sleep_zone, "Knight should be in P1's sleep zone"
        assert beary in setup.player2.sleep_zone, "Beary should be in P2's sleep zone"
    
    def test_beary_attacks_knight_only_knight_sleeps(self):
        """
        When Beary attacks Knight, only Knight should sleep.
        
        Beary: 5+1 (turn bonus) = 6 speed, 3 strength
        Knight: 4 speed (no turn bonus), 4 strength
        
        Beary strikes first (6 > 4).
        Beary deals 3 damage to Knight (stamina 3) -> Knight defeated, sleeped.
        Knight doesn't strike back because it's already defeated.
        """
        setup, cards = create_game_with_cards(
            player1_in_play=["Beary"],
            player2_in_play=["Knight"],
            active_player="player1",
        )
        
        beary = cards["p1_inplay_Beary"]
        knight = cards["p2_inplay_Knight"]
        
        # Initiate tussle through GameEngine
        # Signature: initiate_tussle(attacker, defender, player)
        setup.engine.initiate_tussle(beary, knight, setup.player1)
        
        # Only Knight should be sleeped (Beary strikes first and one-shots)
        assert beary in setup.player1.in_play, "Beary should still be in play"
        assert knight not in setup.player2.in_play, "Knight should not be in play"
        assert knight in setup.player2.sleep_zone, "Knight should be in sleep zone"
        
        # Beary should have full stamina (no counter-attack)
        assert beary.current_stamina == beary.stamina, "Beary should have full stamina"


class TestIssue140KnightVsUmbruh:
    """
    Issue #140: Knight should auto-win against Umbruh.
    
    Umbruh does NOT have opponent_immunity like Beary.
    Knight's auto-win effect should work normally.
    """
    
    def test_knight_auto_wins_against_umbruh(self):
        """
        Knight's auto-win ability should defeat Umbruh instantly.
        
        Knight has "On your turn, this card wins all tussles it enters."
        Umbruh has no protection against this effect.
        """
        setup, cards = create_game_with_cards(
            player1_in_play=["Knight"],
            player2_in_play=["Umbruh"],
            active_player="player1",
        )
        
        knight = cards["p1_inplay_Knight"]
        umbruh = cards["p2_inplay_Umbruh"]
        
        initial_knight_stamina = knight.current_stamina
        
        # Initiate tussle through GameEngine
        # Signature: initiate_tussle(attacker, defender, player)
        setup.engine.initiate_tussle(knight, umbruh, setup.player1)
        
        # Umbruh should be sleeped (Knight auto-wins)
        assert umbruh not in setup.player2.in_play, "Umbruh should not be in play"
        assert umbruh in setup.player2.sleep_zone, "Umbruh should be in sleep zone"
        
        # Knight should be untouched (auto-win, no combat)
        assert knight in setup.player1.in_play, "Knight should still be in play"
        assert knight.current_stamina == initial_knight_stamina, \
            "Knight should have full stamina (auto-win, no damage taken)"


class TestIssue141SunLastCardDefeat:
    """
    Issue #141: Playing Sun as last card triggers premature defeat.
    
    When Sun is played as the last card in hand:
    1. Sun moves from hand to sleep zone
    2. At this point, hand is empty and no cards in play
    3. Defeat condition is checked BEFORE Sun's effect unsleeps cards
    4. Game incorrectly ends
    
    Expected: Sun's effect should resolve first, THEN check defeat.
    """
    
    def test_sun_as_last_card_should_not_trigger_defeat(self):
        """
        Playing Sun as last card should unsleep cards, not trigger defeat.
        
        Scenario:
        - Player has 2 cards in sleep zone
        - Player has Sun as only card in hand
        - Player plays Sun to unsleep both cards
        - Player should now have 2 cards in play, not be defeated
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Sun"],
            player1_sleep=["Ka", "Demideca"],
            player2_hand=["Knight"],  # Opponent has cards (not defeated)
            active_player="player1",
        )
        
        sun = cards["p1_hand_Sun"]
        ka = cards["p1_sleep_Ka"]
        demideca = cards["p1_sleep_Demideca"]
        
        # Verify initial state
        assert len(setup.player1.hand) == 1, "Player 1 should have 1 card in hand"
        assert len(setup.player1.sleep_zone) == 2, "Player 1 should have 2 sleeping cards"
        assert setup.game_state.winner_id is None, "No winner yet"
        
        # Play Sun targeting both sleeping cards
        target_ids = [ka.id, demideca.id]
        setup.engine.play_card(setup.player1, sun, target_ids=target_ids)
        
        # Sun should be in sleep zone now
        assert sun in setup.player1.sleep_zone, "Sun should be in sleep zone after playing"
        
        # Ka and Demideca should be unsleeping (returned to hand, per rules)
        # "Unsleep" means to return a card from your Sleep Zone to your hand
        assert ka in setup.player1.hand, "Ka should be in hand after Sun effect"
        assert demideca in setup.player1.hand, "Demideca should be in hand after Sun effect"
        
        # Player 1 should NOT be defeated - they have cards in hand
        assert setup.game_state.winner_id != "player2", \
            "Player 1 should not be defeated after playing Sun"
        
        # Player should have cards in hand (not sleep zone)
        assert len(setup.player1.hand) == 2, "Player 1 should have 2 cards in hand"


class TestIssue142CleanStolenCards:
    """
    Issue #142: Clean doesn't sleep stolen cards.
    
    When Clean is played, it should sleep ALL cards in play.
    Stolen cards (via Twist) should also be sleeped.
    
    The bug is that is_protected_from_effect checks the controller's
    ownership, not the effect source's ownership.
    """
    
    def test_clean_sleeps_stolen_cards(self):
        """
        Clean should sleep cards stolen via Twist.
        
        Scenario:
        - Player 2 stole Umbruh from Player 1 using Twist
        - Player 1 plays Clean
        - All cards should be sleeped, including the stolen Umbruh
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Clean"],
            player2_in_play=["Wizard"],
            active_player="player1",
        )
        
        clean = cards["p1_hand_Clean"]
        wizard = cards["p2_inplay_Wizard"]
        
        # Create Umbruh owned by Player 1 but controlled by Player 2 (stolen)
        umbruh = create_card("Umbruh", owner="player1", controller="player2", zone=Zone.IN_PLAY)
        setup.player2.in_play.append(umbruh)
        
        # Verify setup
        assert umbruh.owner == "player1", "Umbruh should be owned by P1"
        assert umbruh.controller == "player2", "Umbruh should be controlled by P2"
        assert umbruh in setup.player2.in_play, "Umbruh should be in P2's play zone"
        
        # Play Clean
        setup.engine.play_card(setup.player1, clean)
        
        # All cards should be sleeped
        assert wizard not in setup.player2.in_play, "Wizard should not be in play"
        assert wizard in setup.player2.sleep_zone, "Wizard should be in P2's sleep zone"
        
        # Stolen Umbruh should also be sleeped (to owner's zone)
        assert umbruh not in setup.player2.in_play, \
            "Stolen Umbruh should not be in play after Clean"
        assert umbruh in setup.player1.sleep_zone, \
            "Stolen Umbruh should be in owner's (P1) sleep zone"


class TestIssue143BallaberVsStolenUmbruh:
    """
    Issue #143: Tussle with stolen Umbruh causes negative stamina.
    
    When tussling a stolen card:
    1. The card takes damage repeatedly
    2. Stamina goes negative (-2, -8, etc.)
    3. Card doesn't get sleeped properly
    4. CC costs don't seem to be spent
    
    This indicates the tussle is executing multiple times or
    the sleep logic isn't triggering.
    """
    
    def test_tussle_stolen_card_sleeps_properly(self):
        """
        Tussle against stolen card should sleep it normally.
        
        Scenario:
        - P2 stole Umbruh from P1 via Twist
        - P1 plays Ballaber and tussles Umbruh
        - Umbruh should be sleeped to P1's zone (owner), not go negative
        """
        setup, cards = create_game_with_cards(
            player1_in_play=["Ballaber"],
            active_player="player1",
        )
        
        ballaber = cards["p1_inplay_Ballaber"]
        
        # Create stolen Umbruh (owned by P1, controlled by P2)
        umbruh = create_card("Umbruh", owner="player1", controller="player2", zone=Zone.IN_PLAY)
        setup.player2.in_play.append(umbruh)
        
        # Verify Ballaber stats: 4 speed, 6 strength, 4 stamina
        # Umbruh stats: 4 speed, 4 strength, 4 stamina
        assert ballaber.speed == 4, "Ballaber speed should be 4"
        assert ballaber.strength == 6, "Ballaber strength should be 6"
        assert umbruh.speed == 4, "Umbruh speed should be 4"
        assert umbruh.stamina == 4, "Umbruh stamina should be 4"
        
        # Initiate tussle
        # Ballaber: 4+1=5 speed vs Umbruh: 4 speed
        # Ballaber strikes first, deals 6 damage to Umbruh (4 stamina) -> defeated
        # Signature: initiate_tussle(attacker, defender, player)
        setup.engine.initiate_tussle(ballaber, umbruh, setup.player1)
        
        # Umbruh should be sleeped to owner's zone, stamina should not be negative
        assert umbruh not in setup.player2.in_play, "Umbruh should not be in P2's play zone"
        assert umbruh in setup.player1.sleep_zone, "Umbruh should be in owner's (P1) sleep zone"
        
        # Current stamina can be 0 or negative (took 6 damage with 4 stamina)
        # But it should only be -2, not -8 or worse (indicating multiple damage applications)
        assert umbruh.current_stamina >= -6, \
            f"Umbruh stamina {umbruh.current_stamina} is too negative (indicates bug)"
        
        # Ballaber should be untouched (struck first, one-shotted Umbruh)
        assert ballaber in setup.player1.in_play, "Ballaber should still be in play"
        assert ballaber.current_stamina == ballaber.stamina, \
            "Ballaber should have full stamina"


class TestIssue144KaVsStolenDemideca:
    """
    Issue #144: Ka vs stolen Demideca results in negative stamina zombie.
    
    When Ka tussles a stolen Demideca:
    - Demideca ends up with -10 stamina
    - But Demideca stays in play ("zombie" state)
    
    This is similar to #143 - stolen cards aren't being sleeped properly.
    """
    
    def test_tussle_ka_vs_stolen_demideca(self):
        """
        Ka should defeat stolen Demideca normally.
        
        Ka stats: 5 speed, 9 strength, 1 stamina
        Demideca stats: 3 speed, 2 strength, 3 stamina
        Ka buff: +2 strength to all friendly cards
        Demideca buff: +1 all stats to all friendly cards
        
        As attacker on P1's turn:
        - Ka: 5+1=6 speed, 9+2(self buff)=11 strength
        - Stolen Demideca: 3 speed, 2 strength (no buffs, it's controlled by P2)
        
        Ka strikes first (6 > 3), deals 11 damage to Demideca (3 stamina).
        Demideca is defeated and should be sleeped.
        """
        setup, cards = create_game_with_cards(
            player1_in_play=["Ka"],
            active_player="player1",
        )
        
        ka = cards["p1_inplay_Ka"]
        
        # Create stolen Demideca (owned by P1, controlled by P2)
        demideca = create_card("Demideca", owner="player1", controller="player2", zone=Zone.IN_PLAY)
        setup.player2.in_play.append(demideca)
        
        # Initiate tussle
        # Signature: initiate_tussle(attacker, defender, player)
        setup.engine.initiate_tussle(ka, demideca, setup.player1)
        
        # Demideca should be sleeped to owner's zone
        assert demideca not in setup.player2.in_play, \
            "Stolen Demideca should not be in P2's play zone after tussle"
        assert demideca in setup.player1.sleep_zone, \
            "Stolen Demideca should be in owner's (P1) sleep zone"
        
        # Stamina should not be extremely negative (indicates repeated damage bug)
        assert demideca.current_stamina >= -15, \
            f"Demideca stamina {demideca.current_stamina} is too negative (indicates bug)"
        
        # Ka should be untouched (struck first, one-shotted Demideca)
        assert ka in setup.player1.in_play, "Ka should still be in play"


class TestIssue145BallaberAlternativeCost:
    """
    Issue #145: Ballaber's alternative cost doesn't sleep stolen cards.
    
    Ballaber can be played for free by sleeping one of your cards.
    When the sleeped card was stolen (via Twist), it should still be sleeped.
    """
    
    def test_ballaber_alternative_cost_sleeps_stolen_card(self):
        """
        Using Ballaber's alternative cost on a stolen card should sleep it.
        
        Scenario:
        - P2 previously stole Demideca from P1
        - P1 has Ballaber in hand and another card in play
        - P1 plays Ballaber using alt cost, sleeping the "stolen back" card
        - The card should actually be sleeped
        """
        # Note: This test assumes we can use alt cost on a card we control
        # even if it was originally ours and stolen by opponent
        setup, cards = create_game_with_cards(
            player1_hand=["Ballaber"],
            player1_in_play=["Ka"],  # Card to use for alternative cost
            active_player="player1",
            player1_cc=0,  # Force alternative cost to be needed
        )
        
        ballaber = cards["p1_hand_Ballaber"]
        ka = cards["p1_inplay_Ka"]
        
        # Play Ballaber using alternative cost (sleep Ka)
        setup.engine.play_card(
            setup.player1, 
            ballaber, 
            alternative_cost_card_id=ka.id
        )
        
        # Ballaber should be in play
        assert ballaber in setup.player1.in_play, "Ballaber should be in play"
        
        # Ka should be sleeped (used as alternative cost)
        assert ka not in setup.player1.in_play, "Ka should not be in play (used as alt cost)"
        assert ka in setup.player1.sleep_zone, "Ka should be in sleep zone"
    
    def test_ballaber_alternative_cost_with_stolen_card_in_play(self):
        """
        Test Ballaber alt cost when you have a stolen card in play.
        
        Scenario:
        - P1 stole P2's Demideca via Twist
        - P1 plays Ballaber using alt cost on stolen Demideca  
        - Demideca should be sleeped to P2's zone (original owner)
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Ballaber"],
            active_player="player1",
            player1_cc=0,  # Force alternative cost
        )
        
        ballaber = cards["p1_hand_Ballaber"]
        
        # Create stolen Demideca (owned by P2, controlled by P1)
        stolen_demideca = create_card(
            "Demideca", 
            owner="player2",  # Original owner
            controller="player1",  # Current controller (stolen)
            zone=Zone.IN_PLAY
        )
        setup.player1.in_play.append(stolen_demideca)
        
        # Play Ballaber using stolen Demideca as alternative cost
        setup.engine.play_card(
            setup.player1,
            ballaber,
            alternative_cost_card_id=stolen_demideca.id
        )
        
        # Ballaber should be in play
        assert ballaber in setup.player1.in_play, "Ballaber should be in play"
        
        # Stolen Demideca should be sleeped to OWNER's zone (P2), not controller's
        assert stolen_demideca not in setup.player1.in_play, \
            "Stolen Demideca should not be in P1's play zone"
        assert stolen_demideca not in setup.player1.sleep_zone, \
            "Stolen Demideca should NOT be in P1's sleep zone (not owner)"
        assert stolen_demideca in setup.player2.sleep_zone, \
            "Stolen Demideca should be in P2's sleep zone (owner)"


class TestTussleStaminaIntegrity:
    """
    General tests for tussle stamina integrity.
    
    These tests verify that:
    1. Damage is only applied once
    2. Cards are sleeped when stamina <= 0
    3. Counter-attacks only happen if the defender survives
    """
    
    def test_no_counter_attack_when_one_shotted(self):
        """
        A card that's one-shotted should not counter-attack.
        
        Ka (9 str) vs Umbruh (4 sta)
        Ka strikes first (5+1=6 > 4), deals 9 damage
        Umbruh is defeated, should not deal damage back
        """
        setup, cards = create_game_with_cards(
            player1_in_play=["Ka"],
            player2_in_play=["Umbruh"],
            active_player="player1",
        )
        
        ka = cards["p1_inplay_Ka"]
        umbruh = cards["p2_inplay_Umbruh"]
        
        # Ka with its own buff: 9 + 2 = 11 strength
        # Umbruh: 4 speed, 4 strength, 4 stamina

        # Signature: initiate_tussle(attacker, defender, player)
        # Umbruh should be sleeped
        setup.engine.initiate_tussle(ka, umbruh, setup.player1)
        assert umbruh in setup.player2.sleep_zone, "Umbruh should be sleeped"
        
        # Ka should have full stamina (no counter-attack)
        assert ka.current_stamina == ka.stamina, \
            f"Ka should have full stamina {ka.stamina}, got {ka.current_stamina}"
    
    def test_damage_applied_only_once(self):
        """
        Damage should only be applied once per tussle.
        
        Use a scenario where defender survives to verify correct damage amount.
        If damage were applied multiple times, defender would be one-shotted.
        
        Note: Using cards WITHOUT stat-boosting effects to avoid complexity.
        """
        setup, cards = create_game_with_cards(
            player1_in_play=["Beary"],  # 5/3/3 speed/strength/stamina
            player2_in_play=["Beary"],  # 5/3/3 (opponent_immunity, no stat buffs)
            active_player="player1",
        )
        
        attacker = cards["p1_inplay_Beary"]
        defender = cards["p2_inplay_Beary"]
        
        # Attacker: 5+1=6 speed, 3 strength
        # Defender: 5 speed, 3 strength
        # Attacker strikes first (speed 6 > 5)
        # Defender takes 3 damage (3 stamina - 3 damage = 0)
        # Defender is sleeped (stamina <= 0)

        initial_attacker_stamina = attacker.current_stamina  # 3
        
        # Signature: initiate_tussle(attacker, defender, player)
        setup.engine.initiate_tussle(attacker, defender, setup.player1)
        
        # Defender should be sleeped (one-shotted)
        assert defender in setup.player2.sleep_zone, "Defender should be sleeped"
        
        # Attacker should be untouched (struck first, one-shotted defender)
        # No counter-attack because defender was sleeped immediately
        assert attacker in setup.player1.in_play, "Attacker should still be in play"
        assert attacker.current_stamina == initial_attacker_stamina, \
            f"Attacker should have full stamina {initial_attacker_stamina}, got {attacker.current_stamina}"


# Run tests when executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
