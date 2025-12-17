# Troubleshooting Prompt: Gemini 2.5 AI Player

## Context

We've implemented a simulation system for AI vs AI games. Testing with `gemini-2.0-flash` works well (games complete in 17-25 seconds), but `gemini-2.5-flash` appears to hang - games don't complete even after several minutes.

## Goal

Get the GGLTCG game working with `gemini-2.5-flash` as the AI model.

## Test Protocol

### Step 1: Check Current Configuration

```bash
# Check the current AI model configuration
grep -r "GEMINI" backend/.env
grep -r "gemini" backend/src/game_engine/ai/llm_player.py | head -20
```

### Step 2: Switch Backend to Gemini 2.5

Edit `backend/.env` to set:
```
DEFAULT_AI_MODEL=gemini-2.5-flash
```

Or modify `backend/src/game_engine/ai/llm_player.py` to change the default model.

### Step 3: Restart Backend

```bash
cd backend
# Kill existing server
lsof -ti :8000 | xargs kill -9 2>/dev/null
# Start fresh
source ../.venv/bin/activate
python run_server.py
```

### Step 4: Start a Test Game

1. Open http://localhost:5173
2. Start a new game against AI
3. Make your first move
4. Watch the terminal for AI decision logs

### Step 5: Monitor Logs

Look for these log patterns:
```
🤖 AI Turn X - Y actions available
Calling gemini API (gemini-2.5-flash)...
HTTP Request: POST https://generativelanguage.googleapis.com/...
```

**Potential Issues:**
- If it hangs after "Calling gemini API" → API timeout or response parsing issue
- If you see 429 errors → Rate limiting
- If you see parsing errors → Model response format incompatibility

### Step 6: Check Response Format

The AI expects structured JSON output:
```json
{
  "action_number": 1,
  "reasoning": "...",
  "target_ids": null,
  "alternative_cost_id": null
}
```

If Gemini 2.5 returns a different format, we need to update the parsing logic.

## Key Files to Investigate

- `backend/src/game_engine/ai/llm_player.py` - Main AI decision logic
- `backend/src/game_engine/ai/prompts/` - Prompt templates
- `backend/src/simulation/runner.py` - Simulation game execution

## Known Differences Between Models

| Aspect | gemini-2.0-flash | gemini-2.5-flash |
|--------|------------------|------------------|
| Response time | ~1-2 seconds | Unknown |
| Structured output | Works | To verify |
| Rate limits | Standard | May differ |

## Expected Outcome

After troubleshooting, you should be able to:
1. Play a complete game against AI using Gemini 2.5
2. Run simulations with Gemini 2.5 that complete successfully
3. Compare performance between 2.0 and 2.5 models
