# Backend Scripts

Long-lived operational scripts only. One-off investigation and migration
scripts get deleted once they've served their purpose — they're recoverable
from git history, and leaving them around means broken tooling that reads as
supported.

Local scratch scripts are gitignored: name them `_something.py` (see
`.gitignore`) and they stay out of the repo.

## backfill_posthog_events.py

Backfills historical completed games into PostHog as `game_analyzed` events,
joining `games` with `game_stats` (the two tables that survive the cleanup
task). Idempotent — each event gets a deterministic UUID, so re-running
doesn't duplicate. Players with legacy placeholder IDs are skipped.

```bash
cd backend
python scripts/backfill_posthog_events.py --dry-run
```

## Simulation analysis

These read the local SQLite database written by `python -m simulation.sweep`
(`backend/data/sweep.db` by default). See
[SIMULATION_SYSTEM.md](../../docs/development/SIMULATION_SYSTEM.md).

| Script | Does |
|---|---|
| `analyze_sweep.py` | Fits per-card values from a random-deck sweep; `--compare` checks rank agreement between runs |
| `build_candidate_decks.py` | Derives candidate decks from fitted card values; `--write` updates `data/simulation_decks.csv` |
| `deck_matrix.py` | Win-rate matrix and seat effects for a fixed-deck round-robin |

## Where the other tooling lives

| Task | Use |
|---|---|
| LLM simulations, model comparison | `python -m simulation.cli --help` |
| Scripted (LLM-free) sweeps and combo ablations | `python -m simulation.sweep --help`, `python -m simulation.combo --help` |
| AI planner tests | `pytest tests/test_enumerator.py tests/test_enum_planner_integration.py` |
| Inspect a production game's AI decisions | `render psql` against `ai_decision_logs` / `game_playback` |
| Browse users, games, playbacks, simulation runs | `/admin.html` |
