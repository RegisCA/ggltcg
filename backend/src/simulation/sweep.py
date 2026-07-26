"""Random-deck sweep: play many scripted games to measure card value.

Hand-built decks answer "is *this* deck good?". To answer "is *this card* good?"
we instead sample random legal decks from the whole pool, play them against each
other, and later regress outcomes on which cards were present. Every card then
gets a marginal contribution estimate from thousands of different deck contexts,
with no deck-design judgement entering the measurement.

Because games are scripted (no API calls) a run is CPU-bound and parallel across
processes. See ``docs/development/CARD_EVALUATION_PLAN.md`` for the analysis that
consumes this dataset.

    python -m simulation.sweep --games 5000 --policy greedy --workers 6
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import os
import random
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "sweep.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sweep_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT    NOT NULL,
    policy1      TEXT    NOT NULL,
    policy2      TEXT    NOT NULL,
    games        INTEGER NOT NULL,
    deck_size    INTEGER NOT NULL,
    min_toys     INTEGER NOT NULL,
    pool_size    INTEGER NOT NULL,
    both_seats   INTEGER NOT NULL,
    base_seed    INTEGER NOT NULL,
    max_turns    INTEGER NOT NULL,
    notes        TEXT
);
CREATE TABLE IF NOT EXISTS sweep_games (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES sweep_runs(id) ON DELETE CASCADE,
    pair_id     INTEGER NOT NULL,
    seed        INTEGER NOT NULL,
    deck1       TEXT    NOT NULL,
    deck2       TEXT    NOT NULL,
    outcome     TEXT    NOT NULL,
    turns       INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,
    fallbacks   INTEGER NOT NULL DEFAULT 0,
    error       TEXT
);
CREATE INDEX IF NOT EXISTS idx_sweep_games_run ON sweep_games(run_id);
CREATE INDEX IF NOT EXISTS idx_sweep_games_pair ON sweep_games(run_id, pair_id);
"""


def _card_pool() -> tuple[list[str], set[str]]:
    """All card names, plus the subset that are Toys (have combat stats)."""
    from game_engine.data.card_loader import load_cards_dict

    cards = load_cards_dict()
    names = sorted(cards)
    toys = {n for n in names if cards[n].card_type.value == "Toy"}
    return names, toys


def sample_deck(rng: random.Random, pool: Sequence[str], toys: set[str],
                deck_size: int, min_toys: int) -> list[str]:
    """A random deck of distinct cards holding at least ``min_toys`` Toys.

    The Toy floor matters because a deck of pure Actions cannot tussle and barely
    interacts — those games are noise, not signal. It does mildly bias the
    sampling distribution (Action cards are only ever seen alongside enough Toys),
    which the analysis has to acknowledge; keep ``min_toys`` low for that reason.
    """
    for _ in range(200):
        deck = rng.sample(list(pool), deck_size)
        if sum(1 for c in deck if c in toys) >= min_toys:
            return sorted(deck)
    raise RuntimeError(f"could not sample a deck with >= {min_toys} toys")


def plan_games(base_seed: int, games: int, pool: Sequence[str], toys: set[str],
               deck_size: int, min_toys: int, both_seats: bool) -> list[tuple]:
    """Build the full work list up front, in the parent process.

    Sampling here (not in workers) keeps a run fully determined by ``base_seed``,
    so the same command reproduces the same dataset regardless of worker count or
    scheduling order.
    """
    rng = random.Random(base_seed)
    work: list[tuple] = []
    pair_id = 0
    while len(work) < games:
        d1 = sample_deck(rng, pool, toys, deck_size, min_toys)
        d2 = sample_deck(rng, pool, toys, deck_size, min_toys)
        work.append((pair_id, base_seed * 1_000_003 + len(work), d1, d2))
        if both_seats and len(work) < games:
            # Same pair with the seats swapped: differencing the two removes deck
            # quality entirely and leaves the seat effect on its own.
            work.append((pair_id, base_seed * 1_000_003 + len(work), d2, d1))
        pair_id += 1
    return work[:games]


_RUNNER = None


def _init_worker(policy1: str, policy2: str, max_turns: int) -> None:
    global _RUNNER
    logging.disable(logging.CRITICAL)
    os.environ.setdefault("GOOGLE_API_KEY", "unused-scripted-sweep")
    from .runner import SimulationRunner

    _RUNNER = SimulationRunner(
        max_turns=max_turns,
        player1_policy=policy1,
        player2_policy=policy2,
    )


