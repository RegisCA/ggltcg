# AI Player Setup Guide

The GGLTCG AI player runs a single architecture: a deterministic enumerator
computes every engine-legal action sequence for the turn (no LLM call), then
one **Google Gemini** call (strategic selection) picks the best sequence.
Gemini is the only supported provider — there is no provider abstraction or
planner-mode switch to configure.

See [AI_CURRENT_STATE.md](../docs/development/ai/AI_CURRENT_STATE.md) for the
full architecture reference.

## Setup

1. **Get a free API key:**
   - Visit: [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   - Sign in with your Google account
   - Click "Get API key" or "Create API key"
   - Copy your API key

2. **Set the environment variable:**

   ```bash
   export GOOGLE_API_KEY='your-api-key-here'
   ```

3. **That's it.** The AI player uses Gemini automatically — no other
   configuration is required.

## Model Selection

| Env var | Purpose | Default |
| --- | --- | --- |
| `GEMINI_MODEL` | Primary model | `gemini-flash-lite-latest` |
| `GEMINI_FALLBACK_MODEL` | Fallback model used on capacity (429) errors | `gemini-2.5-flash-lite` |

```bash
export GEMINI_MODEL='gemini-flash-lite-latest'
export GEMINI_FALLBACK_MODEL='gemini-2.5-flash-lite'
```

If you hit 429s on the primary model, the fallback kicks in automatically —
no action needed beyond making sure `GEMINI_FALLBACK_MODEL` is set to a model
with separate quota.

## Testing the AI Player

### Via pytest

```bash
cd backend
export GOOGLE_API_KEY='your-key'
python -m pytest tests/test_ai_enum_scenario.py -q -s
```

Live-LLM tests are skipped automatically (`pytestmark = pytest.mark.skipif(...)`)
when no real `GOOGLE_API_KEY` is present, so CI runs them with a dummy key and
skips the gated ones.

### Via API

```bash
# Start the server
cd backend
python run_server.py

# Create a game
curl -X POST http://localhost:8000/games \
  -H "Content-Type: application/json" \
  -d '{
    "player1": {
      "player_id": "human",
      "name": "You",
      "deck": ["Ka", "Knight", "Beary"]
    },
    "player2": {
      "player_id": "ai",
      "name": "AI Opponent",
      "deck": ["Wizard", "Demideca", "Archer"]
    },
    "first_player_id": "ai"
  }'

# Get game_id from response, then:
# Have AI take its turn
curl -X POST "http://localhost:8000/games/{game_id}/ai-turn?player_id=ai"
```

## Troubleshooting

**"API key required" error:**

- Make sure you've exported `GOOGLE_API_KEY`.

**Rate limit errors:**

- `gemini-flash-lite-latest` gives a generous free-tier daily quota and is
  the recommended default.
- If you hit 429s, the fallback model (`GEMINI_FALLBACK_MODEL`) kicks in
  automatically.

**AI makes invalid moves:**

- This should not happen — the enumerator only produces engine-legal
  sequences, so an "invalid move" is either an enumerator bug or an execution
  heuristic-matching bug, not a hallucination. File an issue with the AI logs
  for the turn (see below).

**Plan execution issues:**

- Check AI logs in the admin UI for fallback reasons.
- Plan may not match game state (opponent played unexpectedly), which
  triggers a mid-turn replan (capped at 2 per turn).

---

## Viewing AI Logs in Admin

The admin interface (`/admin`) provides detailed AI decision logs:

1. **AI Logs Tab**: View all AI decisions with:
   - Turn plans: strategy, action sequence, Charge budgeting
   - Strategic-selection prompt and response
   - Execution status (complete, partial, fallback)
   - Charge efficiency metrics

2. **Filter by Game**: From Playbacks tab, click "View AI Logs for this Game"

3. **Log Details**:
   - **Strategy**: Selected approach for the turn
   - **Action Sequence**: Planned actions with Charge budgeting
   - **Execution Status**: Whether the plan was fully executed

---

## Next Steps

Once you have an API key set up:

1. Test the AI with `python -m pytest tests/test_ai_enum_scenario.py -q -s`
2. Play against it via the API
3. Observe its strategy and reasoning in admin AI logs
4. Tune the prompts (`backend/src/game_engine/ai/prompts/`) to improve play quality
