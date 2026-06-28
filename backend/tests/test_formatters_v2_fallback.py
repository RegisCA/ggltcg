"""
V2 fallback prompt formatting after card_library.py retirement - issue #338.

format_game_state_for_ai used to read effect text and opponent-threat level
from CARD_EFFECTS_LIBRARY (card_library.py, now deleted). It now reads each
card's own effect_text (from cards.csv) and looks up threat from
card_guidance.yaml via card_loader.load_card_guidance(). This pins that the
six cards migrated from card_library.py into card_guidance.yaml (Ballaber,
Demideca, Drum, Jumpscare, "That was fun", Toynado) still produce sane V2
fallback prompt text, and that vanilla Toys with no guidance entry don't
crash threat lookup.
"""

from conftest import create_game_with_cards
from game_engine.ai.prompts.card_loader import load_card_guidance
from game_engine.ai.prompts.formatters import format_game_state_for_ai


def test_migrated_cards_show_real_effect_text_in_hand():
    setup, _ = create_game_with_cards(
        player1_hand=["Ballaber", "Demideca", "Drum", "Jumpscare", "That was fun", "Toynado"],
        player1_in_play=[],
        player2_hand=[],
        player2_in_play=[],
        player1_charge=3,
        player2_charge=0,
        active_player="player1",
        turn_number=1,
    )
    state_text = format_game_state_for_ai(setup.game_state, "player1", setup.engine)

    # Effect text now comes straight from each Card's own effect_text (cards.csv),
    # not a duplicated copy in a now-deleted library dict.
    assert "break 1 of your cards to play this card for free" in state_text  # Ballaber
    assert "+ 1 of all stats" in state_text  # Demideca
    assert "2 more speed" in state_text  # Drum
    assert "into their owner" in state_text  # Jumpscare / Toynado phrasing
    assert "Fix an action card" in state_text  # That was fun


def test_opponent_threat_lookup_uses_card_guidance_yaml():
    setup, _ = create_game_with_cards(
        player1_hand=[],
        player1_in_play=[],
        player2_hand=[],
        player2_in_play=["Knight"],
        player1_charge=3,
        player2_charge=0,
        active_player="player1",
        turn_number=1,
    )
    state_text = format_game_state_for_ai(setup.game_state, "player1", setup.engine)

    guidance = load_card_guidance()
    assert guidance["Knight"]["threat"] == "CRITICAL"
    assert "THREAT: CRITICAL" in state_text


def test_vanilla_toy_with_no_guidance_entry_shows_unknown_threat():
    """Block/Car/Dino are vanilla Toys with intentionally no card_guidance.yaml entry."""
    setup, _ = create_game_with_cards(
        player1_hand=[],
        player1_in_play=[],
        player2_hand=[],
        player2_in_play=["Block"],
        player1_charge=3,
        player2_charge=0,
        active_player="player1",
        turn_number=1,
    )
    state_text = format_game_state_for_ai(setup.game_state, "player1", setup.engine)
    assert "THREAT: UNKNOWN" in state_text
