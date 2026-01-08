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

def test_prompt_header_with_rush():
    """
    Verify behavior when Rush IS in hand.
    """
    # Setup: 6 CC, Rush in hand
    setup, cards = create_game_with_cards(
        player1_hand=["Rush", "Knight"],
        player1_cc=6,
        active_player="player1"
    )
    
    # Generate prompt
    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)
    
    lines = prompt.split("\n")
    cc_line = next(line for line in lines if line.startswith("## CC:"))
    
    print(f"\nGenerated Header: {cc_line}")
    
    # This should now show the dynamic potential text for Rush
    assert "Max potential: 8 via Rush +2" in cc_line

def test_prompt_header_with_surge_and_rush():
    """
    Verify behavior when BOTH Surge and Rush are in hand.
    """
    # Setup: 6 CC, Surge and Rush in hand
    setup, cards = create_game_with_cards(
        player1_hand=["Surge", "Rush"],
        player1_cc=6,
        active_player="player1"
    )
    
    # Generate prompt
    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)
    
    lines = prompt.split("\n")
    cc_line = next(line for line in lines if line.startswith("## CC:"))
    
    print(f"\nGenerated Header: {cc_line}")
    
    # This should now show the dynamic potential text for both
    assert "Max potential: 9 via" in cc_line
    assert "Surge +1" in cc_line
    assert "Rush +2" in cc_line


def test_prompt_sleep_zone_has_actionable_card_info():
    """Regression test for Issue #295: sleep zone prompt should include more than name/id."""
    setup, cards = create_game_with_cards(
        player1_hand=["Wake"],
        player1_sleep=["Knight"],
        player1_cc=4,
        active_player="player1",
        turn_number=1,
    )

    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)

    # The sleep zone section should contain compact details including cost/type/stats.
    # With the v3 compact formatter, toys show "(XCC, ... SPD/STR/STA)" and actions show "(ACTION, XCC)".
    assert "## YOUR SLEEP ZONE (for Wake targeting)" in prompt
    assert "Knight" in prompt
    assert "1CC" in prompt
    assert "SPD/STR/STA" in prompt
