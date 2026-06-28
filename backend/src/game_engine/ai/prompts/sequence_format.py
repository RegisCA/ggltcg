"""
Formatting helpers for enumerator-produced action sequences.

The enumerator (``game_engine.ai.enumerator``) computes candidate sequences
engine-side; these helpers label and render them for the strategic-selection
prompt (``strategic_selector.py``).
"""


def add_tactical_labels(sequences: list[dict]) -> list[dict]:
    """
    Add tactical labels to validated sequences.

    Labels help the strategic selector understand what each sequence accomplishes:
    - [Lethal]: Can win this turn (6+ cards broken)
    - [Aggressive Removal]: Multiple attacks
    - [Resource Building]: Plays Surge/Rush without attacking
    - [Board Setup]: Plays multiple toys without attacking
    - [Conservative]: Minimal Charge spent
    - [Balanced]: Everything else
    """
    for seq in sequences:
        # Skip if already labeled
        if "tactical_label" in seq:
            continue

        actions = seq.get("actions", [])
        cards_broken = seq.get("cards_broken", 0)
        charge_spent = seq.get("total_charge_spent", 0)

        # Count action types
        attack_count = sum(1 for a in actions if a.get("action_type") in ["tussle", "direct_attack"])
        play_count = sum(1 for a in actions if a.get("action_type") == "play_card")
        has_resource = any(a.get("card_name") in ["Surge", "Rush"] for a in actions)

        # Determine label
        if cards_broken >= 6:
            seq["tactical_label"] = "[Lethal]"
        elif attack_count >= 2:
            seq["tactical_label"] = "[Aggressive Removal]"
        elif has_resource and attack_count == 0:
            seq["tactical_label"] = "[Resource Building]"
        elif play_count >= 2 and attack_count == 0:
            seq["tactical_label"] = "[Board Setup]"
        elif charge_spent <= 2:
            seq["tactical_label"] = "[Conservative]"
        else:
            seq["tactical_label"] = "[Balanced]"

    return sequences


def format_sequence_for_display(seq: dict, index: int) -> str:
    """
    Format a sequence for display in the strategic-selection prompt.

    Args:
        seq: Sequence dictionary
        index: 0-based sequence index

    Returns:
        Formatted string showing sequence summary
    """
    label = seq.get("tactical_label", "[Unknown]")
    raw = seq.get("raw_string", "")
    charge_spent = seq.get("total_charge_spent", 0)
    charge_avail = seq.get("charge_available", 0)
    cards_broken = seq.get("cards_broken", 0)

    return f'{index}. {label} broken={cards_broken} charge={charge_spent}/{charge_avail} :: {raw}'
