"""
Regression test pinning the AI CC-gain tables to real cards.

Two hard-coded tables tell the AI which cards grant CC *when played*:
- CCBudgetValidator.CC_GAIN_ON_PLAY (turn plan validator)
- TurnPlanner._CC_GAIN_ON_PLAY (turn planner)

A June 2026 audit found a phantom "HLK" key in both — no such card exists
(the real card is "Hind Leg Kicker", and its effect is on_card_played, not
gain-on-play), so the entry never fired. These tests keep the tables honest:
every key must be a real card whose CSV effect is a play-triggered `gain_cc:`,
and the two tables must agree with each other and with the card data.
"""

from game_engine.data.card_loader import load_cards_dict
from game_engine.ai.validators.turn_plan_validator import CCBudgetValidator
from game_engine.ai.turn_planner import TurnPlanner


def _has_play_triggered_gain_cc(effect_definitions: str) -> bool:
    """True if the card has a bare ``gain_cc:`` effect (fires when the card is played).

    Distinguishes the play-triggered ``gain_cc`` from the other CC-gain effects
    whose first colon-segment differs: ``start_of_turn_gain_cc``,
    ``on_card_played_gain_cc``, ``gain_cc_when_sleeped``.
    """
    for token in (effect_definitions or "").split(";"):
        if token.strip().split(":")[0] == "gain_cc":
            return True
    return False


def _cards_with_play_gain_cc() -> set[str]:
    return {
        name
        for name, card in load_cards_dict().items()
        if _has_play_triggered_gain_cc(card.effect_definitions)
    }


def test_validator_cc_gain_keys_are_real_play_gain_cards():
    """Every CCBudgetValidator.CC_GAIN_ON_PLAY key is a real card that gains CC on play."""
    cards = load_cards_dict()
    for name in CCBudgetValidator.CC_GAIN_ON_PLAY:
        assert name in cards, (
            f"CC_GAIN_ON_PLAY key {name!r} is not a card in cards.csv "
            f"(phantom entry, like the old 'HLK')"
        )
        assert _has_play_triggered_gain_cc(cards[name].effect_definitions), (
            f"CC_GAIN_ON_PLAY key {name!r} exists but has no play-triggered "
            f"gain_cc effect (got {cards[name].effect_definitions!r})"
        )


def test_planner_cc_gain_keys_are_real_play_gain_cards():
    """Every TurnPlanner._CC_GAIN_ON_PLAY key is a real card that gains CC on play."""
    cards = load_cards_dict()
    for name in TurnPlanner._CC_GAIN_ON_PLAY:
        assert name in cards, (
            f"_CC_GAIN_ON_PLAY key {name!r} is not a card in cards.csv"
        )
        assert _has_play_triggered_gain_cc(cards[name].effect_definitions), (
            f"_CC_GAIN_ON_PLAY key {name!r} exists but has no play-triggered "
            f"gain_cc effect (got {cards[name].effect_definitions!r})"
        )


def test_cc_gain_tables_match_each_other():
    """The validator and planner tables are meant to mirror each other exactly."""
    assert CCBudgetValidator.CC_GAIN_ON_PLAY == TurnPlanner._CC_GAIN_ON_PLAY, (
        "CCBudgetValidator.CC_GAIN_ON_PLAY and TurnPlanner._CC_GAIN_ON_PLAY have "
        "diverged; they must stay in sync."
    )


def test_cc_gain_tables_cover_all_play_gain_cards():
    """The tables include every card that actually gains CC on play (no omissions)."""
    expected = _cards_with_play_gain_cc()
    assert set(CCBudgetValidator.CC_GAIN_ON_PLAY) == expected, (
        f"CC_GAIN_ON_PLAY {set(CCBudgetValidator.CC_GAIN_ON_PLAY)} does not match "
        f"the set of cards with a play-triggered gain_cc effect {expected}"
    )
