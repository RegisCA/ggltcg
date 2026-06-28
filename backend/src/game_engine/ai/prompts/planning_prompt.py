"""
Shared planning-prompt helper(s).

The original v3 4-phase planning prompt and its formatters lived here but were
superseded by ``planning_prompt_v3.py`` (active) and removed in the June 2026
dead-code sweep. Only ``format_break_zone_for_planning`` remains — it is still
imported by ``turn_planner.py`` via the prompts package.
"""


def format_break_zone_for_planning(break_zone: list) -> str:
    """Format break zone cards (just names and IDs)."""
    if not break_zone:
        return "EMPTY"

    lines = []
    for card in break_zone:
        lines.append(f"  - [ID: {card.id}] {card.name}")
    return "\n".join(lines)
