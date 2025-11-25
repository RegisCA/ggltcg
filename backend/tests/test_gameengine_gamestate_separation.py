"""
Tests for GameEngine/GameState separation - Issue #85

Tests that game logic (like sleeping cards) properly triggers effects when
called through GameEngine methods, ensuring architectural boundaries are maintained.
"""

import sys
from pathlib import Path

# Add backend/src to path for imports
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))

from game_engine.models.card import Card, CardType, Zone
from game_engine.models.player import Player
from game_engine.models.game_state import GameState, Phase
from game_engine.game_engine import GameEngine
from game_engine.data.card_loader import CardLoader


# Path to cards.csv
CARDS_CSV_PATH = Path(__file__).parent.parent / "data" / "cards.csv"


def test_ballaber_sleeps_umbruh_from_play_triggers_cc_gain():
    """
    Test that when Ballaber sleeps Umbruh from play as alternative cost,
    Umbruh's when-sleeped effect triggers and grants 1 CC to owner.
    
    This tests the fix in action_executor.py:256
    """
    print("\n=== Test: Ballaber sleeps Umbruh from play ===")
    
    # Load cards from CSV
    loader = CardLoader(CARDS_CSV_PATH)
    all_cards = loader.load_cards()
    
    # Find Ballaber and Umbruh
    ballaber = next(c for c in all_cards if c.name == "Ballaber")
    umbruh = next(c for c in all_cards if c.name == "Umbruh")
    
    # Create players
    p1 = Player(player_id="p1", name="Player 1")
    p2 = Player(player_id="p2", name="Player 2")
    
    # Give P1: Ballaber in hand, Umbruh in play
    ballaber.zone = Zone.HAND
    ballaber.owner = "p1"
    ballaber.controller = "p1"
    p1.hand = [ballaber]
    
    umbruh.zone = Zone.IN_PLAY
    umbruh.owner = "p1"
    umbruh.controller = "p1"
    p1.in_play = [umbruh]
    
    # Give P1 enough CC for Ballaber (cost 3) and then some
    p1.cc = 5
    p1.max_cc = 7
    
    # Create game
    game_state = GameState(
        game_id="test",
        players={"p1": p1, "p2": p2},
        active_player_id="p1",
        first_player_id="p1",
        turn_number=2,  # Not turn 1
    )
    engine = GameEngine(game_state)
    
    print(f"Before: P1 CC = {p1.cc}, Umbruh in play: {umbruh in p1.in_play}")
    
    # Sleep Umbruh from play via GameEngine (simulating Ballaber alternative cost)
    # This should trigger Umbruh's when-sleeped effect
    engine._sleep_card(umbruh, p1, was_in_play=True)
    
    print(f"After: P1 CC = {p1.cc}, Umbruh in sleep zone: {umbruh in p1.sleep_zone}")
    
    # Assertions
    assert umbruh in p1.sleep_zone, "Umbruh should be in sleep zone"
    assert p1.cc == 6, f"P1 should have gained 1 CC from Umbruh trigger (expected 6, got {p1.cc})"
    # 5 initial CC + 1 from Umbruh when sleeped = 6
    
    print("✓ Umbruh from play triggers CC gain correctly")


