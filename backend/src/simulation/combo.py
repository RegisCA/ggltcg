"""Measure a *declared* multi-card combo by ablation.

The random-deck sweep (``simulation.sweep``) estimates each card's average
contribution. That is the wrong instrument for a combo, for two reasons:

1. **Sample size.** At 200k games a specific pair co-occurs in ~7,700 decks, a
   triple in ~810, and a 4-card set in ~66 — against 91,390 candidate 4-sets.
   Blind search for a quad is not underpowered, it is impossible.
2. **Execution.** A combo has to actually be *played* to be measured, and the
   default ``greedy`` policy ranks lines by ``cards_broken`` first. A Charge-engine
   turn that bounces the opponent's board but breaks nothing scores zero on that
   key and is never selected. More games do not fix this.

So combos are declared, not discovered. This module forces a named card set into
every deck and measures it by **leave-one-out ablation**: drop one piece, replace
it with the same neutral filler the full deck would have used, and replay the
identical opponent and seed. The win-rate collapse when a piece is removed is that
piece's contribution *in context*; comparing it against the card's solo value from
the sweep gives superadditivity — the actual combo effect.

The design is paired throughout: variant decks differ from the full deck by
exactly one card, and face the same opponent under the same seed. That removes
opponent and filler variance instead of averaging over it, which is what makes a
few thousand games enough.

    python -m simulation.combo --combo "Hind Leg Kicker,Jumpscare,That was fun,Car|Dino|Block" \
        --games 2000 --policy search2 --max-actions 14
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import math
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Iterator, Optional, Sequence

DECK_SIZE = 6


def parse_combo(spec: str, pool: Sequence[str]) -> list[list[str]]:
    """Parse ``"A,B,C|D"`` into slots, where ``C|D`` means "any one of C or D".

    Alternation exists because combos are often written against a *role* rather
    than a card — "a 0-cost Toy" — and forcing one specific card would measure
    that card instead of the role.
    """
    slots = []
    for raw in spec.split(","):
        options = [o.strip() for o in raw.split("|") if o.strip()]
        unknown = [o for o in options if o not in pool]
        if unknown:
            raise ValueError(f"unknown card(s): {', '.join(unknown)}")
        if not options:
            raise ValueError(f"empty combo slot in {spec!r}")
        slots.append(options)
    if len(slots) > DECK_SIZE:
        raise ValueError(f"combo has {len(slots)} slots, deck holds {DECK_SIZE}")
    return slots


def slot_label(options: list[str]) -> str:
    """Stable name for a slot, independent of which card a trial happened to pick.

    Alternation slots must aggregate across trials. Labelling a variant by the
    *chosen* card instead would split one measurement into as many cells as the
    slot has options — at a few hundred trials that turns a usable estimate into
    several useless ones.
    """
    return options[0] if len(options) == 1 else f"any({'|'.join(options)})"


def build_variants(slots: list[list[str]], rng: random.Random,
                   pool: Sequence[str]) -> dict[str, list[str]]:
    """One trial's decks: the full combo plus each leave-one-out variant.

    Every variant draws fillers from the *same* shuffled remainder, so the full
    deck and ``drop:X`` differ by exactly one card — X swapped for the next
    filler. Without that the comparison would also be measuring filler luck.
    """
    chosen = [rng.choice(options) for options in slots]
    remainder = [c for c in pool if c not in chosen]
    rng.shuffle(remainder)

    variants: dict[str, list[str]] = {}
    n_filler = DECK_SIZE - len(chosen)
    variants["full"] = sorted(chosen + remainder[:n_filler])
    for i, options in enumerate(slots):
        kept = [c for j, c in enumerate(chosen) if j != i]
        variants[f"drop:{slot_label(options)}"] = sorted(kept + remainder[:n_filler + 1])
    # All combo pieces removed — isolates the fillers' own contribution.
    variants["none"] = sorted(remainder[:DECK_SIZE])
    return variants


def plan_trials(base_seed: int, trials: int, slots: list[list[str]],
                pool: Sequence[str], min_toys: int, toys: set[str]) -> list[dict]:
    """Build every trial up front so a run is fully determined by ``base_seed``."""
    rng = random.Random(base_seed)
    out = []
    for t in range(trials):
        variants = build_variants(slots, rng, pool)
        # Opponent is a plain random legal deck: the combo is being measured
        # against the field, not against one hand-picked foil.
        for _ in range(200):
            opponent = sorted(rng.sample(list(pool), DECK_SIZE))
            if sum(1 for c in opponent if c in toys) >= min_toys:
                break
        out.append({
            "trial": t,
            "seed": base_seed * 7_919 + t,
            "variants": variants,
            "opponent": opponent,
        })
    return out


_RUNNER = None
_OPTS: dict = {}


def _init_worker(policy: str, max_turns: int, max_actions, max_sequences) -> None:
    global _RUNNER
    logging.disable(logging.CRITICAL)
    os.environ.setdefault("GOOGLE_API_KEY", "unused-combo-harness")
    from .runner import SimulationRunner
    from .scripted_player import ScriptedPlayer

    _OPTS.update(max_actions=max_actions, max_sequences=max_sequences)

    runner = SimulationRunner(
        max_turns=max_turns, player1_policy=policy, player2_policy=policy
    )
    # Raise the enumerator ceiling for both seats. Real combo turns run past the
    # 8-action default, and a turn that is never enumerated can never be played.
    original = runner._make_player

    def _make(seat, seed):
        player = original(seat, seed)
        if isinstance(player, ScriptedPlayer):
            player.turn_planner.enum_max_actions = _OPTS["max_actions"]
            player.turn_planner.enum_max_sequences = _OPTS["max_sequences"]
        return player

    runner._make_player = _make
    _RUNNER = runner


def _play_chunk(chunk: list[tuple]) -> list[dict]:
    from .config import DeckConfig

    rows = []
    for trial, seed, variant, deck, opponent, seat in chunk:
        combo_deck = DeckConfig(name=variant, description="combo", cards=list(deck))
        opp_deck = DeckConfig(name="opp", description="combo", cards=list(opponent))
        d1, d2 = (combo_deck, opp_deck) if seat == 1 else (opp_deck, combo_deck)
        try:
            res = _RUNNER.run_game(d1, d2, game_number=seed, seed=seed)
            outcome = res.outcome.value if hasattr(res.outcome, "value") else str(res.outcome)
            if outcome == "draw":
                score = 0.5
            else:
                won = (outcome == "player1_win") == (seat == 1)
                score = 1.0 if won else 0.0
            # Longest single turn: the direct test of whether the combo ever
            # fired. A combo deck whose turns stay short was never executed, and
            # its win rate says nothing about the combo.
            per_turn: dict = {}
            for entry in res.action_log:
                key = (entry.get("turn"), entry.get("player"))
                per_turn[key] = per_turn.get(key, 0) + 1
            combo_side = "player1" if seat == 1 else "player2"
            own = [n for (t, p), n in per_turn.items() if p == combo_side]
            rows.append({
                "trial": trial, "variant": variant, "seat": seat, "seed": seed,
                "score": score, "turns": res.turn_count,
                "max_actions_in_turn": max(own) if own else 0,
                "error": res.error_message,
            })
        except Exception as e:
            rows.append({"trial": trial, "variant": variant, "seat": seat,
                         "seed": seed, "score": None, "turns": 0,
                         "max_actions_in_turn": 0, "error": f"{type(e).__name__}: {e}"})
    return rows


def _chunks(items: list, size: int) -> Iterator[list]:
    it = iter(items)
    while batch := list(itertools.islice(it, size)):
        yield batch


def _wilson(wins: float, n: int) -> tuple[float, float]:
    """Wilson interval — behaves near 0 and 1, unlike the normal approximation."""
    if n == 0:
        return (0.0, 0.0)
    z, p = 1.96, wins / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (centre - half, centre + half)


def run_combo(spec: str, trials: int, policy: str, workers: int, base_seed: int,
              max_turns: int, max_actions: Optional[int],
              max_sequences: Optional[int], min_toys: int,
              out_path: Optional[str]) -> dict:
    from .sweep import _card_pool

    pool, toys = _card_pool()
    slots = parse_combo(spec, pool)
    plan = plan_trials(base_seed, trials, slots, pool, min_toys, toys)

    work = []
    for t in plan:
        for variant, deck in t["variants"].items():
            for seat in (1, 2):  # both seats: seat advantage is large in this game
                work.append((t["trial"], t["seed"] + seat * 101, variant, deck,
                             t["opponent"], seat))

    print(f"combo: {' + '.join('|'.join(s) for s in slots)}")
    print(f"{trials} trials x {len(plan[0]['variants'])} variants x 2 seats "
          f"= {len(work)} games, policy={policy}, "
          f"max_actions={max_actions or 'default(8)'}")

    rows: list[dict] = []
    chunk = max(1, min(40, len(work) // (workers * 4) or 1))
    with ProcessPoolExecutor(
        max_workers=workers, initializer=_init_worker,
        initargs=(policy, max_turns, max_actions, max_sequences),
    ) as ex:
        for out in ex.map(_play_chunk, _chunks(work, chunk)):
            rows.extend(out)
            print(f"\r  {len(rows)}/{len(work)}", end="", flush=True)
    print()

    report = summarize(rows, slots)
    if out_path:
        with open(out_path, "w") as fh:
            json.dump({"spec": spec, "policy": policy, "trials": trials,
                       "max_actions": max_actions, "rows": rows,
                       "report": report}, fh, indent=2)
        print(f"\nraw results -> {out_path}")
    return report


def summarize(rows: list[dict], slots: list[list[str]]) -> dict:
    by_variant: dict[str, list[dict]] = {}
    for r in rows:
        if r["score"] is not None:
            by_variant.setdefault(r["variant"], []).append(r)

    errors = sum(1 for r in rows if r["error"])
    stats = {}
    for variant, rs in by_variant.items():
        n = len(rs)
        wins = sum(r["score"] for r in rs)
        lo, hi = _wilson(wins, n)
        fired = [r["max_actions_in_turn"] for r in rs]
        stats[variant] = {
            "n": n, "win_rate": wins / n, "lo": lo, "hi": hi,
            "mean_turns": sum(r["turns"] for r in rs) / n,
            "mean_max_actions": sum(fired) / n,
            "p95_max_actions": sorted(fired)[int(0.95 * (n - 1))],
        }

    full = stats.get("full")
    print(f"\n{'variant':<26}{'n':>6}{'win%':>8}{'95% CI':>18}"
          f"{'vs full':>10}{'max acts/turn':>15}")
    print("-" * 84)
    order = ["full"] + sorted(v for v in stats if v.startswith("drop:")) + ["none"]
    for variant in order:
        s = stats.get(variant)
        if not s:
            continue
        delta = ""
        if full and variant != "full":
            d = (s["win_rate"] - full["win_rate"]) * 100
            delta = f"{d:+.1f} pts"
        print(f"{variant:<26}{s['n']:>6}{s['win_rate']*100:>7.1f}%"
              f"  [{s['lo']*100:>5.1f},{s['hi']*100:>5.1f}]{delta:>10}"
              f"{s['mean_max_actions']:>9.1f} (p95 {s['p95_max_actions']})")

    if errors:
        print(f"\n  {errors} game(s) errored")

    if full and full["mean_max_actions"] < 3:
        print("\n  WARNING: the combo deck averages under 3 actions per turn — the"
              "\n  combo almost certainly never fired. Win rates here measure card"
              "\n  stats, not the combo. Try --policy search2 and raise --max-actions.")

    print("\nRead 'vs full' as each piece's contribution IN CONTEXT: how much the"
          "\ndeck loses when that card alone is swapped for a neutral filler."
          "\nCompare against the card's solo value from analyze_sweep.py — the gap"
          "\nbetween the two is the combo effect (superadditivity).")
    return stats


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--combo", required=True,
                   help='comma-separated cards; "A|B" means any one of A or B')
    p.add_argument("--games", type=int, default=2000,
                   help="approximate total games; trials are derived from it")
    p.add_argument("--policy", default="search2",
                   help="greedy is blind to non-breaking combos; default search2")
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--max-turns", type=int, default=20)
    p.add_argument("--max-actions", type=int, default=14,
                   help="enumerator action ceiling (engine default is 8)")
    p.add_argument("--max-sequences", type=int, default=24,
                   help="enumerator sequence ceiling (engine default is 12)")
    p.add_argument("--min-toys", type=int, default=2)
    p.add_argument("--out", default=None, help="write raw per-game JSON here")
    a = p.parse_args(argv)

    from .sweep import _card_pool

    pool, _ = _card_pool()
    n_variants = len(parse_combo(a.combo, pool)) + 2  # full + each drop + none
    trials = max(1, a.games // (n_variants * 2))

    run_combo(a.combo, trials, a.policy, a.workers, a.seed, a.max_turns,
              a.max_actions, a.max_sequences, a.min_toys, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
