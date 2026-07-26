#!/usr/bin/env python3
"""Report a fixed-deck round-robin (``simulation.sweep --decks all``).

``analyze_sweep.py`` answers "which cards are good?" by regressing outcomes onto
card presence. Once candidate decks exist the question changes to "which deck is
good, and against whom?", which wants a matchup matrix instead.

Reports three cuts:

- overall win rate per deck, pooled over both seats
- the full matchup matrix (row deck as player 1, i.e. moving first)
- seat preference per deck: win rate moving first vs moving second, over an
  identical opponent set, so matchup effects cancel exactly

    python backend/scripts/deck_matrix.py --run 10
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "sweep.db"


def wilson(wins: float, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    z, p = 1.96, wins / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (centre - half, centre + half)


def load(conn: sqlite3.Connection, run_id: int, decks: dict[str, tuple]):
    rows = conn.execute(
        "SELECT deck1, deck2, outcome FROM sweep_games"
        " WHERE run_id=? AND error IS NULL AND outcome != 'error'",
        (run_id,),
    ).fetchall()
    if not rows:
        raise SystemExit(f"run {run_id} has no completed games")

    by_cards = {cards: name for name, cards in decks.items()}
    out = []
    unknown = 0
    for d1, d2, outcome in rows:
        a = by_cards.get(tuple(sorted(json.loads(d1))))
        b = by_cards.get(tuple(sorted(json.loads(d2))))
        if a is None or b is None:
            unknown += 1
            continue
        out.append((a, b, outcome))
    if unknown:
        print(f"note: {unknown} game(s) used decks not in simulation_decks.csv, skipped")
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--run", type=int, default=None, help="run id (default: latest)")
    a = p.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from simulation.deck_loader import load_simulation_decks_dict

    decks = {n: tuple(sorted(d.cards)) for n, d in load_simulation_decks_dict().items()}

    if not a.db.exists():
        raise SystemExit(f"no sweep database at {a.db}")
    conn = sqlite3.connect(a.db)
    run_id = a.run or conn.execute("SELECT MAX(id) FROM sweep_runs").fetchone()[0]
    games = load(conn, run_id, decks)

    # score[deck] = (wins, games); draws count as half for both sides.
    overall: dict[str, list[float]] = defaultdict(lambda: [0.0, 0])
    first: dict[str, list[float]] = defaultdict(lambda: [0.0, 0])
    second: dict[str, list[float]] = defaultdict(lambda: [0.0, 0])
    cell: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0])

    for a_name, b_name, outcome in games:
        sa = 0.5 if outcome == "draw" else (1.0 if outcome == "player1_win" else 0.0)
        for name, score, bucket in ((a_name, sa, first), (b_name, 1 - sa, second)):
            overall[name][0] += score
            overall[name][1] += 1
            bucket[name][0] += score
            bucket[name][1] += 1
        cell[(a_name, b_name)][0] += sa
        cell[(a_name, b_name)][1] += 1

    order = sorted(overall, key=lambda d: -overall[d][0] / max(1, overall[d][1]))

    print(f"\nrun {run_id} — {len(games)} games, {len(order)} decks\n")
    print(f"{'deck':<16}{'games':>7}{'win%':>8}{'95% CI':>16}")
    print("-" * 47)
    for name in order:
        w, n = overall[name]
        lo, hi = wilson(w, n)
        print(f"{name:<16}{n:>7}{w/n*100:>7.1f}%  [{lo*100:>5.1f},{hi*100:>5.1f}]")

    print("\nmatchup matrix — row deck's win% as PLAYER 1 (moving first) vs column")
    print(f"{'':<16}" + "".join(f"{n[:7]:>9}" for n in order))
    for r in order:
        line = f"{r:<16}"
        for c in order:
            w, n = cell[(r, c)]
            line += f"{w/n*100:>8.0f}%" if n else f"{'-':>9}"
        print(line)

    print("\nseat preference — same opponent set in both halves, so matchups cancel")
    print(f"{'deck':<16}{'as P1':>9}{'as P2':>9}{'delta':>9}")
    print("-" * 43)
    for name in order:
        fw, fn = first[name]
        sw, sn = second[name]
        f_pct, s_pct = fw / fn * 100, sw / sn * 100
        print(f"{name:<16}{f_pct:>8.1f}%{s_pct:>8.1f}%{f_pct - s_pct:>+8.1f}p")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
