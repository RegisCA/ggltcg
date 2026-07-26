#!/usr/bin/env python3
"""Estimate per-card value from a scripted sweep (``simulation.sweep``).

The model is Bradley-Terry with additive card strengths:

    logit P(player 1 wins) = seat + sum_c beta_c * (in_deck1[c] - in_deck2[c])

Each card's ``beta`` is its contribution to the log-odds of winning, holding the
rest of the deck fixed — which is exactly "how much is this card worth?" measured
across thousands of different deck contexts. The antisymmetric design means any
card appearing on both sides cancels, and the intercept absorbs seat advantage on
its own rather than smearing it across the card estimates.

Fitted by Newton-Raphson (IRLS). Rows are sparse (at most 12 nonzero features),
so this stays fast in pure Python and the backend gains no numpy dependency.

    python backend/scripts/analyze_sweep.py --db backend/data/sweep.db
    python backend/scripts/analyze_sweep.py --compare 1 2 3
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "sweep.db"


# --- linear algebra ---------------------------------------------------------

def invert(matrix: list[list[float]]) -> list[list[float]]:
    """Gauss-Jordan inverse with partial pivoting. n is ~41 here."""
    n = len(matrix)
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)]
           for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError(f"singular matrix at column {col}")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        div = aug[col][col]
        aug[col] = [v / div for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor:
                aug[r] = [v - factor * w for v, w in zip(aug[r], aug[col])]
    return [row[n:] for row in aug]


def fit_logistic(rows: list[tuple[list[tuple[int, float]], int]], n_features: int,
                 ridge: float = 1e-6, iters: int = 25) -> tuple[list[float], list[list[float]]]:
    """IRLS fit. ``rows`` is [(sparse [(index, value)], y in {0,1})].

    Returns ``(beta, covariance)``. The tiny ridge only guards against a card
    that never appears in the sample; the structural rank deficiency is handled
    by the caller's reference coding, not here.
    """
    beta = [0.0] * n_features
    for _ in range(iters):
        grad = [0.0] * n_features
        hess = [[0.0] * n_features for _ in range(n_features)]
        for feats, y in rows:
            z = sum(beta[i] * v for i, v in feats)
            p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
            r = y - p
            w = max(p * (1.0 - p), 1e-9)
            for i, vi in feats:
                grad[i] += r * vi
                hrow = hess[i]
                for j, vj in feats:
                    hrow[j] += w * vi * vj
        for i in range(n_features):
            grad[i] -= ridge * beta[i]
            hess[i][i] += ridge
        try:
            cov = invert(hess)
        except ValueError:
            break
        step = [sum(cov[i][j] * grad[j] for j in range(n_features))
                for i in range(n_features)]
        beta = [b + s for b, s in zip(beta, step)]
        if max(abs(s) for s in step) < 1e-8:
            break
    return beta, cov


# --- data -------------------------------------------------------------------

def load_run(conn: sqlite3.Connection, run_id: int):
    meta = conn.execute(
        "SELECT policy1, policy2, games, min_toys, both_seats, notes FROM sweep_runs WHERE id=?",
        (run_id,),
    ).fetchone()
    if meta is None:
        raise SystemExit(f"no run {run_id} in database")
    games = conn.execute(
        "SELECT deck1, deck2, outcome, turns FROM sweep_games"
        " WHERE run_id=? AND error IS NULL AND outcome != 'error'",
        (run_id,),
    ).fetchall()
    return meta, [(json.loads(d1), json.loads(d2), o, t) for d1, d2, o, t in games]


def analyze(run_id: int, meta, games, top: int) -> dict[str, float]:
    policy1, policy2, n_planned, min_toys, both_seats, notes = meta
    cards = sorted({c for d1, d2, _, _ in games for c in (*d1, *d2)})
    index = {c: i for i, c in enumerate(cards)}
    n_cards = len(cards)

    # Every deck holds exactly the same number of cards, so the card features sum
    # to zero on every single row: sum_c (in_deck1[c] - in_deck2[c]) == 0. The 40
    # card coefficients are therefore identified only up to an additive constant,
    # and fitting all of them leaves the Hessian singular along that direction —
    # which is what produced ±9.8 intervals on every card. Standard fix: drop the
    # last card as a reference level (its beta is pinned to 0), fit the rest, then
    # recentre all 40 to sum to zero so each beta reads as "value relative to an
    # average card". Contrast variances are propagated through the same linear map.
    # Two separate index spaces that happen to share a bound — worth naming:
    #   ref_idx  indexes `cards` (which card is pinned to beta = 0)
    #   seat_idx indexes the feature vector
    # The reference is the last card, so dropping its column frees feature slot
    # n_cards - 1, and the seat term reuses it. Hence the equal values.
    reference = cards[-1]
    ref_idx = n_cards - 1
    seat_idx = n_cards - 1
    n_features = n_cards  # (n_cards - 1) card columns + 1 seat column

    decisive, draws = [], 0
    for d1, d2, outcome, _ in games:
        if outcome == "draw":
            draws += 1
            continue
        counts: dict[int, float] = {}
        for c in d1:
            counts[index[c]] = counts.get(index[c], 0.0) + 1.0
        for c in d2:
            counts[index[c]] = counts.get(index[c], 0.0) - 1.0
        feats = [(i, v) for i, v in counts.items() if v != 0.0 and i != ref_idx]
        feats.append((seat_idx, 1.0))
        decisive.append((feats, 1 if outcome == "player1_win" else 0))

    print(f"\n{'='*74}")
    print(f"run {run_id}  policy={policy1} vs {policy2}  {notes or ''}")
    print(f"{'='*74}")
    print(f"games={len(games)}  decisive={len(decisive)}  draws={draws} "
          f"({draws/max(1,len(games))*100:.1f}%)  cards seen={len(cards)}")
    turns = [t for _, _, _, t in games]
    print(f"mean turns={sum(turns)/max(1,len(turns)):.2f}")

    p1_wins = sum(y for _, y in decisive)
    share = p1_wins / max(1, len(decisive))
    ci = 1.96 * math.sqrt(share * (1 - share) / max(1, len(decisive)))
    print(f"player-1 share of decisive games: {share*100:.1f}% ± {ci*100:.1f} pts")

    raw, cov = fit_logistic(decisive, n_features)

    seat = raw[seat_idx]
    seat_se = math.sqrt(max(cov[seat_idx][seat_idx], 0.0))
    print(f"seat coefficient (log-odds of moving first): "
          f"{seat:+.3f} ± {1.96*seat_se:.3f}  "
          f"-> {100/(1+math.exp(-seat)):.1f}% for an even matchup")

    # Recentre to sum-to-zero. For card i the contrast is
    #   c_i = b_i - (1/n) * sum_{j < n-1} b_j        (b_reference == 0)
    # so its variance is v^T Cov v for the matching coefficient vector v.
    fitted = [raw[i] if i < ref_idx else 0.0 for i in range(n_cards)]
    mean_b = sum(fitted) / n_cards
    beta = {c: fitted[index[c]] - mean_b for c in cards}

    stderr: dict[str, float] = {}
    for c in cards:
        i = index[c]
        v = [-1.0 / n_cards] * n_features
        v[seat_idx] = 0.0  # seat is not part of the card contrast
        if i != ref_idx:
            v[i] += 1.0
        stderr[c] = math.sqrt(max(sum(
            v[a] * cov[a][b] * v[b] for a in range(n_features) for b in range(n_features)
        ), 0.0))

    ranked = sorted(cards, key=lambda c: beta[c], reverse=True)
    print(f"\nCard values are relative to an average card (they sum to zero).")
    print(f"Reference level: {reference}\n")
    print(f"{'card':<20}{'beta':>8}{'95% CI':>18}{'win% vs avg':>13}")
    print("-" * 62)

    def show(names):
        for c in names:
            lo, hi = beta[c] - 1.96 * stderr[c], beta[c] + 1.96 * stderr[c]
            wr = 100 / (1 + math.exp(-beta[c]))
            flag = "" if lo * hi > 0 else "   (ns)"
            print(f"{c:<20}{beta[c]:>+8.3f}  [{lo:>+7.3f},{hi:>+7.3f}]{wr:>12.1f}%{flag}")

    show(ranked[:top])
    print(f"{'...':<20}")
    show(ranked[-top:])
    print("\n(ns) = 95% interval spans zero; card value not distinguishable from average")
    return beta


def spearman(a: dict[str, float], b: dict[str, float]) -> float:
    shared = sorted(set(a) & set(b))
    if len(shared) < 3:
        return float("nan")

    def ranks(values: dict[str, float]) -> dict[str, float]:
        order = sorted(shared, key=lambda c: values[c])
        return {c: i + 1 for i, c in enumerate(order)}

    ra, rb = ranks(a), ranks(b)
    n = len(shared)
    d2 = sum((ra[c] - rb[c]) ** 2 for c in shared)
    return 1 - 6 * d2 / (n * (n * n - 1))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--run", type=int, default=None, help="run id (default: latest)")
    p.add_argument("--compare", type=int, nargs="+", default=None,
                   help="run ids to fit and cross-correlate")
    p.add_argument("--top", type=int, default=10)
    a = p.parse_args(argv)

    conn = sqlite3.connect(a.db)
    run_ids = a.compare or [a.run or conn.execute(
        "SELECT MAX(id) FROM sweep_runs").fetchone()[0]]

    fits, labels = {}, {}
    for rid in run_ids:
        meta, games = load_run(conn, rid)
        if not games:
            print(f"run {rid}: no completed games, skipping")
            continue
        fits[rid] = analyze(rid, meta, games, a.top)
        labels[rid] = meta[0]

    if len(fits) > 1:
        print(f"\n{'='*74}\ncard-ranking agreement between policies (Spearman rho)\n{'='*74}")
        ids = sorted(fits)
        for i, x in enumerate(ids):
            for y in ids[i + 1:]:
                rho = spearman(fits[x], fits[y])
                print(f"  run {x} ({labels[x]}) vs run {y} ({labels[y]}): rho = {rho:+.3f}")
        print("\nCards ranked very differently across policies are the ones whose value"
              "\ndepends on how well they are piloted — the candidates for LLM validation.")
        ids = sorted(fits)
        base, other = fits[ids[0]], fits[ids[-1]]
        shared = sorted(set(base) & set(other))
        rb = {c: i for i, c in enumerate(sorted(shared, key=lambda c: base[c]))}
        ro = {c: i for i, c in enumerate(sorted(shared, key=lambda c: other[c]))}
        movers = sorted(shared, key=lambda c: -abs(rb[c] - ro[c]))[:8]
        print(f"\n{'card':<20}{'rank ' + labels[ids[0]]:>18}{'rank ' + labels[ids[-1]]:>18}{'shift':>8}")
        print("-" * 66)
        for c in movers:
            print(f"{c:<20}{len(shared)-rb[c]:>18}{len(shared)-ro[c]:>18}{rb[c]-ro[c]:>+8}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
