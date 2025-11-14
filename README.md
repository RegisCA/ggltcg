# GGLTCG - Googooland Trading Card Game

A tactical two-player card game with no randomness in draws—only skill and strategy.

## Project Overview

GGLTCG is a web application that allows players to play the Googooland TCG against an AI opponent. The game features 18 unique cards with diverse mechanics and strategic depth.

## Tech Stack

### Backend

- **Python 3.13** with FastAPI 0.115.6
- Uvicorn 0.34.0 ASGI server
- Card data stored in CSV format
- Game state management with JSON serialization
- AI player powered by Google Gemini (free tier available)
- Alternative LLM providers supported (see `backend/AI_SETUP.md`)

### Frontend

- **React 19** with TypeScript
- **Vite 7.2.2** for fast development
- **React Query** (@tanstack/react-query) for server state management
- **Axios** for HTTP client
- **TailwindCSS 4.1** for styling
- Dark theme UI with responsive design
- 6 polished components for complete game experience

## Project Structure

```
ggltcg/
├── backend/
│   ├── src/
│   │   ├── game_engine/
│   │   │   ├── models/          # Card, Player, GameState classes
│   │   │   ├── rules/           # Game logic, turn management, tussles
│   │   │   │   └── effects/     # Card effect system (18 cards)
│   │   │   ├── ai/              # LLM player integration (Gemini/Claude)
│   │   │   └── data/            # Card loader, CSV handling
│   │   └── api/                 # FastAPI routes (9 endpoints)
│   ├── data/
│   │   └── cards.csv            # 18-card starter pack (SINGLE SOURCE OF TRUTH)
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React UI components (6 components)
│   │   ├── hooks/               # React Query hooks
│   │   ├── api/                 # API client
│   │   ├── types/               # TypeScript definitions
│   │   └── App.tsx
│   ├── public/
│   └── package.json
├── docs/
│   ├── rules/                   # Game rules documentation
│   └── development/             # Development guides, MVP progress
├── COPILOT_CONTEXT.md           # GitHub Copilot seed prompt
└── README.md
```

## Development Setup

### Prerequisites

- Python 3.13+
- Node.js 18+
- Google Gemini API key (get one free at <https://aistudio.google.com/api-keys>)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On macOS/Linux; use venv\Scripts\activate on Windows
pip install -r requirements.txt

# Copy .env.example to .env and add your API key
cp .env.example .env
# Edit .env and add: GOOGLE_API_KEY=your_key_here
# Get your free API key at: https://aistudio.google.com/api-keys
# Optional: If you experience 429 capacity errors with gemini-2.0-flash-lite,
# add GEMINI_MODEL=gemini-2.5-flash to use a newer, more stable model
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Running the Application

**Backend:**

```bash
cd backend
# Option 1: Activate venv first
source venv/bin/activate
python run_server.py

# Option 2: Run directly with venv Python (no activation needed)
./venv/bin/python3 run_server.py

# Option 3: Use an alternate deck CSV file
python run_server.py --deck-csv /path/to/your/custom_cards.csv

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

**Command Line Options:**

The backend server supports the following command-line arguments:

- `--deck PATH`: Path to a custom deck CSV file (default: `backend/data/cards.csv`)
- `--host HOST`: Host to bind the server to (default: `0.0.0.0`)
- `--port PORT`: Port to bind the server to (default: `8000`)
- `--no-reload`: Disable auto-reload on code changes

Example with custom deck and different port:
```bash
python run_server.py --deck-csv my_custom_deck.csv --port 8080
```

**Frontend:**

```bash
cd frontend
npm run dev
# App runs at http://localhost:5173
```

Open <http://localhost:5175> in your browser to play!

## Custom Deck CSV Format

You can create your own custom deck by providing a CSV file with the following format:

```csv
name,status,cost,effect,speed,strength,stamina,faction,quote,primary_color,accent_color
Beary,18,1,"Knight's effects don't affect this card...",3,3,5,,,#C74444,#C74444
Rush,18,0,A Toy you choose gets +2 speed until end of turn.,,,,,#8B5FA8,#8B5FA8
```

**Required columns:**
- `name`: Card name (must be unique)
- `cost`: Card cost (use `?` for variable cost cards like Copy)
- `effect`: Card effect text
- `speed`, `strength`, `stamina`: For Toy cards (leave empty for Action cards)
- `primary_color`, `accent_color`: Hex color codes for card appearance

**Card Types:**
- **Toy cards**: Must have speed, strength, and stamina values
- **Action cards**: Leave speed, strength, and stamina columns empty

See `backend/data/cards.csv` for the complete reference implementation with all 18 cards.

## Game Rules Quick Reference

- **Objective:** Put all opponent's cards into their Sleep Zone
- **Turn Start:** Gain 4 CC (Player 1 on Turn 1 gains only 2)
- **CC Cap:** Maximum 7 CC per player at any time
- **Tussle:** Pay CC to have two Toys fight. Higher speed strikes first

See `docs/rules/GGLTCG-Rules-v1_1.md` for complete rules.

## Troubleshooting

### AI Player Issues

**429 Resource Exhausted Errors:**

- This is a Google infrastructure capacity issue, not your API rate limit
- The free tier `gemini-2.0-flash-lite` can be overloaded during peak times
- **Solution 1:** Wait a few minutes and try again
- **Solution 2:** Switch to `gemini-2.5-flash` (newer, more stable):

  ```bash
  # Add to backend/.env:
  GEMINI_MODEL=gemini-2.5-flash
  ```

- The code automatically retries with exponential backoff (1s, 2s, 4s)

**Rate Limit Exceeded:**

- Check your usage at <https://aistudio.google.com/usage>
- Free tier limits: 15 requests per minute (RPM) for most models
- Wait 1 minute and try again, or slow down gameplay

**AI Not Making Decisions:**

- Check backend terminal for detailed logs showing Gemini API calls
- Logs include prompts, responses, and error details
- Look for ERROR or WARNING messages in the output

**Using Alternative LLM Providers:**

- This project supports multiple LLM providers (Gemini, Claude, etc.)
- See `backend/AI_SETUP.md` for detailed setup instructions for each provider
- Gemini is recommended for development due to its generous free tier



## Development Roadmap

### Phase 1: MVP Foundation ✅ COMPLETE

- [x] Project setup and structure
- [x] Core game engine (card loading, game state)
- [x] Turn management and CC system
- [x] Tussle resolution
- [x] Card effect system (all 18 cards)
- [x] FastAPI REST API (9 endpoints)
- [x] React + TypeScript UI
- [x] AI player integration (Gemini)
- [x] **First complete game played: November 10, 2025** 🎉

### Phase 2: Production Polish ✅ COMPLETE

- [x] Automated deck picker with slider (Issue #19)
- [x] Victory screen with play-by-play and AI reasoning (Issue #20)
- [x] Medium-sized hand cards showing effects (Issue #22)
- [x] Player name customization (Issue #23)
- [x] Narrative "bedtime story" mode (Issue #21)
- [x] Backend CSV as single source of truth
- [x] Production-ready code cleanup

### Phase 3: Future Enhancements

- [ ] Card animations and visual effects
- [ ] Sound effects
- [ ] Game replay system
- [ ] Statistics and match history
- [ ] Additional card sets

## Contributing

This project is developed using GitHub Copilot. See `COPILOT_CONTEXT.md` for development guidelines and context.

## License

Private project - All rights reserved
