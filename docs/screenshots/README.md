# GGLTCG Screenshots

This directory contains screenshots of the GGLTCG web application for documentation purposes.

## Available Screenshots

### Deck Selection Screen
- **deck-selection-empty.png** - Shows the initial deck selection screen with 0/6 cards selected
- **deck-selection-full.png** - Shows the deck selection screen with 6/6 cards selected (ready to confirm)

### Game Board
- **gameboard-turn1-start.png** - Shows the initial game state at Turn 1 with all zones empty

## Missing Screenshots (Requires AI API Key)

To capture additional screenshots showing realistic mid/late game situations and victory screens, a valid Google Gemini API key is required. These screenshots would include:

### Game Board - Additional States
- Mid-game state with toys in play on both sides
- Late game with cards in sleep zones
- Game state showing tussle resolution
- Game state with various card effects active

### Victory Screen
- Victory screen in factual/play-by-play mode showing turn-by-turn actions
- Victory screen in narrative/story mode showing AI-generated bedtime story

## How to Capture Screenshots

1. Set up backend with valid `GOOGLE_API_KEY` in `backend/.env`
2. Run backend: `cd backend && python run_server.py`
3. Run frontend: `cd frontend && npm run dev`
4. Play through a complete game
5. Use browser screenshots or Playwright to capture screens

## Technical Details

- **Format**: PNG
- **Full Page**: Screenshots are captured with full page scrolling when needed
- **Locations Referenced**: Screenshots are referenced in `../../COPILOT_CONTEXT.md`
