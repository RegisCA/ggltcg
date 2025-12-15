# GGLTCG Quick Start Guide

## What We've Built

You now have a **fully functional GGLTCG game** with both backend and frontend:

✅ **Complete project structure** - Backend and frontend fully implemented  
✅ **Core data models** - Card, Player, and GameState classes  
✅ **Card loading system** - All 18 cards from CSV (single source of truth)  
✅ **Effect system** - All 18 card effects implemented  
✅ **Game engine** - Turn management, card playing, tussle system  
✅ **FastAPI REST API** - 9 endpoints with auto-docs and CORS  
✅ **AI player** - Google Gemini integration for strategic opponent  
✅ **React frontend** - Complete UI with TypeScript, React Query, and game flow  
✅ **Comprehensive tests** - Card loading, effects, and game engine all passing  
✅ **Documentation** - Rules, design docs, and progress tracking  
✅ **First complete game played** - November 10, 2025 🎉  
✅ **Production features** - Play-by-play tracking, narrative mode, player customization  

## Running the Game

### Backend Setup

```bash
cd backend
python3.13 -m venv venv  # Use Python 3.13
source venv/bin/activate  # On macOS/Linux; use venv\Scripts\activate on Windows
pip install -r requirements.txt

# Set up API key and Database
cp .env.example .env
# Edit .env and add:
# GOOGLE_API_KEY=your_key_here
# DATABASE_URL=postgresql://user:password@localhost/ggltcg_db
# GOOGLE_CLIENT_ID=your_google_oauth_client_id
```

### Frontend Setup

```bash
cd frontend
npm install
# Create .env.local
echo "VITE_GOOGLE_CLIENT_ID=your_google_oauth_client_id" > .env.local
```

### Start Playing

**Terminal 1 - Backend:**

```bash
cd backend
source venv/bin/activate
python run_server.py
# Server at http://localhost:8000
# API docs at http://localhost:8000/docs
```

**Terminal 2 - Frontend:**

```bash
cd frontend
npm run dev
# Game at http://localhost:5175
```

Open <http://localhost:5175> and play against the AI!

**Note:** This project requires **Python 3.13**. Python 3.14 is not yet supported by all dependencies.

## Key Features

### 🎮 Gameplay

- **Quick Play** - Jump straight into battle with random decks for instant action
- **Deck Selection** - Build your own deck with split Toys/Actions layout and sorting options
- **Favorite Decks** - Save up to 3 favorite decks for quick reuse (requires login)
- **Random Deck** - Generate completely random decks (any combination of toys/actions)
- **Player Customization** - Click to edit player names
- **Strategic AI** - Powered by Google Gemini with intelligent decision-making
- **Live Play-by-Play** - Track every action with AI reasoning displayed

### 📖 Victory Screen

- **Factual Mode** - Complete play-by-play with CC costs and AI reasoning
- **Story Mode** - AI-generated "bedtime story" narrative of your epic battle
- **Beautiful Formatting** - Organized by turns with clear visual hierarchy

### 🎨 UI/UX Polish

- **Card Size Options** - Medium-sized hand cards show effects clearly
- **Responsive Design** - Works on desktop and tablet
- **Dark Theme** - Easy on the eyes with GGLTCG branding
- **Victory Screen** - Comprehensive game summary with play-by-play

## Project Structure Reference

```mermaid
ggltcg/
├── backend/
│   ├── src/
│   │   ├── game_engine/
│   │   │   ├── models/          ✅ Card, Player, GameState
│   │   │   ├── rules/           ✅ TurnManager, Effects
│   │   │   │   └── effects/     ✅ Effect system (7 files)
│   │   │   ├── ai/              ✅ LLM player (Gemini)
│   │   │   ├── data/            ✅ CardLoader (CSV single source of truth)
│   │   │   └── game_engine.py   ✅ Main controller + tussle resolution
│   │   └── api/                 ✅ FastAPI REST API (9 endpoints)
│   ├── data/
│   │   └── cards.csv            ✅ 18 cards - SINGLE SOURCE OF TRUTH
│   ├── tests/                   ✅ All tests passing
│   └── requirements.txt         ✅ DONE
├── frontend/                    ✅ React + TypeScript + Vite
│   ├── src/
│   │   ├── components/          ✅ 6 UI components
│   │   ├── hooks/               ✅ React Query hooks
│   │   ├── api/                 ✅ API client & services
│   │   └── types/               ✅ TypeScript definitions
│   └── package.json             ✅ Dependencies installed
├── docs/
│   ├── rules/                   ✅ Game rules
│   └── development/             ✅ Progress tracking
├── COPILOT_CONTEXT.md           ✅ Development guide
└── README.md                    ✅ DONE
```

## API Endpoints

The backend provides 9 REST endpoints:

**Game Management:**

- `GET /games/cards` - Get all card data from CSV (frontend loads this on startup)
- `POST /games` - Create new game
- `GET /games/{id}` - Get game state
- `DELETE /games/{id}` - Delete game
- `POST /games/random-deck` - Generate random deck

**Game Actions:**

- `POST /games/{id}/play-card` - Play a card
- `POST /games/{id}/tussle` - Initiate tussle
- `POST /games/{id}/end-turn` - End turn
- `POST /games/{id}/ai-turn` - AI takes action

**Game Features:**

- `GET /games/{id}/valid-actions` - Get available actions
- `POST /games/narrative` - Generate bedtime story from play-by-play

**Other:**

- `GET /` - API info
- `GET /health` - Health check

Visit `http://localhost:8000/docs` when running to see interactive API documentation.

## Development Workflow

### Making Changes

1. **Backend Changes** - Edit files in `backend/src/`
2. **Frontend Changes** - Edit files in `frontend/src/`
3. **Card Data** - Edit `backend/data/cards.csv` (SINGLE SOURCE OF TRUTH)
4. **Testing** - Run `pytest` in backend directory

### Adding New Cards

1. Add row to `backend/data/cards.csv`
2. Frontend will automatically load it via `/games/cards` API
3. If special effect needed, add effect class in `backend/src/game_engine/rules/effects/`
4. No frontend changes needed - backend CSV is the source of truth

### Code Organization

- **Backend CSV** is the single source of truth for all card data
- Frontend fetches cards via `/games/cards` API endpoint on startup
- Card data cached in frontend to avoid repeated API calls
- No duplicate card definitions anywhere

## Key Files for Contributors

When contributing or working with GitHub Copilot, reference these files:

1. **backend/data/cards.csv** - All card definitions (SINGLE SOURCE OF TRUTH)
2. **docs/rules/GGLTCG-Rules-v1_1.md** - Complete game rules
3. **backend/src/api/routes_games.py** - API endpoints
4. **frontend/src/components/** - UI components
5. **COPILOT_CONTEXT.md** - Development guidelines
6. **docs/development/MVP_PROGRESS.md** - Current progress

## Ready to Play

The MVP is complete with production features! You can:

1. **Play the game** - Full gameplay with AI opponent, player customization, and narrative mode
2. **Review the code** - Clean, well-documented, tested, and production-ready
3. **Add features** - Backend CSV makes adding cards trivial
4. **Explore the API** - Visit <http://localhost:8000/docs> when backend is running

Enjoy your epic toy battles in Googooland! 🎮✨
