# GGLTCG Simulation System

The simulation system enables automated AI vs AI gameplay for performance measurement, model comparison, and deck testing.

## Quick Start

### Prerequisites

- Python 3.13+ with virtual environment activated
- Backend dependencies installed (`pip install -r requirements.txt`)
- Database configured and running

### Running Your First Simulation

```bash
# From backend/src directory
cd backend/src

# List available decks
python -m simulation.cli list-decks

# Run a quick baseline test (V4 vs V4, 10 games per matchup)
python -m simulation.cli baseline --iterations 10

# Compare V4 vs V3
python -m simulation.cli compare --v1 4 --v2 3 --iterations 20

# Test a specific matchup
python -m simulation.cli quick Aggro_Rush Control_Ka --iterations 5
```

## CLI Commands

### `baseline`
Run V4 vs V4 with standard decks to establish performance baseline.

```bash
python -m simulation.cli baseline [OPTIONS]

Options:
  -i, --iterations INTEGER   Games per matchup (default: 10)
  -p, --parallel INTEGER     Parallel workers (default: 10)
  -m, --model TEXT          AI model (default: gemini-2.5-flash-lite)
  -d, --decks TEXT          Deck preset: baseline, top2, all (default: baseline)
```

**Example:**
```bash
python -m simulation.cli baseline --iterations 20 --decks top2
```

### `compare`
Compare two AI versions or models head-to-head.

```bash
python -m simulation.cli compare [OPTIONS]

Options:
  --v1 INTEGER              Player 1 AI version (default: 4)
  --v2 INTEGER              Player 2 AI version (default: 3)
  --model1 TEXT             Player 1 model (default: gemini-2.5-flash-lite)
  --model2 TEXT             Player 2 model (default: gemini-2.5-flash-lite)
  -i, --iterations INTEGER  Games per matchup (default: 10)
  -p, --parallel INTEGER    Parallel workers (default: 10)
  -d, --decks TEXT          Deck preset (default: baseline)
```

**Example:**
```bash
# Compare V4 with gemini-2.5-flash-lite vs V3 with gemini-2.0-flash
python -m simulation.cli compare --v1 4 --v2 3 --model1 gemini-2.5-flash-lite --model2 gemini-2.0-flash
```

### `test-deck`
Test custom decks against a set of opponents.

```bash
python -m simulation.cli test-deck DECK_NAMES... [OPTIONS]

Arguments:
  DECK_NAMES...            One or more deck names to test

Options:
  -a, --against TEXT       Decks to test against (default: baseline)
  -i, --iterations INTEGER Games per matchup (default: 10)
  -p, --parallel INTEGER   Parallel workers (default: 10)
  -m, --model TEXT         AI model (default: gemini-2.5-flash-lite)
  -v, --ai-version INTEGER AI version (default: 4)
```

**Example:**
```bash
python -m simulation.cli test-deck User_Slot1 --against baseline --iterations 15
```

### `quick`
Fast test between two specific decks (5 games by default).

```bash
python -m simulation.cli quick DECK1 DECK2 [OPTIONS]

Arguments:
  DECK1                    First deck name
  DECK2                    Second deck name

Options:
  -i, --iterations INTEGER Number of games (default: 5)
  -m, --model TEXT         AI model (default: gemini-2.5-flash-lite)
  -v, --ai-version INTEGER AI version (default: 4)
```

**Example:**
```bash
python -m simulation.cli quick Aggro_Rush Control_Ka --iterations 3
```

### `list-runs`
Show recent simulation runs with status and configuration.

```bash
python -m simulation.cli list-runs [OPTIONS]

Options:
  -l, --limit INTEGER  Number of recent runs to show (default: 10)
```

### `list-decks`
Display all available simulation decks from `simulation_decks.csv`.

```bash
python -m simulation.cli list-decks
```

## Understanding Results

### Output Structure

After each simulation, you get:
1. **Console summary** - Win rates, average turns, CC stats
2. **Markdown report** - Saved to `backend/reports/simulation_run_<id>_<timestamp>.md`
3. **Database records** - Full details queryable via API

### Report Sections

#### Overall Statistics
- Win rates for Player 1 (always goes first) and Player 2
- Draw rate (games hitting turn limit)
- Error count (games with exceptions)
- Average game length in turns and milliseconds

#### Matchup Matrix
Deck-by-deck win rates showing Player 1's performance with each deck against each opponent deck.

**Reading the matrix:**
- Each row is a P1 deck, each column is a P2 deck
- Values show P1 win rate (0-100%)
- Mirror matches (same deck both sides) measure first-player advantage

#### CC (Charge Counter) Analysis
**Important:** Raw CC totals are context-dependent!

- **CC Generated**: Total resources gained (higher in longer games)
- **CC Spent**: Total resources used (also higher in longer games)
- **Winners vs Losers**: Winners often generate MORE CC because they survive longer

**Key insight:** Don't compare raw CC numbers without considering game length. Use CC-per-turn or efficiency metrics instead.

