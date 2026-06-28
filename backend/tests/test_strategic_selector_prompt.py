"""
Strategic selector prompt content - issue #338.

Pins that generate_strategic_prompt actually includes the board legend and
card-specific guidance (previously wired up in card_loader.py but never
called from here), and that the strategic-selection system instruction stays
free of card-specific knowledge (which belongs in card_guidance.yaml) and of
the index-selection schema's irrelevant V2-era output-format rules.
"""

from conftest import create_game_with_cards
from game_engine.ai.enumerator import enumerate_sequences
from game_engine.ai.prompts.sequence_format import add_tactical_labels
from game_engine.ai.prompts.strategic_selector import (
    generate_strategic_prompt,
    get_strategic_selector_system_instruction,
)


def _build_sequences(setup, player_id: str):
    sequences = enumerate_sequences(setup.game_state, player_id)
    return add_tactical_labels(sequences)


def test_prompt_includes_board_legend_and_card_guidance():
    setup, _ = create_game_with_cards(
        player1_hand=["Surge"],
        player1_in_play=["Knight"],
        player2_hand=["Ka", "Wizard"],
        player2_in_play=["Paper Plane"],
        player1_charge=5,
        player2_charge=0,
        active_player="player1",
        turn_number=3,
    )
    sequences = _build_sequences(setup, "player1")
    prompt = generate_strategic_prompt(setup.game_state, "player1", sequences, setup.engine)

    assert "<board_legend>" in prompt
    # Legend lines for every relevant card, with their short labels.
    assert "Y1" in prompt and "Surge" in prompt
    assert "Y2" in prompt and "Knight" in prompt
    assert "O1" in prompt and "Paper Plane" in prompt

    # The opponent's hand must never be exposed - this game hides hand
    # contents from the opponent.
    assert "Ka" not in prompt
    assert "Wizard" not in prompt

    assert "<card_guidance>" in prompt
    # Surge has a card_guidance.yaml entry.
    assert "Surge" in prompt
    # Knight is in play and has a card_guidance.yaml entry ("CRITICAL" threat,
    # auto-win quirk) - the system_instruction must not hardcode this by name
    # (see test_system_instruction_has_no_card_specific_knowledge below), so
    # card_guidance.yaml is the only place this information can come from.
    import re
    guidance_block = re.search(r"<card_guidance>(.*?)</card_guidance>", prompt, re.S).group(1)
    assert "Knight" in guidance_block

    # Candidate sequences should reference labels, not raw UUIDs, for any tussle target.
    for seq in sequences:
        raw = seq["raw_string"]
        if "tussle Knight->" in raw:
            assert "tussle Knight->O1" in raw


def test_system_instruction_has_no_card_specific_knowledge():
    """The system_instruction is supposed to be generic framing - per-card quirks
    (Knight's auto-win, Raggy's free tussles, Wizard's 1charge tussles, etc.) belong
    only in card_guidance.yaml, which is dynamically filtered to cards actually
    in the current game. Hardcoding a specific card's name here would duplicate
    that data-driven source and go stale as cards are added/changed."""
    instruction = get_strategic_selector_system_instruction()

    for card_name in ("Knight", "Raggy", "Wizard", "Ka", "Archer", "Gibbers"):
        assert card_name not in instruction, (
            f"system_instruction must not name specific cards like {card_name!r} - "
            "that knowledge belongs in card_guidance.yaml"
        )


def test_prompt_works_without_game_engine():
    """game_engine is optional; legend still renders using base stats."""
    setup, _ = create_game_with_cards(
        player1_hand=[],
        player1_in_play=["Knight"],
        player2_hand=[],
        player2_in_play=[],
        player1_charge=2,
        player2_charge=0,
        active_player="player1",
        turn_number=3,
    )
    sequences = _build_sequences(setup, "player1")
    prompt = generate_strategic_prompt(setup.game_state, "player1", sequences)
    assert "Knight" in prompt
    assert "<board_legend>" in prompt


def test_strategic_system_instruction_has_no_index_selection_leakage():
    instruction = get_strategic_selector_system_instruction()

    # The action_number / [ID: xxx] extraction rules belong to the old
    # per-action selection prompt and don't apply to this index-selection
    # schema; they must not leak in.
    assert "action_number" not in instruction
    assert "[ID: xxx]" not in instruction

    # It should still cover the basics needed to judge a pre-validated tussle.
    assert "Break Zone" in instruction
    assert "Stamina" in instruction or "STA" in instruction


def test_strategic_system_instruction_is_stable_string():
    assert get_strategic_selector_system_instruction() == get_strategic_selector_system_instruction()
