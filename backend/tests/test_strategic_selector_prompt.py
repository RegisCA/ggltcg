"""
Strategic selector (Request 2) prompt content - issue #338.

Pins that generate_strategic_prompt actually includes the board legend and
card-specific guidance (previously wired up in card_loader.py but never
called from here), and that the Request-2-specific system instruction is
distinct from the V2 SYSTEM_PROMPT (whose output-format section doesn't
apply to index-selection).
"""

from conftest import create_game_with_cards
from game_engine.ai.enumerator import enumerate_sequences
from game_engine.ai.prompts.sequence_generator import add_tactical_labels
from game_engine.ai.prompts.strategic_selector import (
    generate_strategic_prompt,
    get_strategic_selector_system_instruction,
)
from game_engine.ai.prompts.system_prompt import SYSTEM_PROMPT


def _build_sequences(setup, player_id: str):
    sequences = enumerate_sequences(setup.game_state, player_id)
    return add_tactical_labels(sequences)


def test_prompt_includes_board_legend_and_card_guidance():
    setup, _ = create_game_with_cards(
        player1_hand=["Surge"],
        player1_in_play=["Knight"],
        player2_hand=["Ka", "Wizard"],
        player2_in_play=["Paper Plane"],
        player1_cc=5,
        player2_cc=0,
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
    # Surge has a card_guidance.yaml entry not covered by the system_instruction.
    assert "Surge" in prompt

    # Candidate sequences should reference labels, not raw UUIDs, for any tussle target.
    for seq in sequences:
        raw = seq["raw_string"]
        if "tussle Knight->" in raw:
            assert "tussle Knight->O1" in raw


def test_card_guidance_omits_cards_already_named_by_system_instruction():
    """Knight/Raggy/Wizard's mechanics are explicitly named in
    STRATEGIC_SELECTOR_SYSTEM_INSTRUCTION (Knight's auto-win, Raggy/Wizard's
    tussle-cost overrides) - their card_guidance.yaml bullets would just repeat
    that, so the <card_guidance> block must exclude them even when they're on
    the board. They may still appear elsewhere in the prompt (the legend,
    valid_sequences) - only the per-card guidance bullet is suppressed."""
    setup, _ = create_game_with_cards(
        player1_hand=[],
        player1_in_play=["Knight"],
        player2_hand=[],
        player2_in_play=["Wizard"],
        player1_cc=5,
        player2_cc=0,
        active_player="player1",
        turn_number=3,
    )
    sequences = _build_sequences(setup, "player1")
    prompt = generate_strategic_prompt(setup.game_state, "player1", sequences, setup.engine)

    import re
    guidance_block = re.search(r"<card_guidance>(.*?)</card_guidance>", prompt, re.S).group(1)

    assert "Knight" not in guidance_block
    assert "Wizard" not in guidance_block
    # Knight/Wizard still appear in the legend - just not duplicated as guidance bullets.
    assert "Knight" in prompt
    assert "Wizard" in prompt


def test_prompt_works_without_game_engine():
    """game_engine is optional; legend still renders using base stats."""
    setup, _ = create_game_with_cards(
        player1_hand=[],
        player1_in_play=["Knight"],
        player2_hand=[],
        player2_in_play=[],
        player1_cc=2,
        player2_cc=0,
        active_player="player1",
        turn_number=3,
    )
    sequences = _build_sequences(setup, "player1")
    prompt = generate_strategic_prompt(setup.game_state, "player1", sequences)
    assert "Knight" in prompt
    assert "<board_legend>" in prompt


def test_strategic_system_instruction_is_not_v2_system_prompt():
    instruction = get_strategic_selector_system_instruction()

    assert instruction != SYSTEM_PROMPT
    # V2's output-format section (action_number / [ID: xxx] extraction) doesn't
    # apply to Request 2's index-selection schema and must not leak in.
    assert "action_number" not in instruction
    assert "[ID: xxx]" not in instruction

    # It should still cover the basics needed to judge a pre-validated tussle.
    assert "Sleep Zone" in instruction
    assert "Stamina" in instruction or "STA" in instruction


def test_strategic_system_instruction_is_stable_string():
    assert get_strategic_selector_system_instruction() == get_strategic_selector_system_instruction()
