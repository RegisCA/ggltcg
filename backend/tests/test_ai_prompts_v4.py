import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards
from game_engine.ai.prompts.sequence_generator import generate_sequence_prompt

def test_prompt_header_pollution_no_surge_rush():
    """
    Reproduction test for Issue #11: Charge Header Pollution.
    
    Verifies that the prompt header currently includes static text about 
    Surge/Rush bonuses even when those cards are NOT in hand.
    """
    # Setup: 6 Charge, NO Surge/Rush in hand
    setup, cards = create_game_with_cards(
        player1_hand=["Umbruh", "Knight"], # No Surge, No Rush
        player1_charge=6,
        active_player="player1"
    )
    
    # Generate prompt
    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)
    
    # Extract header line (usually line 3)
    lines = prompt.split("\n")
    charge_line = next(line for line in lines if line.startswith("## Charge:"))
    
    print(f"\nGenerated Header: {charge_line}")
    
    # ASSERTION (Fixed Behavior):
    # The header SHOULD NOT contain this text if we don't have the cards.
    assert "(Surge adds +1, Rush adds +2 when played)" not in charge_line, \
        "Bug present: Static header text still exists!"
    
    # It should just show the base Charge
    assert f"## Charge: {setup.player1.charge}" in charge_line
    assert "Max potential" not in charge_line

def test_prompt_header_with_surge():
    """
    Verify behavior when Surge IS in hand.
    """
    # Setup: 6 Charge, Surge in hand
    setup, cards = create_game_with_cards(
        player1_hand=["Surge", "Knight"],
        player1_charge=6,
        active_player="player1"
    )
    
    # Generate prompt
    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)
    
    lines = prompt.split("\n")
    charge_line = next(line for line in lines if line.startswith("## Charge:"))
    
    print(f"\nGenerated Header: {charge_line}")
    
    # This should now show the dynamic potential text
    assert "Max potential: 7 via Surge +1" in charge_line

def test_prompt_header_with_rush():
    """
    Verify behavior when Rush IS in hand.
    """
    # Setup: 6 Charge, Rush in hand
    setup, cards = create_game_with_cards(
        player1_hand=["Rush", "Knight"],
        player1_charge=6,
        active_player="player1"
    )
    
    # Generate prompt
    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)
    
    lines = prompt.split("\n")
    charge_line = next(line for line in lines if line.startswith("## Charge:"))
    
    print(f"\nGenerated Header: {charge_line}")
    
    # This should now show the dynamic potential text for Rush
    assert "Max potential: 8 via Rush +2" in charge_line

def test_prompt_header_with_surge_and_rush():
    """
    Verify behavior when BOTH Surge and Rush are in hand.
    """
    # Setup: 6 Charge, Surge and Rush in hand
    setup, cards = create_game_with_cards(
        player1_hand=["Surge", "Rush"],
        player1_charge=6,
        active_player="player1"
    )
    
    # Generate prompt
    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)
    
    lines = prompt.split("\n")
    charge_line = next(line for line in lines if line.startswith("## Charge:"))
    
    print(f"\nGenerated Header: {charge_line}")
    
    # This should now show the dynamic potential text for both
    assert "Max potential: 9 via" in charge_line
    assert "Surge +1" in charge_line
    assert "Rush +2" in charge_line


def test_prompt_break_zone_has_actionable_card_info():
    """Regression test for Issue #295: break zone prompt should include more than name/id."""
    setup, cards = create_game_with_cards(
        player1_hand=["Wake"],
        player1_break=["Knight"],
        player1_charge=4,
        active_player="player1",
        turn_number=1,
    )

    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)

    # The break zone section should contain actionable details including cost/stats/effects.
    assert "## YOUR BREAK ZONE (Break Zone)" in prompt
    assert "Knight" in prompt
    assert "eff_cost=" in prompt
    assert "SPD/STR/STA=" in prompt
    assert "effects=" in prompt


def test_request1_state_schema_has_required_fields_and_no_hp_label():
    """Guardrail: Request 1 should use consistent schema and STA (not HP)."""
    setup, cards = create_game_with_cards(
        player1_hand=["Umbruh", "Surge"],
        player1_in_play=["Ka"],
        player1_break=["Knight"],
        player1_charge=4,
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
    assert "## OPPONENT BREAK ZONE (Break Zone):" in prompt


def test_request1_direct_attack_wording_matches_quick_reference():
    """Guardrail: direct_attack wording must match QUICK_REFERENCE mechanics."""
    setup, cards = create_game_with_cards(
        player1_hand=["Umbruh"],
        player1_charge=4,
        player2_in_play=["Ka"],
        active_player="player1",
        turn_number=1,
    )

    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)

    assert "## ACTIONS & COSTS" in prompt
    assert (
        "| **Direct Attack** | 2 Charge (default) | Only when opponent has no Toys In Play. Max 2 per turn. "
        "Random card from opponent's Hand → Break Zone. |" in prompt
    )
    assert "direct_attack doesn't break toys" not in prompt
    assert "summoning sickness" not in prompt


def test_request1_explicit_play_from_hand_only_constraint():
    """
    Guardrail: Prompt MUST explicitly state that 'play' action requires cards in Hand.
    
    This prevents the model from attempting to play cards from Break Zone or In Play.
    Issue found in game c18ec8d3-3e1c-4114-abc0-edc16e23eb5c where sequences
    tried to play Surge from Break Zone.
    """
    setup, cards = create_game_with_cards(
        player1_hand=["Umbruh", "Wake"],
        player1_break=["Surge", "Ka"],
        player1_charge=5,
        active_player="player1",
        turn_number=3,
    )

    prompt = generate_sequence_prompt(setup.game_state, "player1", setup.engine)

    # Must have the explicit constraint section with clear wording
    assert "## CRITICAL CONSTRAINTS" in prompt
    assert "The 'play' action requires the card to be in YOUR HAND" in prompt
    assert "Use card IDs from the YOUR HAND section" in prompt
