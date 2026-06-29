"""Card metadata derived from cards.csv, shared across the AI layer.

Single source of truth for facts that several AI modules previously hardcoded
independently (and which drifted — e.g. one copy was missing Cake). Computed
once at import time since cards.csv doesn't change at runtime.
"""
from game_engine.data.card_loader import load_cards_dict
from game_engine.models.card import CardType


def _has_play_triggered_gain_charge(effect_definitions: str) -> bool:
    """True for a bare ``gain_charge:N`` effect (fires when the card is played).

    Distinguishes the play-triggered ``gain_charge`` from other Charge-gain
    effects whose first colon-segment differs: ``start_of_turn_gain_charge``,
    ``on_card_played_gain_charge``, ``gain_charge_when_broken``.
    """
    for token in (effect_definitions or "").split(";"):
        if token.strip().split(":")[0] == "gain_charge":
            return True
    return False


def _build_charge_gain_on_play() -> dict[str, int]:
    table: dict[str, int] = {}
    for name, card in load_cards_dict().items():
        if not _has_play_triggered_gain_charge(card.effect_definitions):
            continue
        for token in card.effect_definitions.split(";"):
            parts = token.strip().split(":")
            if parts[0] == "gain_charge":
                table[name] = int(parts[1])
                break
    return table


def _build_action_card_names() -> frozenset[str]:
    return frozenset(
        name for name, card in load_cards_dict().items()
        if card.card_type == CardType.ACTION
    )


CHARGE_GAIN_ON_PLAY: dict[str, int] = _build_charge_gain_on_play()
ACTION_CARD_NAMES: frozenset[str] = _build_action_card_names()