#### First-Player Advantage
Measures whether going first provides a significant edge.

- Expected: 50% win rate (no advantage)
- <45% or >55%: Significant advantage detected
- Important for game balance

#### Notable Games
- Fastest win (fewest turns)
- Longest game (most turns)
- Error games (with exception messages)

## Deck Configuration

### Deck File Format
Decks are defined in `backend/data/simulation_decks.csv`:

```csv
deck_name,description,card1,card2,card3,card4,card5,card6
Aggro_Rush,Fast aggressive deck,Dream,Knight,Raggy,Umbruh,Rush,Surge
Control_Ka,Board control with Ka,Ka,Wizard,Beary,Copy,Clean,Wake
```

**Requirements:**
- Each deck must have exactly 6 cards
- All card names must match entries in `backend/data/cards.csv`
- No duplicate cards within a deck

### Validation
The system automatically validates decks before starting:
- Typos trigger helpful suggestions: `"Arcer" → Did you mean: Archer?`
- Invalid deck sizes fail immediately
- Missing cards show available alternatives

**Example error:**
```
❌ Validation error: Deck validation failed:
Card not found in 'Custom_Deck': 'Arcer'
  Did you mean: Archer?
```

## Architecture

### Core Components

```
simulation/
├── __init__.py
├── __main__.py         # CLI entry point
├── cli.py              # Command-line interface
├── config.py           # Data classes (SimulationConfig, GameResult, TurnCC)
├── deck_loader.py      # Deck CSV parsing and validation
├── orchestrator.py     # Batch simulation management
├── runner.py           # Individual game execution
└── reporter.py         # Report generation
```

### Execution Flow

1. **CLI Command** → Parses arguments, creates `SimulationConfig`
2. **Orchestrator** → Validates decks, creates DB record, generates matchup matrix
3. **Parallel Execution** → ThreadPoolExecutor runs multiple games simultaneously
4. **Runner** → Executes individual game, tracks CC, logs actions
5. **Database Update** → Saves results after each game
6. **Report Generation** → Creates markdown report on completion

### Database Schema

**SimulationRunModel**
- Tracks overall simulation (status, config, progress)
- Foreign key: Many `SimulationGameModel` records

**SimulationGameModel**
- Individual game result
- Stores: outcome, winner, turns, duration, CC tracking, action log

### Parallel Execution
- Default: 10 parallel workers (configurable via `--parallel`)
- Thread-safe using locks for DB writes and progress tracking
- Each game is independent - no shared state

## Logging Control

Simulations suppress verbose DEBUG logs by default to keep output clean.

**Log levels:**
- `WARNING` (default): Errors and warnings only
- `INFO`: Progress updates, major events
- `DEBUG`: Detailed game engine internals

**Change log level:**
```bash
python -m simulation.cli baseline --verbose  # Enables INFO logging
```

**Programmatic control:**
```python
from simulation.runner import SimulationRunner

# Suppress all logs except errors
runner = SimulationRunner(log_level="ERROR")

# Enable verbose debugging
runner = SimulationRunner(log_level="DEBUG")
```

## API Endpoints

The simulation system exposes REST endpoints for programmatic access:

### Start Simulation
```http
POST /admin/simulation/start
Content-Type: application/json

{
  "deck_names": ["Aggro_Rush", "Control_Ka"],
  "player1_model": "gemini-2.5-flash-lite",
  "player2_model": "gemini-2.5-flash-lite",
  "player1_ai_version": 4,
  "player2_ai_version": 4,
  "iterations_per_matchup": 10,
  "max_turns": 40
}
```

### Get Run Status
```http
GET /admin/simulation/runs/{run_id}
```

### Get Full Results
```http
GET /admin/simulation/runs/{run_id}/results
```

### Download Report
```http
GET /admin/simulation/runs/{run_id}/report
```
Returns markdown report as plain text.

### Get Game Details
```http
GET /admin/simulation/runs/{run_id}/games/{game_number}
```
Returns detailed CC tracking and action log for a specific game.

## Admin UI

Access the web-based admin interface at `http://localhost:8000/admin.html`:

1. **Start New Simulation**: Select decks, models, iterations
2. **Monitor Progress**: Live polling shows completion percentage
3. **View Results**: Heatmap matrix, game list, detailed breakdowns
4. **Download Reports**: Click "Download Report" button for markdown file
5. **Inspect Games**: Click any game to see turn-by-turn CC tracking and actions

## Troubleshooting

### Common Issues

**"Module not found: simulation"**
```bash
# Solution: Run from backend/src directory
cd backend/src
python -m simulation.cli baseline
```

**"Deck validation failed: Card not found"**
- Check spelling in `simulation_decks.csv`
- Verify card exists in `backend/data/cards.csv`
- Look for suggestions in error message

**"Database not configured"**
- Ensure database is running
- Check `DATABASE_URL` environment variable
- Run `alembic upgrade head` to apply migrations

