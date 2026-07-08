# Simulation System Documentation

## Overview

The Simulation System enables automated AI vs AI game testing. Its primary
use today is **card-balance benchmarking**: running many games with a fixed
model to surface out-of-balance cards and decks. It was implemented as part
of GitHub Issue #243.

**Key Features:**

- Parallel game execution (10 workers by default) for faster completion
- N² matchup matrix (all deck permutations)
- Charge tracking for both players per turn
- Action logging with human-readable descriptions
- **Rate/budget throttling** — an optional requests-per-minute cap and a
  persisted daily request budget so long benchmarking campaigns stay within
  Gemini quotas
- **Resumable, multi-day runs** — when the daily budget is exhausted a run
  pauses cleanly and resumes (next day, or on demand) without losing
  completed games; runs can also be paused/resumed manually
- Command-line interface (CLI) for easy local testing and long-running batches
- Web-based Admin UI for browser-based simulations

**Quick Start:**

```bash
cd backend/src
python -m simulation.cli baseline --iterations 10

# Throttled, multi-day-safe campaign (stays within quotas, auto-resumes daily):
python -m simulation.cli baseline --iterations 50 --rpm 60 --daily-budget 2000
```

For comprehensive CLI documentation, see [backend/src/simulation/README.md](../../backend/src/simulation/README.md).

## Architecture

### Components

```bash
backend/src/simulation/
├── __init__.py
├── __main__.py        # CLI entry point (python -m simulation.cli)
├── cli.py             # Command-line interface with Click
├── config.py          # Data classes (SimulationConfig, GameResult, DeckConfig)
├── deck_loader.py     # Loads deck configurations from CSV
├── orchestrator.py    # Manages batch runs, parallel execution, resume/pause, DB persistence
├── runner.py          # Executes games; Charge tracking & action logging
├── reporter.py        # Generates markdown reports (win rates, matchup matrix, charge analysis)
└── README.md          # Comprehensive CLI documentation
```

The rate/budget limiter lives with the Gemini provider it throttles, at
`backend/src/game_engine/ai/rate_limiter.py` (`RateBudgetLimiter`,
`NoopLimiter`, `BudgetExhaustedError`), not under `simulation/`.

### Parallel Execution

Games run in parallel using a ThreadPoolExecutor (default: 10 workers).
This significantly speeds up large simulation runs:

- Sequential: ~20 seconds/game → 160 games = ~53 minutes
- Parallel (10x): ~20 seconds/game → 160 games = ~5-6 minutes

Each parallel worker:

- Creates its own SimulationRunner instance
- Makes independent Gemini API calls
- Uses a separate database session for persistence
- Progress updates are thread-safe via locking
- Shares one `RateBudgetLimiter` across all workers, so the RPM cap and daily
  budget are enforced globally for the run (the limiter's `acquire()` is
  thread-safe)

### API Routes

Located in `backend/src/api/routes_simulation.py`:

- `GET  /admin/simulation/decks` — List available simulation decks
- `GET  /admin/simulation/models` — List suggested model names
- `POST /admin/simulation/start` — Start a new simulation run
- `GET  /admin/simulation/runs` — List all simulation runs
- `GET  /admin/simulation/runs/{id}` — Get run status/progress
  (includes a `budget` object: `used_today`, `daily_budget`, `rpm`, `resets_at`)
- `GET  /admin/simulation/runs/{id}/results` —
  Get results & matchup stats
- `GET  /admin/simulation/runs/{id}/games/{num}` —
  Get individual game details (Charge & action log)
- `GET  /admin/simulation/runs/{id}/report` — Get the markdown report
- `POST /admin/simulation/runs/{id}/cancel` — Cancel a run
- `POST /admin/simulation/runs/{id}/pause` — Pause a running run
- `POST /admin/simulation/runs/{id}/resume` — Resume a
  paused/budget-exhausted/failed run

