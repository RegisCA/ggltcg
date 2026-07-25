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

## Where the other tooling lives

| Task | Use |
|---|---|
| Run simulations, compare models, test a deck | `python -m simulation.cli --help` |
| Verify AI turn quality | `pytest tests/test_ai_enum_scenario.py -v -s` |
| Inspect a production game's AI decisions | `render psql` against `ai_decision_logs` / `game_playback` |
| Browse users, games, playbacks, simulation runs | `/admin.html` |