**Simulation hangs or times out**
- Check parallel workers count (reduce if system is overloaded)
- Verify API rate limits (Gemini API has quota limits)
- Check logs for specific errors: `tail -f backend/logs/simulation.log`

**High CC values seem wrong**
- Remember: Winners generate more CC because they play longer
- Compare CC-per-turn, not raw totals
- Check matchup length (longer games = more CC generated)

### Debug Mode

Enable detailed logging for troubleshooting:
```bash
# Full debug output
python -m simulation.cli baseline --verbose
```

Or set environment variable:
```bash
export LOG_LEVEL=DEBUG
python -m simulation.cli baseline
```

### Performance Tuning

**Too slow:**
- Increase parallel workers: `--parallel 20`
- Use faster model: `--model gemini-2.5-flash-lite`
- Reduce iterations: `--iterations 5`
- Use `quick` command for rapid testing

**API rate limiting:**
- Reduce parallel workers: `--parallel 5`
- Add delays between requests (requires code modification)
- Upgrade Gemini API quota

**Memory issues:**
- Reduce parallel workers
- Run smaller simulations (fewer decks)
- Clear database of old runs

## Advanced Usage

### Custom Deck Testing Workflow

1. **Create deck in CSV:**
   ```csv
   My_Custom_Deck,Experimental combo,Ka,Knight,Archer,Umbruh,Wake,Surge
   ```

2. **Validate before running:**
   ```bash
   python -m simulation.cli list-decks | grep My_Custom_Deck
   ```

3. **Test against baseline:**
   ```bash
   python -m simulation.cli test-deck My_Custom_Deck --against baseline --iterations 20
   ```

4. **Analyze report:**
   - Check matchup matrix for weaknesses
   - Compare CC efficiency to baseline decks
   - Identify problematic matchups

5. **Iterate:**
   - Adjust deck composition
   - Re-run simulation
   - Compare win rates

### Model Comparison Study

To rigorously compare two Gemini models:

```bash
# 1. Baseline each model against itself
python -m simulation.cli baseline --model gemini-2.0-flash --iterations 30
python -m simulation.cli baseline --model gemini-2.5-flash-lite --iterations 30

# 2. Head-to-head comparison (both player orders)
python -m simulation.cli compare --v1 4 --v2 4 --model1 gemini-2.0-flash --model2 gemini-2.5-flash-lite --iterations 30

# 3. Reverse player order
python -m simulation.cli compare --v1 4 --v2 4 --model1 gemini-2.5-flash-lite --model2 gemini-2.0-flash --iterations 30

# 4. Analyze reports to check for:
# - Win rate differences
# - First-player advantage impact
# - Deck-specific performance variations
```

### Automated Regression Testing

Use simulations in CI/CD to detect AI performance regressions:

```bash
#!/bin/bash
# run_regression_test.sh

# Run baseline simulation
python -m simulation.cli baseline --iterations 50 > results.txt

# Extract win rate from output
WIN_RATE=$(grep "Player 1 Win Rate" results.txt | awk '{print $5}')

# Check if within acceptable range (45-55%)
if (( $(echo "$WIN_RATE < 0.45" | bc -l) )) || (( $(echo "$WIN_RATE > 0.55" | bc -l) )); then
    echo "REGRESSION DETECTED: Win rate $WIN_RATE outside acceptable range"
    exit 1
fi

echo "PASS: Win rate $WIN_RATE within acceptable range"
```

## Contributing

When adding new simulation features:

1. **Update config.py** if adding new parameters
2. **Add validation** in deck_loader.py or orchestrator.py
3. **Write tests** in `backend/tests/test_simulation_*.py`
4. **Update CLI** in cli.py if exposing to users
5. **Document** in this README and relevant docs
6. **Update report format** in reporter.py if needed

### Testing Changes

```bash
# Run all simulation tests
cd backend
pytest tests/test_simulation_*.py -v

# Run specific test file
pytest tests/test_deck_validation.py -v

# Test CLI commands without full simulation
python -m simulation.cli list-decks
python -m simulation.cli list-runs --limit 5
```

## Related Documentation

- [SIMULATION.md](../docs/development/SIMULATION.md) - Original system documentation
- [SIMULATION_IMPROVEMENTS.md](../docs/development/SIMULATION_IMPROVEMENTS.md) - Enhancement history
- [AI_V4_ARCHITECTURE.md](../docs/development/AI_V4_ARCHITECTURE.md) - AI player architecture
- [ARCHITECTURE.md](../docs/development/ARCHITECTURE.md) - Overall game architecture

## Version History

### v2.0 (January 2026)
- Added CLI tool with presets
- Automated report generation
- Pre-flight deck validation with suggestions
- Simulation-specific logging control
- CC tracking enhancements (gained + spent)

### v1.0 (December 2025)
- Initial simulation system
- Parallel execution with ThreadPoolExecutor
- Database persistence
- Admin UI with live progress
- CC tracking per turn
