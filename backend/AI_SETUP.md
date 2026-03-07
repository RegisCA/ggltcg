# AI Player Setup Guide

The GGLTCG AI player supports a provider abstraction with three current backends:

- Gemini: native structured output via `google-genai`
- Groq: OpenAI-compatible JSON mode, currently best for fast experimentation
- OpenRouter: OpenAI-compatible JSON mode for broader model access

Gemini remains the default provider. Groq and OpenRouter support are experimental and should be treated as proof-of-concept paths until they have broader live regression coverage.

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

### Option 1: Google Gemini

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

3. **That's it.** The AI player will automatically use Gemini by default.

### Free Tier Limits:
- **Gemini 2.0 Flash**: 15 requests per minute, 1 million tokens per minute
- **Gemini 1.5 Flash**: 15 requests per minute, 1 million tokens per minute
- **Gemini 1.5 Pro**: 2 requests per minute, 32,000 tokens per minute

### Recommended environment

```bash
export GOOGLE_API_KEY='your-key'
# AI_PROVIDER defaults to gemini
```

### Option 2: Groq

Groq exposes an OpenAI-compatible API and works with the new provider abstraction. The best current test target is `llama-3.1-8b-instant`.

### Setup:

1. **Get an API key:**
   - Visit: https://console.groq.com/keys
   - Create an account
   - Generate an API key

2. **Set environment variables:**
   ```bash
   export AI_PROVIDER='groq'
   export GROQ_API_KEY='your-api-key-here'
   export AI_MODEL='llama-3.1-8b-instant'
   ```

### Current behavior

- Single live tests can pass cleanly.
- Bursty test files can still hit Groq `429` limits.
- The provider adapter now retries, but free-tier throughput still needs practical evaluation.

### Option 3: OpenRouter

OpenRouter is useful when you want access to models such as `openai/gpt-oss-20b` through the same OpenAI-compatible adapter shape.

### Setup:

```bash
export AI_PROVIDER='openrouter'
export OPENROUTER_API_KEY='your-api-key-here'
export AI_MODEL='openai/gpt-oss-20b'
```

OpenRouter support is implemented but has not yet been validated in this branch with a live key.

## Testing the AI Player

### Via Python Script:
```bash
cd backend
export GOOGLE_API_KEY='your-key'
python tests/test_ai_player.py
```

### Provider-aware live test example:

```bash
cd backend
AI_PROVIDER=groq GROQ_API_KEY='your-key' AI_MODEL='llama-3.1-8b-instant' \
   python -m pytest tests/test_ai_standard_scenario.py::TestStandardScenario::test_turn1_with_surge_knight -q -s
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

Use `AI_MODEL` for provider-neutral selection.

Examples:

- Gemini: `AI_MODEL='gemini-3.1-flash-lite-preview'`
- Groq: `AI_MODEL='llama-3.1-8b-instant'`
- OpenRouter: `AI_MODEL='openai/gpt-oss-20b'`

Gemini-specific compatibility env vars `GEMINI_MODEL` and `GEMINI_FALLBACK_MODEL` still work.

## Switching Providers

The AI player detects the provider from `AI_PROVIDER` and resolves provider-specific keys automatically.

**Use Gemini (default):**
```bash
export GOOGLE_API_KEY='your-key'
# No AI_PROVIDER needed - Gemini is default
```

**Use Groq:**
```bash
export AI_PROVIDER='groq'
export GROQ_API_KEY='your-key'
export AI_MODEL='llama-3.1-8b-instant'
```

**Use OpenRouter:**
```bash
export AI_PROVIDER='openrouter'
export OPENROUTER_API_KEY='your-key'
export AI_MODEL='openai/gpt-oss-20b'
```

## Troubleshooting

**"API key required" error:**
- Make sure you've exported the environment variable
- Check that the key matches the selected provider
- Gemini uses `GOOGLE_API_KEY`
- Groq uses `GROQ_API_KEY`
- OpenRouter uses `OPENROUTER_API_KEY`

**Rate limit errors:**
- Gemini free tier is currently too restrictive for sustained simulation use.
- Groq works for isolated live tests but can still hit `429` errors on bursty test files.
- Reduce batch size and run one scenario at a time when comparing experimental providers.

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
