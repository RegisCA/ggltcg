# Simulation System Documentation

## Overview

The Simulation System enables automated AI vs AI game testing to analyze game balance, deck performance, and LLM model behavior. It was implemented as part of GitHub Issue #243.

**Key Features:**

- Parallel game execution (5 games by default) for faster completion
- N² matchup matrix (all deck permutations)
- CC tracking for both players per turn
- Action logging with human-readable descriptions

## Architecture

### Components

```bash
backend/src/simulation/
├── __init__.py
├── config.py          # Data classes (SimulationConfig, GameResult, DeckConfig, etc.)
├── deck_loader.py     # Loads deck configurations from CSV
├── orchestrator.py    # Manages batch runs with parallel execution, DB persistence
└── runner.py          # Executes individual games with CC tracking & action logging
```

### Parallel Execution

Games run in parallel using a ThreadPoolExecutor (default: 5 workers). This significantly speeds up large simulation runs:

- Sequential: ~20 seconds/game → 160 games = ~53 minutes
- Parallel (5x): ~20 seconds/game → 160 games = ~11 minutes

Each parallel worker:

- Creates its own SimulationRunner instance
- Makes independent Gemini API calls
- Uses a separate database session for persistence
- Progress updates are thread-safe via locking

### API Routes

Located in `backend/src/api/routes_simulation.py`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/simulation/decks` | GET | List available simulation decks |
| `/admin/simulation/start` | POST | Start a new simulation run |
| `/admin/simulation/runs` | GET | List all simulation runs |
| `/admin/simulation/runs/{id}` | GET | Get run status/progress |
| `/admin/simulation/runs/{id}/results` | GET | Get detailed results with matchup stats |
| `/admin/simulation/runs/{id}/games/{num}` | GET | Get individual game details (CC tracking, action log) |

### Database Models

Located in `backend/src/api/db_models.py`:

- `SimulationRunModel` - Tracks run metadata, status, config
- `SimulationGameModel` - Individual game results with CC tracking and action log

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

Supported models are defined in `backend/src/simulation/config.py`:

```python
SUPPORTED_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-flash", 
    "gemini-2.5-flash-lite",
]
```

The default model is `gemini-2.0-flash`.

## Usage

### Starting a Simulation

Via API:

```bash
curl -X POST http://localhost:8000/admin/simulation/start \
  -H "Content-Type: application/json" \
  -d '{
    "deck_names": ["Aggro_Rush", "Control_Ka"],
    "iterations_per_matchup": 3,
    "player1_model": "gemini-2.0-flash",
    "player2_model": "gemini-2.0-flash"
  }'
```

Via Admin UI:

1. Navigate to Admin Data Viewer → Simulation tab
2. Select decks (1 for mirror match, 2+ for cross-deck testing)
3. Choose models for each player
4. Set iterations per matchup
5. Click "Start Simulation"

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

**CC Tracking:**
Each turn records both players' CC state:

- `turn`: Turn number (odd = P1's turn, even = P2's turn)
- For both `p1` and `p2`:
  - `cc_start`: CC at start of that player's action window
  - `cc_gained`: CC gained (from abilities like Umbruh's on-tussle effect)
  - `cc_spent`: CC spent on actions
  - `cc_end`: CC at end of turn

Note: Players can gain CC during their opponent's turn (e.g., Umbruh generates CC when tussled).

**Action Log:**
Each action records:

- `turn`: Turn number
- `player`: Player identifier
- `action`: Action type (play_card, tussle, activate_ability, direct_attack, end_turn)
- `card`: Card name (if applicable)
- `target`: Target card (if applicable)
- `description`: Human-readable action description (e.g., "Spent 2 CC for Knight to tussle Umbruh")
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
3. **Important**: Run both configurations (swap models) to control for first-player effects
4. Compare aggregate results

## Troubleshooting

### Simulation Stalls

If games don't complete:

1. Check server logs for API errors (429 rate limits, timeouts)
2. Verify the model is working in regular game mode first
3. Check the `error_message` field in game results

### Rate Limiting

Gemini API has rate limits. If hitting 429 errors:

- The system automatically falls back to `gemini-2.5-flash-lite`
- Reduce `iterations_per_matchup`
- Add delays between runs

### Model Issues

If a specific model isn't working:

1. Test in regular AI game mode first (easier to debug)
2. Check `backend/.env` for `GEMINI_API_KEY`
3. Verify model name matches Gemini API exactly

## Frontend

The Simulation UI is in the Admin Data Viewer (`frontend/src/components/AdminDataViewer.tsx`):

- **Simulation Tab**: Configure and start runs
- **Run History**: View past runs with status
- **Results Matrix**: Heatmap showing P1 win rates for all deck matchups
- **Individual Games Table**: List of all games with P1/P2 decks, winner, total CC spent
- **Game Detail Panel**: Inline below clicked game row, showing:
  - Turn-by-turn CC tracking for both players
  - Color-coded actions using play-by-play descriptions
  - Turn highlighting (green for P1's turns, blue for P2's turns)

## Future Enhancements

Potential improvements identified:

- [ ] Parallel game execution (currently sequential)
- [ ] Aggregate statistics across multiple runs
- [ ] Export results to CSV
- [ ] Configurable delays between API calls
- [ ] Model performance metrics (tokens, latency)
