# AI Player Setup Guide

The GGLTCG AI player uses **Google Gemini's native structured output** mode for reliable JSON responses. This eliminates parsing errors and ensures the AI always returns valid, schema-compliant decisions.

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

## Next Steps

Once you have an API key set up:
1. Test the AI with `python tests/test_ai_player.py`
2. Play against it via the API
3. Observe its strategy and reasoning (logged to console)
4. Tune the prompts to improve play quality
