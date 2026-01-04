import pytest
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards
from game_engine.ai.prompts.sequence_generator import generate_sequence_prompt

def test_prompt_header_pollution_no_surge_rush():
    """
    Reproduction test for Issue #11: CC Header Pollution.
    
    Verifies that the prompt header currently includes static text about 
    Surge/Rush bonuses even when those cards are NOT in hand.
    """
    # Setup: 6 CC, NO Surge/Rush in hand
    setup, cards = create_game_with_cards(
        player1_hand=["Umbruh", "Knight"], # No Surge, No Rush
        player1_cc=6,
        active_player="player1"
    )
    
    # Generate prompt
    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)
    
    # Extract header line (usually line 3)
    lines = prompt.split("\n")
    cc_line = next(line for line in lines if line.startswith("## CC:"))
    
    print(f"\nGenerated Header: {cc_line}")
    
    # ASSERTION (Fixed Behavior):
    # The header SHOULD NOT contain this text if we don't have the cards.
    assert "(Surge adds +1, Rush adds +2 when played)" not in cc_line, \
        "Bug present: Static header text still exists!"
    
    # It should just show the base CC
    assert f"## CC: {setup.player1.cc}" in cc_line
    assert "Max potential" not in cc_line

def test_prompt_header_with_surge():
    """
    Verify behavior when Surge IS in hand.
    """
    # Setup: 6 CC, Surge in hand
    setup, cards = create_game_with_cards(
        player1_hand=["Surge", "Knight"],
        player1_cc=6,
        active_player="player1"
    )
    
    # Generate prompt
    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)
    
    lines = prompt.split("\n")
    cc_line = next(line for line in lines if line.startswith("## CC:"))
    
    print(f"\nGenerated Header: {cc_line}")
    
    # This should now show the dynamic potential text
    assert "Max potential: 7 via Surge +1" in cc_line
