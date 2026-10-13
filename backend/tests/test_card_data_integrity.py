"""
Data-integrity gate for backend/data/cards.csv.

Replaces the old manual ``scripts/validate_new_cards.py`` (which had rotted:
it imported a long-deleted ``CARD_EFFECTS_LIBRARY`` and read a column that no
longer exists). Running in CI means a bad row fails the PR that adds it.

The card loader is deliberately forgiving — an unparseable cost becomes 0, a
partially-filled stat line silently turns a Toy into an Action, a bad color
falls back to a default — so these checks read the raw CSV rather than the
loaded ``Card`` objects.
"""

import csv
import re
from pathlib import Path

import pytest

from game_engine.ai.prompts.card_loader import load_card_guidance
from game_engine.data.card_loader import load_cards_dict
from game_engine.rules.effects.effect_registry import EffectFactory

CSV_PATH = Path(__file__).parent.parent / "data" / "cards.csv"
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
STATS = ("speed", "strength", "stamina")


def _active_rows():
    with open(CSV_PATH, newline="") as f:
        return [row for row in csv.DictReader(f) if row.get("status") == "18"]


ACTIVE_ROWS = _active_rows()


def _ids(rows):
    return [row["name"] for row in rows]


def test_card_names_are_unique():
    names = _ids(ACTIVE_ROWS)
    duplicates = sorted({n for n in names if names.count(n) > 1})
    assert not duplicates, f"Duplicate card names: {duplicates}"


@pytest.mark.parametrize("row", ACTIVE_ROWS, ids=_ids(ACTIVE_ROWS))
def test_cost_is_an_integer(row):
    # -1 is the variable-cost sentinel (Copy, Glue, Stomp); "?" is its legacy spelling.
    cost = row["cost"].strip()
    assert cost == "?" or re.fullmatch(r"-?\d+", cost), f"{row['name']}: bad cost {cost!r}"


@pytest.mark.parametrize("row", ACTIVE_ROWS, ids=_ids(ACTIVE_ROWS))
def test_stats_are_all_or_nothing_integers(row):
    values = [row[s].strip() for s in STATS]
    if not any(values):
        return  # Action card
    assert all(re.fullmatch(r"\d+", v) for v in values), (
        f"{row['name']}: a Toy needs integer speed/strength/stamina, got {values}"
    )


@pytest.mark.parametrize("row", ACTIVE_ROWS, ids=_ids(ACTIVE_ROWS))
def test_colors_are_hex(row):
    for column in ("primary_color", "accent_color"):
        assert HEX_COLOR.match(row[column].strip()), f"{row['name']}: bad {column} {row[column]!r}"


@pytest.mark.parametrize("row", ACTIVE_ROWS, ids=_ids(ACTIVE_ROWS))
def test_effects_parse(row):
    """Every effect string must be understood by EffectFactory (it raises on unknown types)."""
    card = load_cards_dict()[row["name"]]
    effects = EffectFactory.parse_effects(row["effects"].strip(), card)
    if row["effects"].strip():
        assert effects, f"{row['name']}: effects {row['effects']!r} parsed to nothing"


def test_every_card_with_an_effect_has_ai_guidance():
    guidance = load_card_guidance()
    missing = [row["name"] for row in ACTIVE_ROWS if row["effects"].strip() and row["name"] not in guidance]
    assert not missing, f"Add card_guidance.yaml entries for: {missing}"


def test_no_orphaned_ai_guidance():
    names = set(_ids(ACTIVE_ROWS))
    orphaned = [name for name in load_card_guidance() if name not in names]
    assert not orphaned, f"card_guidance.yaml entries for cards not in cards.csv: {orphaned}"
