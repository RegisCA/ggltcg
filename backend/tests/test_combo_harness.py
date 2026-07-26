"""Combo ablation harness (``simulation.combo``).

Gates pinned here:

1. **Paired ablation** — a ``drop:X`` deck must differ from the full deck by
   exactly one card. If the fillers were redrawn per variant, the measured
   "contribution of X" would also contain filler luck, and at a few thousand
   games that noise would swamp the effect the harness exists to detect.
2. **Enumerator ceiling is actually raised** — the whole point of the harness is
   reaching turns longer than the engine's 8-action default. A turn that is never
   enumerated can never be played, so a silently-ignored override would make every
   combo look worthless.
"""

import random

import pytest

from simulation.combo import DECK_SIZE, build_variants, parse_combo, plan_trials
from simulation.sweep import _card_pool


@pytest.fixture(scope="module")
def pool_and_toys():
    return _card_pool()


def test_parse_combo_handles_alternation(pool_and_toys):
    pool, _ = pool_and_toys
    slots = parse_combo("Hind Leg Kicker,Jumpscare,Car|Dino|Block", pool)

    assert slots[0] == ["Hind Leg Kicker"]
    assert slots[1] == ["Jumpscare"]
    assert slots[2] == ["Car", "Dino", "Block"]


def test_parse_combo_rejects_unknown_and_oversized(pool_and_toys):
    pool, _ = pool_and_toys
    with pytest.raises(ValueError, match="unknown card"):
        parse_combo("Hind Leg Kicker,Nonexistent Card", pool)
    with pytest.raises(ValueError, match="deck holds"):
        parse_combo(",".join(list(pool)[:DECK_SIZE + 1]), pool)


def test_every_variant_is_a_legal_deck(pool_and_toys):
    pool, _ = pool_and_toys
    slots = parse_combo("Hind Leg Kicker,Jumpscare,That was fun,Car|Dino", pool)
    variants = build_variants(slots, random.Random(7), pool)

    for name, deck in variants.items():
        assert len(deck) == DECK_SIZE, f"{name} has {len(deck)} cards"
        assert len(set(deck)) == DECK_SIZE, f"{name} has duplicates"
        assert set(deck) <= set(pool)


def test_drop_variant_differs_from_full_by_exactly_one_card(pool_and_toys):
    """The paired design: swap one combo piece for the next shared filler."""
    pool, _ = pool_and_toys
    slots = parse_combo("Hind Leg Kicker,Jumpscare,That was fun,Car|Dino", pool)
    variants = build_variants(slots, random.Random(11), pool)
    full = set(variants["full"])

    drops = [k for k in variants if k.startswith("drop:")]
    assert len(drops) == len(slots)

    for name in drops:
        deck = set(variants[name])
        assert len(full - deck) == 1, f"{name} removed more than one card"
        assert len(deck - full) == 1, f"{name} added more than one card"


def test_alternation_slot_keeps_one_stable_variant_key(pool_and_toys):
    """An alternation slot must aggregate across trials, not split into one cell
    per option -- splitting would shred the sample size it needs."""
    pool, _ = pool_and_toys
    slots = parse_combo("Hind Leg Kicker,Car|Dino|Block|MaBookBook", pool)

    keys = {frozenset(build_variants(slots, random.Random(s), pool)) for s in range(25)}
    assert len(keys) == 1, "variant keys changed with the trial's alternation pick"

    (only,) = keys
    assert "drop:any(Car|Dino|Block|MaBookBook)" in only
    assert "drop:Hind Leg Kicker" in only


def test_none_variant_contains_no_combo_pieces(pool_and_toys):
    pool, _ = pool_and_toys
    slots = parse_combo("Hind Leg Kicker,Jumpscare,That was fun", pool)
    variants = build_variants(slots, random.Random(3), pool)

    chosen = set(variants["full"]) - set(variants["none"])
    assert {"Hind Leg Kicker", "Jumpscare", "That was fun"} <= chosen
    for card in ("Hind Leg Kicker", "Jumpscare", "That was fun"):
        assert card not in variants["none"]


def test_trials_are_reproducible_from_the_seed(pool_and_toys):
    pool, toys = pool_and_toys
    slots = parse_combo("Hind Leg Kicker,Jumpscare", pool)
    a = plan_trials(5, 4, slots, pool, 2, toys)
    b = plan_trials(5, 4, slots, pool, 2, toys)
    assert a == b


def test_opponent_decks_respect_the_toy_floor(pool_and_toys):
    pool, toys = pool_and_toys
    slots = parse_combo("Hind Leg Kicker,Jumpscare", pool)
    for trial in plan_trials(2, 25, slots, pool, 2, toys):
        assert sum(1 for c in trial["opponent"] if c in toys) >= 2


def test_max_actions_override_reaches_the_enumerator(monkeypatch):
    """A silently-ignored ceiling would make every long-turn combo look worthless.

    Drives the ceiling the way the harness does -- through SimulationRunner's
    constructor -- so this exercises the production path rather than a patch the
    test applied itself.
    """
    import game_engine.ai.turn_planner as tp

    seen = {}
    real = tp.enumerate_sequences

    def spy(game_state, player_id, **kwargs):
        seen.update(kwargs)
        return real(game_state, player_id, **kwargs)

    monkeypatch.setattr(tp, "enumerate_sequences", spy)

    from simulation.deck_loader import load_simulation_decks_dict
    from simulation.runner import SimulationRunner

    decks = [d for _, d in sorted(load_simulation_decks_dict().items())]
    runner = SimulationRunner(
        player1_policy="greedy", player2_policy="greedy",
        policy_max_actions=14, policy_max_sequences=24,
    )
    runner.run_game(decks[0], decks[2], game_number=1, seed=1)

    assert seen.get("max_actions") == 14
    assert seen.get("max_sequences") == 24


def test_search2_models_the_opponent_at_the_same_ceiling():
    """The reply model must use the caller's ceilings.

    Left at defaults, our own lines enumerate to a raised cap while the opponent's
    reply is modelled at 8 -- understating the counterattack in exactly the runs
    where long turns are the point, and biasing every combo measurement.
    """
    from unittest.mock import patch

    from simulation.deck_loader import load_simulation_decks_dict
    from simulation.runner import SimulationRunner


    seen: list[dict] = []

    import game_engine.ai.enumerator as enum_mod
    real_enum = enum_mod.enumerate_sequences

    def spy(game_state, player_id, **kwargs):
        seen.append(kwargs)
        return real_enum(game_state, player_id, **kwargs)

    decks = [d for _, d in sorted(load_simulation_decks_dict().items())]
    with patch.object(enum_mod, "enumerate_sequences", spy):
        runner = SimulationRunner(
            player1_policy="search2", player2_policy="search2",
            policy_max_actions=11, policy_max_sequences=13,
        )
        runner.run_game(decks[0], decks[4], game_number=1, seed=4)

    assert seen, "search2 never enumerated an opponent reply"
    assert all(k.get("max_actions") == 11 for k in seen), seen[:3]
    assert all(k.get("max_sequences") == 13 for k in seen), seen[:3]


def test_default_planner_leaves_enumerator_limits_untouched():
    """Live games must keep the engine defaults — the override is opt-in only."""
    from game_engine.ai.turn_planner import TurnPlanner

    assert TurnPlanner.enum_max_actions is None
    assert TurnPlanner.enum_max_sequences is None