> **Server-hosted runs never sleep across days.** On budget exhaustion a
> server run parks in `budget_exhausted` and waits for a `resume` call (via
> the API, CLI, or Admin UI). The multi-day sleep-and-auto-resume behavior is
> CLI-only (see [Multi-Day Batch Runs](#multi-day-batch-runs)) — a Render web
> worker is not held for days.

### Database Models

Located in `backend/src/api/db_models.py`:

- `SimulationRunModel` - Tracks run metadata, status, config
  (statuses: `pending`, `running`, `completed`, `failed`, `cancelled`,
  `paused`, `budget_exhausted`)
- `SimulationGameModel` - Individual game results with Charge tracking and action
  log
- `ApiUsageModel` (`api_usage_daily`) - Per-provider, per-day request counter
  backing the daily budget; persisted so restarts don't reset the count

## Configuration

### Simulation Decks

Decks are defined in `backend/data/simulation_decks.csv`:

```csv
deck_name,description,card1,card2,card3,card4,card5,card6
Aggro_Rush,Fast aggressive deck with charge generation,Dream,Knight,Raggy,Umbruh,Rush,Surge
Control_Ka,Board control with Ka strength boost,Ka,Wizard,Beary,Copy,Clean,Wake
```

**To add a new deck:**

1. Add a row to `simulation_decks.csv`
2. Use exact card names from `backend/data/cards.csv`
3. Deck will appear automatically in the Admin UI

### LLM Models

Suggested model names (shown as presets in the Admin UI and returned by
`GET /admin/simulation/models`) are defined in
`backend/src/simulation/config.py`:

```python
SUPPORTED_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
]
```

> Only Gemini models are actually wired up — `build_provider` is Gemini-only,
> so the non-Gemini entries are placeholders, not functional backends.

**Default model.** When no model is specified, simulations resolve the same
way live games do — `GEMINI_MODEL` env var, then the provider default
(`gemini-flash-lite-latest`) — via `config.default_simulation_model()`. This
keeps benchmarking honest: games run against the model players actually face,
not a hardcoded snapshot. Explicit `--model` / API `player*_model` values
still override, so cross-model comparison remains possible.

## Usage

### Starting a Simulation

#### Via CLI (Recommended for Local Testing)

The CLI provides a streamlined interface for running simulations locally:

```bash
cd backend/src

# List available decks
python -m simulation.cli list-decks

# Run a baseline campaign (default model, mirror across the baseline decks)
python -m simulation.cli baseline --iterations 10

# Compare two models head-to-head
python -m simulation.cli compare --model1 gemini-flash-lite-latest --model2 gemini-2.0-flash

# Quick test between two decks
python -m simulation.cli quick Aggro_Rush Control_Ka

# Throttled run + resume/status for long campaigns
python -m simulation.cli baseline --iterations 50 --rpm 60 --daily-budget 2000
python -m simulation.cli status 42
python -m simulation.cli resume 42
```

Throttle flags (`--rpm`, `--daily-budget`, `--wait/--no-wait`) are available on
`baseline`, `compare`, `test-deck`, and `quick`. `resume` and `status` operate
on an existing run id. For all CLI commands and options, see
[backend/src/simulation/README.md](../../backend/src/simulation/README.md).

#### Via API

```bash
curl -X POST http://localhost:8000/admin/simulation/start \
  -H "Content-Type: application/json" \
  -d '{
    "deck_names": ["Aggro_Rush", "Control_Ka"],
    "iterations_per_matchup": 3,
    "parallel_games": 10,
    "rpm": 60,
    "daily_request_budget": 2000
  }'
```

`player1_model` / `player2_model` are optional and default to the live-game
model resolution (see [LLM Models](#llm-models)). `rpm`, `daily_request_budget`,
and `parallel_games` are optional throttle controls.

Via Admin UI:

1. Navigate to Admin Data Viewer → Simulation tab
2. Select decks (1 for mirror match, 2+ for cross-deck testing)
3. (Optional) Set RPM, daily request budget, and parallel games — an inline
   estimate shows approximate total requests and days
4. Set iterations per matchup
5. Click "Start Simulation"; pause/resume running or parked runs from the run
   list, with a progress bar that persists across pauses

### Understanding Results

**Matchup Generation:**

- N decks generate N² matchups (all permutations)
- This treats A vs B and B vs A as different matchups since Player 1 goes first
- Single deck: 1 matchup (mirror)
- Two decks: 4 matchups (A vs A, A vs B, B vs A, B vs B)
- Three decks: 9 matchups

**Game Limit:**

- Maximum 500 total games per simulation run
- If iterations × matchups exceeds 500, iterations are automatically reduced

**Results Matrix:**

- Results are displayed in a heatmap matrix format
- Rows = Player 1 deck, Columns = Player 2 deck
- Cell shows P1 Win% with color coding (green = P1 favored, red = P2 favored)
- Diagonal cells are mirror matchups

**Charge Tracking:**
Each turn records both players' Charge state (the `TurnCharge` dataclass in
`backend/src/simulation/config.py`):

- `turn`: Turn number (odd = P1's turn, even = P2's turn)
- For both `p1` and `p2`:
  - `charge_start`: Charge at start of that player's action window
  - `charge_gained`: Charge gained (from abilities like Umbruh's on-tussle effect)
  - `charge_spent`: Charge spent on actions
  - `charge_end`: Charge at end of turn

Note: Players can gain Charge during their opponent's turn. For example, Umbruh
can generate Charge when it is tussled.

**Action Log:**
Each action records:

- `turn`: Turn number
- `player`: Player identifier
- `action`: Action type (play_card, tussle, activate_ability,
  direct_attack, end_turn)
- `card`: Card name (if applicable)
- `target`: Target card (if applicable)
- `description`: Human-readable action description
  (e.g., "Spent 2 Charge for Knight to tussle Umbruh")
- `reasoning`: AI's reasoning for the decision

## Testing Protocol

### Controlled Mirror Match Test

To test first-player advantage with proper controls:

1. Select **single deck** (e.g., Aggro_Rush only)
2. Set **same model** for both players
3. Run 10+ iterations for statistical significance
4. Analyze P1 Win % - 50% indicates balanced, deviation indicates advantage

### Cross-Deck Matchup Test

To compare deck strength:

1. Select multiple decks
2. Use same model for both players
3. Analyze matchup results to understand deck dynamics

### Model Comparison Test

To compare LLM performance:

1. Select single deck (mirror match)
2. Set different models for P1 and P2
3. **Important**: Run both configurations (swap models) to control for
   first-player effects
4. Compare aggregate results

## Multi-Day Batch Runs

For card-balance benchmarking you often want hundreds or thousands of games
spread over days without tripping Gemini rate limits or burning the daily
quota. The throttle + resume machinery makes this a single long-lived command.

**Throttle controls (all optional):**

- `--rpm N` — token-bucket cap of N requests/minute, shared across all workers.
- `--daily-budget N` — stop after N Gemini requests in a calendar day
  (Pacific time, matching Gemini's quota reset). The count is persisted in
  `api_usage_daily`, so it survives restarts and is shared across processes.
- `--wait` (default) / `--no-wait` — behavior when the daily budget is hit.

**Sizing tip.** A game averages ~15–25 Gemini requests (~1.3 calls per
player-turn). At Gemini Tier 1 (4K RPM / 150K RPD), a daily budget of ~2000
requests (~1.3% of RPD) yields roughly 80–130 games/day while leaving live
traffic untouched — comfortable for a weeks-long campaign.

**Long-lived process (recommended):**

```bash
# Runs until the whole campaign finishes, sleeping until the next daily
# window each time the budget is exhausted. `caffeinate` keeps the Mac awake.
caffeinate -is python -m simulation.cli baseline \
  --iterations 100 --rpm 60 --daily-budget 2000
```

With `--wait`, when the budget is exhausted the run parks in
`budget_exhausted`, prints the reset time, sleeps until then (+ a 2-minute
slack), and resumes automatically — repeating until all games are done.

**Scheduler-driven (cron/launchd):**

```bash
# --no-wait exits 75 (EX_TEMPFAIL) while more games remain, so a wrapper can
# re-invoke `resume <run_id>` on the next scheduled tick.
python -m simulation.cli baseline --iterations 100 --daily-budget 2000 --no-wait
python -m simulation.cli resume <run_id> --no-wait
```

See [backend/src/simulation/README.md](../../backend/src/simulation/README.md)
for a full launchd/cron example.

**How resume stays correct:**

- Completed games are persisted per game as they finish. On resume the
  orchestrator skips exactly the persisted `game_number`s (not a
  count comparison — which would break under out-of-order parallel
  completion) and runs only the remainder.
- Aggregate stats (win rates, matchup matrix) are rehydrated from the
  persisted game rows before continuing, so the final report reflects the
  whole campaign, not just the last session.
- `BudgetExhaustedError` is never swallowed mid-game and never recorded as a
  draw — an exhausted run pauses cleanly with completed games intact.

> **"Pause" means "stop starting new games."** In-flight games finish. If
> `parallel_games` ≥ the number of games still queued, a pause may let the
> run complete before it can park. This is irrelevant for real campaigns
> (hundreds of games queued) but can surprise you in tiny tests.

## Troubleshooting

### Simulation Stalls

If games don't complete:

1. Check server logs for API errors (429 rate limits, timeouts)
2. Verify the model is working in regular game mode first
3. Check the `error_message` field in game results

### Rate Limiting

Gemini API has rate limits. To stay within them:

- **Proactive (preferred):** set `--rpm` / `--daily-budget` (or the equivalent
  API fields) — see [Multi-Day Batch Runs](#multi-day-batch-runs). This paces
  requests and pauses cleanly instead of hammering the API.
- **Reactive:** on a 429/`ResourceExhausted`, the provider retries with
  exponential backoff and falls back to `GEMINI_FALLBACK_MODEL`
  (`gemini-2.5-flash-lite` by default).
- Reducing `iterations_per_matchup` or `parallel_games` also lowers pressure.

### Model Issues

If a specific model isn't working:

1. Test in regular AI game mode first (easier to debug)
2. Check `backend/.env` for `GOOGLE_API_KEY`
3. Verify model name matches Gemini API exactly (and that it is a Gemini
   model — non-Gemini `SUPPORTED_MODELS` entries are not wired up)

## Frontend

The admin UI lives under `frontend/src/components/admin/` (an `AdminApp` shell
plus one component per tab in `tabs/`; data fetching in `hooks/`, API calls in
`frontend/src/api/`). The simulation tab is `tabs/SimulationTab.tsx`:

- **Configure and start runs**: deck selection, per-player model, iterations,
  and optional RPM / daily budget / parallel-games controls with an inline
  request-and-days estimate
- **Run list**: past and active runs with status badges (including `paused`
  and `budget_exhausted`); runs started from the CLI appear here too when the
  backend points at the same database
- **Pause/Resume controls**: pause a running run, resume a
  paused/budget-exhausted one; parked runs show budget used/limit and a
  countdown to the reset; the progress bar persists across pauses
- **Results Matrix**: Heatmap showing P1 win rates for all deck matchups
- **Individual Games Table**: List of all games with P1/P2 decks,
  winner, and total Charge spent
- **Game Detail Panel**: Inline below clicked game row, showing:
  - Turn-by-turn Charge tracking for both players
  - Color-coded actions (play-by-play descriptions)
  - Turn highlighting (green for P1 turns, blue for P2 turns)

## Future Enhancements

Potential improvements identified:

- [x] Parallel game execution (✅ implemented with 10 workers default)
- [x] Command-line interface (✅ implemented via simulation.cli)
- [x] Rate/budget throttling and multi-day resumable runs
  (✅ `--rpm` / `--daily-budget`, pause/resume)
- [ ] Aggregate statistics across multiple runs
- [ ] Export results to CSV
- [ ] Model performance metrics (tokens, latency)