def _play_chunk(chunk: list[tuple]) -> list[tuple]:
    from .config import DeckConfig

    out = []
    for pair_id, seed, d1, d2 in chunk:
        deck1 = DeckConfig(name=f"S{seed}a", description="sweep", cards=list(d1))
        deck2 = DeckConfig(name=f"S{seed}b", description="sweep", cards=list(d2))
        try:
            res = _RUNNER.run_game(deck1, deck2, game_number=seed, seed=seed)
            fallbacks = (
                getattr(_RUNNER._player1_ai, "execution_fallbacks", 0)
                + getattr(_RUNNER._player2_ai, "execution_fallbacks", 0)
            )
            outcome = res.outcome.value if hasattr(res.outcome, "value") else str(res.outcome)
            out.append((pair_id, seed, json.dumps(d1), json.dumps(d2), outcome,
                        res.turn_count, res.duration_ms, fallbacks, res.error_message))
        except Exception as e:  # a single bad game must not kill the sweep
            out.append((pair_id, seed, json.dumps(d1), json.dumps(d2), "error",
                        0, 0, 0, f"{type(e).__name__}: {e}"))
    return out


def _chunks(items: list, size: int) -> Iterator[list]:
    it = iter(items)
    while batch := list(itertools.islice(it, size)):
        yield batch


def run_sweep(games: int, policy1: str, policy2: str, workers: int, db_path: Path,
              base_seed: int, deck_size: int, min_toys: int, both_seats: bool,
              max_turns: int, notes: str | None) -> int:
    pool, toys = _card_pool()
    work = plan_games(base_seed, games, pool, toys, deck_size, min_toys, both_seats)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    cur = conn.execute(
        "INSERT INTO sweep_runs (created_at, policy1, policy2, games, deck_size,"
        " min_toys, pool_size, both_seats, base_seed, max_turns, notes)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(), policy1, policy2, len(work), deck_size,
         min_toys, len(pool), int(both_seats), base_seed, max_turns, notes),
    )
    run_id = cur.lastrowid
    conn.commit()

    print(f"run {run_id}: {len(work)} games, {policy1} vs {policy2}, "
          f"{workers} workers, pool={len(pool)} ({len(toys)} toys) -> {db_path}")

    chunk_size = max(1, min(50, len(work) // (workers * 4) or 1))
    started = time.time()
    done = 0
    with ProcessPoolExecutor(
        max_workers=workers, initializer=_init_worker,
        initargs=(policy1, policy2, max_turns),
    ) as pool_exec:
        futures = [pool_exec.submit(_play_chunk, c) for c in _chunks(work, chunk_size)]
        for fut in as_completed(futures):
            rows = fut.result()
            conn.executemany(
                "INSERT INTO sweep_games (run_id, pair_id, seed, deck1, deck2, outcome,"
                " turns, duration_ms, fallbacks, error) VALUES (?,?,?,?,?,?,?,?,?,?)",
                [(run_id, *r) for r in rows],
            )
            conn.commit()
            done += len(rows)
            elapsed = time.time() - started
            rate = done / elapsed if elapsed else 0
            eta = (len(work) - done) / rate if rate else 0
            print(f"\r  {done}/{len(work)}  {rate:5.1f} games/s  eta {eta/60:5.1f} min",
                  end="", flush=True)

    elapsed = time.time() - started
    print(f"\n  done in {elapsed/60:.1f} min ({done/elapsed:.1f} games/s)")

    errs = conn.execute(
        "SELECT COUNT(*) FROM sweep_games WHERE run_id=? AND (error IS NOT NULL OR outcome='error')",
        (run_id,),
    ).fetchone()[0]
    fbs = conn.execute(
        "SELECT COALESCE(SUM(fallbacks),0) FROM sweep_games WHERE run_id=?", (run_id,)
    ).fetchone()[0]
    dist = conn.execute(
        "SELECT outcome, COUNT(*) FROM sweep_games WHERE run_id=? GROUP BY outcome", (run_id,)
    ).fetchall()
    print(f"  outcomes: {dict(dist)}   errors: {errs}   llm-fallbacks: {fbs}")
    conn.close()
    return run_id


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--games", type=int, default=2000)
    p.add_argument("--policy", default="greedy", help="policy for both seats")
    p.add_argument("--policy2", default=None, help="override policy for player 2")
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--deck-size", type=int, default=6)
    p.add_argument("--min-toys", type=int, default=2)
    p.add_argument("--no-both-seats", action="store_true")
    p.add_argument("--max-turns", type=int, default=20)
    p.add_argument("--notes", default=None)
    a = p.parse_args(argv)

    run_sweep(
        games=a.games, policy1=a.policy, policy2=a.policy2 or a.policy,
        workers=a.workers, db_path=a.db, base_seed=a.seed, deck_size=a.deck_size,
        min_toys=a.min_toys, both_seats=not a.no_both_seats, max_turns=a.max_turns,
        notes=a.notes,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
