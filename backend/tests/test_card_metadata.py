"""
Regression test pinning the AI Charge-gain table to real cards.

A June 2026 audit found that the AI layer maintained four hand-copied
Charge-gain-on-play tables, and one (enumerator.py) had already drifted —
missing "Cake". This test pins the single CSV-derived source
(``game_engine.ai.card_metadata``) instead of pinning duplicate copies against
each other.
"""

from game_engine.ai.card_metadata import CHARGE_GAIN_ON_PLAY, ACTION_CARD_NAMES
from game_engine.data.card_loader import load_cards_dict
from game_engine.models.card import CardType


def _has_play_triggered_gain_charge(effect_definitions: str) -> bool:
    for token in (effect_definitions or "").split(";"):
        if token.strip().split(":")[0] == "gain_charge":
            return True
    return False


def test_charge_gain_on_play_covers_every_real_play_gain_card():
    cards = load_cards_dict()
    expected = {
        name for name, card in cards.items()
        if _has_play_triggered_gain_charge(card.effect_definitions)
    }
    assert set(CHARGE_GAIN_ON_PLAY) == expected


def test_charge_gain_on_play_amounts_match_csv():
    cards = load_cards_dict()
    for name, amount in CHARGE_GAIN_ON_PLAY.items():
        for token in cards[name].effect_definitions.split(";"):
            parts = token.strip().split(":")
            if parts[0] == "gain_charge":
                assert amount == int(parts[1]), f"{name}: expected {parts[1]}, got {amount}"
                break
        else:
            raise AssertionError(f"{name} has no gain_charge token")


def test_charge_gain_on_play_includes_cake():
    """Cake was the card missing from the old, hand-copied enumerator.py table."""
    assert CHARGE_GAIN_ON_PLAY.get("Cake") == 5


def test_action_card_names_matches_csv_card_type():
    cards = load_cards_dict()
    expected = {name for name, card in cards.items() if card.card_type == CardType.ACTION}
    assert set(ACTION_CARD_NAMES) == expected
