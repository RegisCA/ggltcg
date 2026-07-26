"""Card-value estimation (``backend/scripts/analyze_sweep.py``).

Every card-level conclusion downstream rests on this fit, so it is checked
against synthetic data with known coefficients rather than only on real runs
where the truth is unknown.

The gate that matters most is **identification**. Every deck holds exactly the
same number of cards, so the card features sum to zero on every row and the
coefficients are identified only up to an additive constant. Fitting all of them
leaves the Hessian singular along that direction: the point estimates still look
entirely reasonable while the standard errors blow up to +/-9.8, which is how the
bug survived a first reading. Reference coding plus sum-to-zero recentring fixes
it, and `test_standard_errors_are_not_degenerate` is what stops it regressing.
"""

import contextlib
import io
import math
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analyze_sweep import analyze, fit_logistic, invert, spearman  # noqa: E402

DECK_SIZE = 6
POOL = [f"C{i:02d}" for i in range(12)]
# Known truth, deliberately centred so the recovered values are directly comparable.
TRUE = {c: v for c, v in zip(POOL, [1.2, 0.9, 0.6, 0.4, 0.2, 0.05,
                                    -0.05, -0.2, -0.4, -0.6, -0.9, -1.25])}
TRUE_SEAT = 0.25


def _simulate(n_games: int, seed: int = 7):
    """Generate games straight from the model the fit assumes."""
    rng = random.Random(seed)
    games = []
    for _ in range(n_games):
        d1 = rng.sample(POOL, DECK_SIZE)
        d2 = rng.sample(POOL, DECK_SIZE)
        z = TRUE_SEAT + sum(TRUE[c] for c in d1) - sum(TRUE[c] for c in d2)
        p = 1 / (1 + math.exp(-z))
        outcome = "player1_win" if rng.random() < p else "player2_win"
        games.append((sorted(d1), sorted(d2), outcome, 6))
    return games


META = ("greedy", "greedy", 0, 2, 1, "synthetic")


@pytest.fixture(scope="module")
def fitted():
    games = _simulate(20000)
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        beta = analyze(1, META, games, top=3)
    return beta, buf.getvalue()


def test_recovers_known_card_values(fitted):
    beta, _ = fitted
    for card, truth in TRUE.items():
        assert abs(beta[card] - truth) < 0.15, (
            f"{card}: recovered {beta[card]:+.3f}, expected {truth:+.3f}"
        )


def test_recovers_the_ranking_exactly(fitted):
    beta, _ = fitted
    assert spearman(beta, TRUE) > 0.99


def test_recovers_the_seat_coefficient(fitted):
    _, out = fitted
    line = next(ln for ln in out.splitlines() if "seat coefficient" in ln)
    value = float(line.split(":")[1].strip().split()[0])
    assert abs(value - TRUE_SEAT) < 0.1, line


def test_values_are_centred_on_zero(fitted):
    """Sum-to-zero is what makes a beta read as 'relative to an average card'."""
    beta, _ = fitted
    assert abs(sum(beta.values())) < 1e-6


def test_standard_errors_are_not_degenerate(fitted):
    """Regression guard for the identification trap.

    Fitting all N card columns leaves the design rank-deficient by one, and the
    symptom is enormous intervals on every card while the point estimates stay
    plausible. Real intervals at this sample size are ~+/-0.1; the broken fit
    produced ~+/-9.8. Anything past 1.0 means the constraint was lost again.
    """
    _, out = fitted
    widths = []
    for line in out.splitlines():
        if "[" in line and "," in line and "%" in line:
            lo, hi = line.split("[")[1].split("]")[0].split(",")
            widths.append(float(hi) - float(lo))
    assert widths, f"no interval rows parsed from:\n{out}"
    assert max(widths) < 1.0, f"degenerate interval width {max(widths):.2f}"


def test_no_card_is_printed_twice(fitted):
    """--top can exceed half the pool; head and tail must not overlap."""
    _, out = fitted
    names = [ln.split()[0] for ln in out.splitlines()
             if ln[:1] == "C" and "[" in ln]
    assert len(names) == len(set(names)), names


def test_fit_survives_a_singular_hessian():
    """A singular first iteration must not raise UnboundLocalError."""
    rows = [([(0, 1.0)], 1), ([(0, 1.0)], 0)]
    beta, cov = fit_logistic(rows, n_features=2, ridge=0.0)
    assert len(beta) == 2 and len(cov) == 2


def test_invert_roundtrips():
    m = [[4.0, 1.0, 0.0], [1.0, 3.0, 1.0], [0.0, 1.0, 2.0]]
    inv = invert(m)
    for i in range(3):
        for j in range(3):
            got = sum(m[i][k] * inv[k][j] for k in range(3))
            assert abs(got - (1.0 if i == j else 0.0)) < 1e-9


def test_invert_rejects_a_singular_matrix():
    with pytest.raises(ValueError, match="singular"):
        invert([[1.0, 2.0], [2.0, 4.0]])
