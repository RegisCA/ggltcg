# Troubleshooting Prompt: Gemini 2.5 AI Player

## Context

We've implemented a simulation system for AI vs AI games. Testing with
`gemini-2.0-flash` works well (games complete in 17-25 seconds), but
`gemini-2.5-flash` shows different behavior:

- **Games complete but are slow** (133-276 seconds vs ~20 seconds)
- **High turn counts** (14-38 turns vs typical 8-15)
- **Passive play patterns** - AI appears to not take many actions per turn
- **Skewed win rates** - 100% P1 win in mirror tests (should be ~50-60%)

The issue is likely that Gemini 2.5 is not recognizing good action opportunities
or is being overly conservative in its decision-making.

## Goal

Improve Gemini 2.5's decision quality to match or exceed gemini-2.0-flash
behavior.

## Test Protocol

### Step 1: Check Current Configuration

```bash
# Check the current AI model configuration
grep -r "GEMINI" backend/.env
grep -r "gemini" backend/src/game_engine/ai/llm_player.py | head -20
```text
### Step 2: Switch Backend to Gemini 2.5

Edit `backend/.env` to set:
```text
DEFAULT_AI_MODEL=gemini-2.5-flash
```text
Or modify `backend/src/game_engine/ai/llm_player.py` to change the default
model.

### Step 3: Restart Backend

```bash
cd backend
# Kill existing server
lsof -ti :8000 | xargs kill -9 2>/dev/null
# Start fresh
source ../.venv/bin/activate
python run_server.py
```text
### Step 4: Start a Test Game

1. Open http://localhost:5173
2. Start a new game against AI
3. Make your first move
4. Watch the terminal for AI decision logs

### Step 5: Monitor Logs

Look for these log patterns:
```text
🤖 AI Turn X - Y actions available
Calling gemini API (gemini-2.5-flash)...
HTTP Request: POST https://generativelanguage.googleapis.com/...
```text
**Potential Issues:**
- If it hangs after "Calling gemini API" → API timeout or response parsing issue
- If you see 429 errors → Rate limiting
- If you see parsing errors → Model response format incompatibility
- If actions are mostly "end_turn" → AI not recognizing valid action
  opportunities
- If games are very long → AI being overly conservative

### Step 6: Compare Action Logs

Compare action logs between gemini-2.0-flash and gemini-2.5-flash games:

1. Run the same matchup with both models
2. View game details and check action logs
3. Look for patterns:
   - Is 2.5 choosing "end_turn" more often?
   - Is 2.5 playing fewer cards per turn?
   - Is 2.5's reasoning different?

### Step 7: Check Response Format

The AI expects structured JSON output:
```json
{
  "action_number": 1,
  "reasoning": "...",
  "target_ids": null,
  "alternative_cost_id": null
}
```text
If Gemini 2.5 returns a different format, we need to update the parsing logic.

## Key Files to Investigate

- `backend/src/game_engine/ai/llm_player.py` - Main AI decision logic
- `backend/src/game_engine/ai/prompts/` - Prompt templates
- `backend/src/simulation/runner.py` - Simulation game execution

## Known Differences Between Models

| Aspect | gemini-2.0-flash | gemini-2.5-flash |
|--------|------------------|------------------|
| Response time | ~1-2 seconds | ~2-5 seconds |
| Structured output | Works well | Works but may differ |
| Game duration | ~20 seconds | 133-276 seconds |
| Turn count | 8-15 typical | 14-38 observed |
| Decision quality | Good aggression | Possibly too conservative |

## Hypotheses to Test

1. **Prompt interpretation**: 2.5 may interpret the game state prompt
   differently
2. **Action selection**: 2.5 may have different risk assessment
3. **Structured output**: 2.5 may handle JSON response format differently
4. **Context length**: 2.5 may process long prompts differently

## Expected Outcome

After troubleshooting, you should be able to:
1. Play a complete game against AI using Gemini 2.5
2. Run simulations with Gemini 2.5 that complete successfully
3. Compare performance between 2.0 and 2.5 models
