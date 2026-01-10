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

    # The sleep zone section should contain actionable details including cost/stats/effects.
    assert "## YOUR SLEEP ZONE (Sleep Zone)" in prompt
    assert "Knight" in prompt
    assert "eff_cost=" in prompt
    assert "SPD/STR/STA=" in prompt
    assert "effects=" in prompt


def test_request1_state_schema_has_required_fields_and_no_hp_label():
    """Guardrail: Request 1 should use consistent schema and STA (not HP)."""
    setup, cards = create_game_with_cards(
        player1_hand=["Umbruh", "Surge"],
        player1_in_play=["Ka"],
        player1_sleep=["Knight"],
        player1_cc=4,
        player2_in_play=["Demideca"],
        active_player="player1",
        turn_number=1,
    )

    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)

    assert "HP=" not in prompt
    assert "SPD/STR/STA=" in prompt
    assert "eff_cost=" in prompt
    assert "effects=" in prompt
    assert "## OPPONENT HAND (Hand):" in prompt
    assert "## OPPONENT SLEEP ZONE (Sleep Zone):" in prompt


def test_request1_direct_attack_wording_matches_quick_reference():
    """Guardrail: direct_attack wording must match QUICK_REFERENCE mechanics."""
    setup, cards = create_game_with_cards(
        player1_hand=["Umbruh"],
        player1_cc=4,
        player2_in_play=["Ka"],
        active_player="player1",
        turn_number=1,
    )

    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)

    assert "## ACTIONS & COSTS" in prompt
    assert (
        "| **Direct Attack** | 2 CC (default) | Only when opponent has no Toys In Play. Max 2 per turn. "
        "Random card from opponent's Hand → Sleep Zone. |" in prompt
    )
    assert "direct_attack doesn't sleep toys" not in prompt
    assert "summoning sickness" not in prompt


def test_request1_explicit_play_from_hand_only_constraint():
    """
    Guardrail: Prompt MUST explicitly state that cards can ONLY be played from Hand.
    
    This prevents the model from attempting to play cards from Sleep Zone or In Play.
    Issue found in game c18ec8d3-3e1c-4114-abc0-edc16e23eb5c where sequences
    tried to play Surge from Sleep Zone.
    """
    setup, cards = create_game_with_cards(
        player1_hand=["Umbruh", "Wake"],
        player1_sleep=["Surge", "Ka"],
        player1_cc=5,
        active_player="player1",
        turn_number=3,
    )

    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)

    # Must have the explicit constraint section
    assert "## CRITICAL PLAY CONSTRAINT" in prompt
    assert "You can ONLY play cards from YOUR HAND (Hand)" in prompt
    assert "Cards in YOUR TOYS IN PLAY (In Play) or YOUR SLEEP ZONE (Sleep Zone) CANNOT be played" in prompt
    assert "You must use card IDs from the YOUR HAND section" in prompt