def test_ballaber_sleeps_umbruh_from_hand_no_trigger():
    """
    Test that when Ballaber sleeps Umbruh from hand as alternative cost,
    Umbruh's when-sleeped effect does NOT trigger (wasn't in play).
    
    Verifies that was_in_play parameter works correctly.
    """
    print("\n=== Test: Ballaber sleeps Umbruh from hand (no trigger) ===")
    
    # Load cards from CSV
    loader = CardLoader(CARDS_CSV_PATH)
    all_cards = loader.load_cards()
    
    # Find Ballaber and Umbruh
    ballaber = next(c for c in all_cards if c.name == "Ballaber")
    umbruh = next(c for c in all_cards if c.name == "Umbruh")
    
    # Create players
    p1 = Player(player_id="p1", name="Player 1")
    p2 = Player(player_id="p2", name="Player 2")
    
    # Give P1: Ballaber in hand, Umbruh in hand (not in play)
    ballaber.zone = Zone.HAND
    ballaber.owner = "p1"
    ballaber.controller = "p1"
    
    umbruh.zone = Zone.HAND
    umbruh.owner = "p1"
    umbruh.controller = "p1"
    
    p1.hand = [ballaber, umbruh]
    p1.in_play = []
    
    # Give P1 enough CC
    p1.cc = 5
    p1.max_cc = 7
    
    # Create game
    game_state = GameState(
        game_id="test",
        players={"p1": p1, "p2": p2},
        active_player_id="p1",
        first_player_id="p1",
        turn_number=2,
    )
    engine = GameEngine(game_state)
    
    print(f"Before: P1 CC = {p1.cc}, Umbruh in hand")
    
    # Sleep Umbruh from hand via GameEngine (simulating Ballaber alternative cost from hand)
    # This should NOT trigger Umbruh's when-sleeped effect (wasn't in play)
    engine._sleep_card(umbruh, p1, was_in_play=False)
    
    print(f"After: P1 CC = {p1.cc}, Umbruh in sleep zone: {umbruh in p1.sleep_zone}")
    
    # Assertions
    assert umbruh in p1.sleep_zone, "Umbruh should be in sleep zone"
    assert p1.cc == 5, f"P1 should NOT have gained CC (Umbruh wasn't in play). Expected 5, got {p1.cc}"
    # 5 initial CC + 0 from Umbruh (not in play) = 5
    
    print("✓ Umbruh from hand correctly does not trigger effect")


def test_snuggles_sleeps_umbruh_triggers_cc_gain():
    """
    Test that when Snuggles is sleeped and sleeps Umbruh (cascading effect),
    Umbruh's when-sleeped effect triggers and grants 1 CC.
    
    This tests the fix in triggered_effects.py:109
    """
    print("\n=== Test: Snuggles sleeps Umbruh (cascading effects) ===")
    
    # Load cards from CSV
    loader = CardLoader(CARDS_CSV_PATH)
    all_cards = loader.load_cards()
    
    # Find Snuggles and Umbruh
    snuggles = next(c for c in all_cards if c.name == "Snuggles")
    umbruh = next(c for c in all_cards if c.name == "Umbruh")
    
    # Create players
    p1 = Player(player_id="p1", name="Player 1")
    p2 = Player(player_id="p2", name="Player 2")
    
    # Give P1: Snuggles and Umbruh both in play
    snuggles.zone = Zone.IN_PLAY
    snuggles.owner = "p1"
    snuggles.controller = "p1"
    
    umbruh.zone = Zone.IN_PLAY
    umbruh.owner = "p1"
    umbruh.controller = "p1"
    
    p1.in_play = [snuggles, umbruh]
    p1.cc = 3
    p1.max_cc = 7
    
    # Create game
    game_state = GameState(
        game_id="test",
        players={"p1": p1, "p2": p2},
        active_player_id="p1",
        first_player_id="p1",
        turn_number=2,
    )
    engine = GameEngine(game_state)
    
    print(f"Before: P1 CC = {p1.cc}, Snuggles and Umbruh in play")
    
    # Sleep Snuggles from play (this should trigger Snuggles' effect)
    # Snuggles' effect should sleep Umbruh
    # Umbruh's effect should grant 1 CC
    engine._sleep_card(snuggles, p1, was_in_play=True)
    
    # Snuggles effect is optional and requires a target
    # The effect should fire but we need to provide target via kwargs
    # Let's manually trigger it with the target
    from game_engine.rules.effects import EffectRegistry
    effects = EffectRegistry.get_effects(snuggles)
    for effect in effects:
        from game_engine.rules.effects.base_effect import TriggeredEffect, TriggerTiming
        if isinstance(effect, TriggeredEffect) and effect.trigger == TriggerTiming.WHEN_SLEEPED:
            if effect.should_trigger(game_state, sleeped_card=snuggles, was_in_play=True):
                # Snuggles' effect requires a target - provide Umbruh
                effect.apply(game_state, sleeped_card=snuggles, target=umbruh, game_engine=engine)
    
    print(f"After: P1 CC = {p1.cc}")
    print(f"Snuggles in sleep zone: {snuggles in p1.sleep_zone}")
    print(f"Umbruh in sleep zone: {umbruh in p1.sleep_zone}")
    
    # Assertions
    assert snuggles in p1.sleep_zone, "Snuggles should be in sleep zone"
    assert umbruh in p1.sleep_zone, "Umbruh should be sleeped by Snuggles effect"
    assert p1.cc == 4, f"P1 should have gained 1 CC from Umbruh trigger (expected 4, got {p1.cc})"
    # 3 initial CC + 1 from Umbruh when sleeped = 4
    
    print("✓ Snuggles + Umbruh cascading effects work correctly")


