import pytest
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards
from game_engine.ai.prompts.sequence_generator import generate_sequence_prompt

def test_prompt_no_summoning_sickness_hint():
    """
    Verify that the prompt explicitly states there is no summoning sickness.
    """
    setup, cards = create_game_with_cards(
        player1_hand=["Knight"],
        player1_cc=4,
        active_player="player1"
    )
    
    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)
    
    assert "Toys can tussle the SAME TURN" in prompt, "Prompt missing immediate tussle hint"

def test_prompt_wake_mechanics_hint():
    """
    Verify that the prompt correctly explains Wake mechanics (Sleep -> Hand -> Play).
    """
    setup, cards = create_game_with_cards(
        player1_hand=["Wake"],
        player1_sleep=["Knight"],
        player1_cc=4,
        active_player="player1"
    )
    
    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)
    
    assert "Wake moves card to HAND" in prompt, "Prompt missing Wake->Hand explanation"
    assert "must pay cost to play it again" in prompt, "Prompt missing re-play cost warning"

def test_prompt_hind_leg_kicker_potential():
    """
    Verify that Hind Leg Kicker adds to the potential CC calculation.
    """
    # Setup: 2 CC, Hind Leg Kicker + 2 other cards in hand
    setup, cards = create_game_with_cards(
        player1_hand=["Hind Leg Kicker", "Drum", "Violin"],
        player1_cc=2,
        active_player="player1"
    )
    
    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)
    
    # Potential CC should be:
    # Base: 2
    # Hind Leg Kicker bonus: +2 (for the 2 other cards)
    # Total Potential: 4
    
    lines = prompt.split("\n")
    cc_line = next(line for line in lines if line.startswith("## CC:"))
    
    print(f"\nGenerated Header: {cc_line}")
    
    assert "Hind Leg Kicker" in cc_line, "Header missing Hind Leg Kicker"
    # We check for presence of the bonus text
    assert "Hind Leg Kicker +2" in cc_line
