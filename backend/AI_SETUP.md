# AI Player Setup Guide

The GGLTCG AI player uses **Google Gemini's native structured output** mode for reliable JSON responses. This eliminates parsing errors and ensures the AI always returns valid, schema-compliant decisions.

## AI Version Configuration

GGLTCG supports two AI architectures:

| Version | Description | Best For |
|---------|-------------|----------|
| **v2** (default) | Single-action mode: LLM selects one action at a time | Debugging, baseline comparison |
| **v3** | Turn planning mode: LLM generates complete turn plan, then executes | Production, faster games |

### Enable v3 Turn Planning

```bash
export AI_VERSION=3
```

When `AI_VERSION=3`, the AI uses a two-phase approach:

1. **Planning Phase**: At turn start, generates a complete `TurnPlan` with:
   - Threat assessment of opponent's board
   - Resource summary (CC, cards in hand/play)
   - Selected strategy with reasoning
   - Full action sequence with CC budgeting
   - Expected CC efficiency

2. **Execution Phase**: Heuristic matching executes planned actions:
   - Each action matched to valid game actions
   - Falls back to LLM if plan doesn't match game state
   - Tracks execution status (complete/partial/fallback)

---

## Supported Providers

### Option 1: Google Gemini (FREE - Recommended)

Gemini offers a generous free tier and **native structured output** support via the `google-genai` SDK. The AI uses Pydantic models to define a JSON schema, ensuring reliable responses.

### Setup:

1. **Get a free API key:**
   - Visit: [https://aistudio.google.com/apikey](https://aistudio.google.com/api-keys)
   - Sign in with your Google account
   - Click "Get API key" or "Create API key"
   - Copy your API key

2. **Set the environment variable:**
   ```bash
   export GOOGLE_API_KEY='your-api-key-here'
   ```

3. **That's it!** The AI player will automatically use Gemini by default.

### Free Tier Limits:
- **Gemini 2.0 Flash**: 15 requests per minute, 1 million tokens per minute
- **Gemini 1.5 Flash**: 15 requests per minute, 1 million tokens per minute
- **Gemini 1.5 Pro**: 2 requests per minute, 32,000 tokens per minute

More than enough for game testing!

### Option 2: Anthropic Claude (Requires Credits)

Claude offers high-quality responses but requires purchasing API credits. Uses prompt-based JSON output (no native structured output).

### Setup:

1. **Get an API key:**
   - Visit: https://console.anthropic.com/
   - Create an account and add credits ($5 minimum)
   - Generate an API key

2. **Set environment variables:**
   ```bash
   export ANTHROPIC_API_KEY='your-api-key-here'
   export AI_PROVIDER='anthropic'
   ```

### Pricing:
- **Claude Sonnet 4**: ~$3 per million input tokens
- Each game turn uses ~500-2000 tokens
- $5 credit = hundreds of games

## Testing the AI Player

### Via Python Script:
```bash
cd backend
export GOOGLE_API_KEY='your-key'
python tests/test_ai_player.py
```

### Via API:
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

## Model Selection

### Gemini Models (edit `llm_player.py` to change):
- `gemini-2.0-flash-exp` (default) - Latest, fastest, free
- `gemini-1.5-flash` - Stable, fast, free
- `gemini-1.5-pro` - Most capable, free but lower rate limits

### Claude Models:
- `claude-sonnet-4-20250514` (default) - Balanced quality/speed
- `claude-3-5-sonnet-20241022` - Previous version
- `claude-3-opus-20240229` - Most capable but expensive

## Switching Providers

The AI player automatically detects which provider to use based on environment variables:

**Use Gemini (default):**
```bash
export GOOGLE_API_KEY='your-key'
# No AI_PROVIDER needed - Gemini is default
```

**Use Claude:**
```bash
export ANTHROPIC_API_KEY='your-key'
export AI_PROVIDER='anthropic'
```

## Troubleshooting

**"API key required" error:**
- Make sure you've exported the environment variable
- Check the variable name is correct
- Try printing it: `echo $GOOGLE_API_KEY`

**Rate limit errors:**
- Gemini free tier is generous but has limits
- Add a small delay between AI turns if needed
- Consider upgrading to paid tier for production

**AI makes invalid moves:**
- This is expected occasionally - the LLM parses natural language
- The code has fallbacks (default to ending turn)
- Improve prompts in `prompts.py` to reduce errors

**v3 plan execution issues:**
- Check AI logs in admin UI for fallback reasons
- Plan may not match game state (opponent played unexpectedly)
- See GitHub issues #267, #268, #271-#273 for known prompt bugs

---

## Viewing AI Logs in Admin

The admin interface (`/admin`) provides detailed AI decision logs:

1. **AI Logs Tab**: View all AI decisions with:
   - v3 turn plans: threat assessment, strategy, action sequence
   - Prompts and responses
   - Execution status (complete, partial, fallback)
   - CC efficiency metrics

2. **Filter by Game**: From Playbacks tab, click "View AI Logs for this Game"

3. **v3 Log Details**:
   - **Threat Assessment**: AI's analysis of opponent's board
   - **Strategy**: Selected approach for the turn
   - **Action Sequence**: Planned actions with CC budgeting
   - **Execution Status**: Whether plan was fully executed

---

## Next Steps

Once you have an API key set up:
1. Test the AI with `python tests/test_ai_player.py`
2. Play against it via the API
3. Observe its strategy and reasoning in admin AI logs
4. Try `AI_VERSION=3` for turn planning mode
5. Tune the prompts to improve play quality