def test_clean_sleeps_umbruh_triggers_cc_gain():
    """
    Test that when Clean sleeps all cards including Umbruh,
    Umbruh's when-sleeped effect triggers.
    
    This was already fixed in Phase 3 but validates it still works.
    """
    print("\n=== Test: Clean sleeps Umbruh (existing Phase 3 fix) ===")
    
    # Load cards from CSV
    loader = CardLoader(CARDS_CSV_PATH)
    all_cards = loader.load_cards()
    
    # Find Clean and Umbruh
    clean = next(c for c in all_cards if c.name == "Clean")
    umbruh = next(c for c in all_cards if c.name == "Umbruh")
    
    # Create players
    p1 = Player(player_id="p1", name="Player 1")
    p2 = Player(player_id="p2", name="Player 2")
    
    # Give P1: Clean in hand
    clean.zone = Zone.HAND
    clean.owner = "p1"
    clean.controller = "p1"
    p1.hand = [clean]
    
    # Give P2: Umbruh in play
    umbruh.zone = Zone.IN_PLAY
    umbruh.owner = "p2"
    umbruh.controller = "p2"
    p2.in_play = [umbruh]
    
    # Give P1 CC to play Clean
    p1.cc = 5
    p1.max_cc = 7
    p2.cc = 2
    p2.max_cc = 7
    
    # Create game
    game_state = GameState(
        game_id="test",
        players={"p1": p1, "p2": p2},
        active_player_id="p1",
        first_player_id="p1",
        turn_number=2,
    )
    game_state.phase = Phase.MAIN  # Set to MAIN phase so we can play cards
    engine = GameEngine(game_state)
    
    print(f"Before: P2 CC = {p2.cc}, Umbruh in play")
    
    # Play Clean via GameEngine (should sleep all cards including Umbruh)
    success = engine.play_card(player=p1, card=clean)
    
    print(f"After: P2 CC = {p2.cc}, Umbruh in sleep zone: {umbruh in p2.sleep_zone}")
    
    # Assertions
    assert success, "Failed to play Clean"
    assert umbruh in p2.sleep_zone, "Umbruh should be in sleep zone"
    assert p2.cc == 3, f"P2 should have gained 1 CC from Umbruh trigger (expected 3, got {p2.cc})"
    # 2 initial CC + 1 from Umbruh when sleeped = 3
    
    print("✓ Clean + Umbruh interaction works correctly (Phase 3 fix validated)")


def run_all_tests():
    """Run all GameEngine/GameState separation tests."""
    print("=" * 60)
    print("GameEngine/GameState Separation Tests (Issue #85)")
    print("=" * 60)
    
    test_ballaber_sleeps_umbruh_from_play_triggers_cc_gain()
    test_ballaber_sleeps_umbruh_from_hand_no_trigger()
    test_snuggles_sleeps_umbruh_triggers_cc_gain()
    test_clean_sleeps_umbruh_triggers_cc_gain()
    
    print("\n" + "=" * 60)
    print("✓ All GameEngine/GameState separation tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
