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
- AI player powered by Google Gemini 2.0 Flash Lite (30 RPM free tier)
- Alternative Claude Sonnet support (Anthropic API)

### Frontend

- **React 18** with TypeScript
- **Vite 7.2.2** for fast development
- **React Query** (@tanstack/react-query) for server state management
- **Axios** for HTTP client
- Plain CSS utilities (200+ classes)
- Dark theme UI with responsive design

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
│   │   └── api/                 # FastAPI routes (8 endpoints)
│   ├── data/
│   │   └── cards.csv            # 18-card starter pack
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React UI components
│   │   ├── hooks/               # React Query hooks
│   │   ├── api/                 # API client
│   │   ├── types/               # TypeScript definitions
│   │   ├── data/                # Card data
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
- Google Gemini API key (free tier, 30 RPM) or Anthropic API key (for AI player)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On macOS/Linux; use venv\Scripts\activate on Windows
pip install -r requirements.txt

# Copy .env.example to .env and add your API key
cp .env.example .env
# Edit .env and add: GOOGLE_API_KEY=your_key_here
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

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

**Frontend:**

```bash
cd frontend
npm run dev
# App runs at http://localhost:5175
```

Open <http://localhost:5175> in your browser to play!

## Game Rules Quick Reference

- **Objective:** Put all opponent's cards into their Sleep Zone
- **Turn Start:** Gain 4 CC (Player 1 on Turn 1 gains only 2)
- **CC Cap:** Maximum 7 CC per player at any time
- **Tussle:** Pay CC to have two Toys fight. Higher speed strikes first

See `docs/rules/GGLTCG-Rules-v1_1.md` for complete rules.

## Development Roadmap

### Phase 1: MVP Foundation ✅ COMPLETE

- [x] Project setup and structure
- [x] Core game engine (card loading, game state)
- [x] Turn management and CC system
- [x] Tussle resolution
- [x] Card effect system (all 18 cards)
- [x] FastAPI REST API (8 endpoints)
- [x] React + TypeScript UI
- [x] AI player integration (Gemini)
- [x] **First complete game played: November 10, 2025** 🎉

### Phase 2: Polish & Improvements (Current)

- [ ] Fix card name display in player zones (Issue #4)
- [ ] Additional UI/UX improvements (Issue #5)
- [ ] Game log display
- [ ] Animations and visual polish

### Phase 3: Admin UI - Card Management

- [ ] Card editor interface
- [ ] Effect documentation system

### Phase 4: Simulation System

- [ ] Automated game runner
- [ ] Statistics collection and reporting

## Contributing

This project is developed using GitHub Copilot. See `COPILOT_CONTEXT.md` for development guidelines and context.

## License

Private project - All rights reserved
