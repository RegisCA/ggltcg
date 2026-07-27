#!/usr/bin/env python3
"""Derive candidate decks from measured card values, reproducibly.

Regenerates ``backend/data/simulation_decks.csv`` from a sweep, so the deck set is
a function of the data rather than of anyone's taste. Each deck answers a stated
question, and two are controls whose job is to fail.

**An additive card model has exactly one best deck.** Ranking alone produced three
identical decks on the first attempt (top-6-by-greedy, top-6-by-search2 and
top-6-by-consensus were the same six cards), which is the same redundancy that
made the old hand-made D1-D8 set uninformative. Diversity has to be imposed as a
constraint: each rival is the best deck sharing at most 2 cards with everything
already chosen.

    python backend/scripts/build_candidate_decks.py --greedy-run 7 --search-run 8
    python backend/scripts/build_candidate_decks.py --write
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import itertools
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

DECK_SIZE = 6
DEFAULT_DB = ROOT / "data" / "sweep.db"
CARDS_CSV = ROOT / "data" / "cards.csv"
DECKS_CSV = ROOT / "data" / "simulation_decks.csv"


def load_values(db: Path, greedy_run: int, search_run: int):
    from analyze_sweep import analyze, load_run

    conn = sqlite3.connect(db)
    out = {}
    for rid in (greedy_run, search_run):
        meta, games = load_run(conn, rid)
        with contextlib.redirect_stdout(io.StringIO()):
            out[rid] = analyze(rid, meta, games, 1)
    conn.close()
    return out[greedy_run], out[search_run]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--greedy-run", type=int, default=7)
    p.add_argument("--search-run", type=int, default=8)
    p.add_argument("--write", action="store_true",
                   help=f"overwrite {DECKS_CSV.name} (otherwise just prints)")
    a = p.parse_args(argv)

    greedy, search = load_values(a.db, a.greedy_run, a.search_run)

    cards = {r["name"]: r for r in csv.DictReader(open(CARDS_CSV))}
    pool = sorted(cards)
    cost = {n: int(cards[n]["cost"]) for n in pool}
    is_toy = {n: cards[n]["card_type"] == "Toy" if "card_type" in cards[n]
              else cards[n]["speed"].strip() != "" for n in pool}
    stat = {n: sum(int(cards[n][k] or 0) for k in ("speed", "strength", "stamina"))
            for n in pool}

    rank_g = {c: i for i, c in enumerate(sorted(pool, key=lambda c: -greedy[c]))}
    rank_s = {c: i for i, c in enumerate(sorted(pool, key=lambda c: -search[c]))}
    consensus = {c: (rank_g[c] + rank_s[c]) / 2 for c in pool}

    # Pinned, NOT read from DECKS_CSV. This script overwrites that file, so
    # deriving the baseline from it makes the run non-idempotent: the second run
    # would pick the previous run's Apex as "the old set's best" and the control
    # would quietly become a duplicate of the deck it is meant to be compared
    # against. A historical reference point has to be frozen to stay one.
    LEGACY_BEST = ["Beary", "Dream", "Knight", "Raggy", "Rush", "Umbruh"]  # old D3

    def legal(deck):
        return len(set(deck)) == DECK_SIZE and sum(1 for c in deck if is_toy[c]) >= 2

    def best_subject_to(score, predicate):
        """Exhaustive best 6-card set. C(40,6) = 3.8M is fine for a one-off."""
        best, best_v = None, float("-inf")
        for combo in itertools.combinations(pool, DECK_SIZE):
            if not legal(combo) or not predicate(combo):
                continue
            v = score(combo)
            if v > best_v:
                best, best_v = list(combo), v
        if best is None:
            raise SystemExit("no legal deck satisfies the constraint")
        return best

    def sum_g(d):
        return sum(greedy[c] for c in d)

    def disjoint_from(chosen, limit=2):
        picked = [set(d) for d in chosen]
        return lambda combo: all(len(set(combo) & s) <= limit for s in picked)

    decks: dict[str, tuple[list[str], str]] = {}

    apex = sorted(pool, key=lambda c: -greedy[c])[:DECK_SIZE]
    decks["Apex"] = (apex, "Top 6 by fitted value -- the model's single best guess.")

    rival_a = best_subject_to(sum_g, disjoint_from([apex]))
    decks["Rival_A"] = (rival_a, "Best deck sharing <=2 cards with Apex.")

    rival_b = best_subject_to(sum_g, disjoint_from([apex, rival_a]))
    decks["Rival_B"] = (rival_b, "Best deck sharing <=2 cards with Apex and Rival_A.")

    decks["Curve"] = (
        best_subject_to(sum_g, lambda d: sum(cost[c] for c in d) <= 2),
        "Best value at total cost <=2 -- deploys free, spends everything on tussles.")

    # Ablation measured Hind Leg Kicker as superadditive (+6.5 pts over its solo
    # value) while Jumpscare and That was fun stayed net-negative. Forcing the
    # whole shell asks whether it competes with raw value regardless.
    combo = ["Hind Leg Kicker", "Jumpscare", "That was fun"]
    decks["Combo"] = (
        best_subject_to(sum_g, lambda d: all(c in d for c in combo)),
        "Forced HLK + Jumpscare + That was fun engine, best remaining slots.")

    # Control: does the fitted value beat just adding up the numbers on the card?
    decks["Stat_Max"] = (
        best_subject_to(lambda d: sum(stat[c] for c in d), lambda d: True),
        "CONTROL: highest raw speed+strength+stamina, ignoring fitted value.")

    # Control: if the model predicts anything at all, this must lose badly.
    decks["Control_Worst"] = (
        sorted(pool, key=lambda c: consensus[c])[-DECK_SIZE:],
        "CONTROL: bottom 6 by consensus. Must lose, or the model is wrong.")

    decks["Legacy_Best"] = (
        LEGACY_BEST,
        "Best of the original hand-made D1-D8 set (D3), as a fixed baseline.")

    print(f"{'deck':<15}{'sum-beta':>10}{'cost':>6}{'toys':>6}  cards")
    print("-" * 100)
    for name, (deck, why) in decks.items():
        deck = sorted(deck)
        assert legal(deck), f"{name} is not a legal deck"
        print(f"{name:<15}{sum_g(deck):>+10.2f}{sum(cost[c] for c in deck):>6}"
              f"{sum(1 for c in deck if is_toy[c]):>6}  {', '.join(deck)}")

    near_dupes = {
        (a_, b_): len(set(decks[a_][0]) & set(decks[b_][0]))
        for a_, b_ in itertools.combinations(decks, 2)
        if len(set(decks[a_][0]) & set(decks[b_][0])) >= 4
    }
    print(f"\npairs sharing >=4 of 6 cards: {near_dupes or 'none'}")
    used = {c for d, _ in decks.values() for c in d}
    print(f"pool coverage: {len(used)}/{len(pool)} cards")

    if a.write:
        with open(DECKS_CSV, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["deck_name", "description",
                        *[f"card{i}" for i in range(1, DECK_SIZE + 1)]])
            for name, (deck, why) in decks.items():
                w.writerow([name, why, *sorted(deck)])
        print(f"\nwrote {DECKS_CSV}")
    else:
        print(f"\n(dry run -- pass --write to update {DECKS_CSV.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
