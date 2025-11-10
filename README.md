# GGLTCG - Googooland Trading Card Game

A tactical two-player card game with no randomness in draws—only skill and strategy.

## Project Overview

GGLTCG is a web application that allows players to play the Googooland TCG against an AI opponent. The game features 18 unique cards with diverse mechanics and strategic depth.

## Tech Stack

### Backend
- **Python 3.11+** with FastAPI
- Card data stored in CSV format
- Game state management with JSON serialization
- AI player powered by Claude Sonnet 4.5 (Anthropic API)

### Frontend
- **React** with Vite
- **Tailwind CSS** for styling
- RESTful API communication

## Project Structure

```
ggltcg/
├── backend/
│   ├── src/
│   │   ├── game_engine/
│   │   │   ├── models/          # Card, Player, GameState classes
│   │   │   ├── rules/           # Game logic, turn management, tussles
│   │   │   ├── ai/              # LLM player integration
│   │   │   └── data/            # Card loader, CSV handling
│   │   └── api/                 # FastAPI routes
│   ├── data/
│   │   └── cards.csv            # 18-card starter pack
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React UI components
│   │   ├── utils/               # API client, helpers
│   │   └── App.jsx
│   ├── public/
│   └── package.json
├── docs/
│   ├── rules/                   # Game rules documentation
│   └── development/             # Development guides
├── COPILOT_CONTEXT.md           # GitHub Copilot seed prompt
└── README.md
```

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Anthropic API key (for AI player)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Running the Application

**Backend:**
```bash
cd backend
uvicorn src.api.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

## Game Rules Quick Reference

- **Objective:** Put all opponent's cards into their Sleep Zone
- **Turn Start:** Gain 4 CC (Player 1 on Turn 1 gains only 2)
- **CC Cap:** Maximum 7 CC per player at any time
- **Tussle:** Pay CC to have two Toys fight. Higher speed strikes first

See `docs/rules/GGLTCG-Rules-v1_1.md` for complete rules.

## Development Roadmap

### Phase 1: MVP Foundation (Current)
- [x] Project setup and structure
- [ ] Core game engine (card loading, game state)
- [ ] Turn management and CC system
- [ ] Tussle resolution
- [ ] Card effect system
- [ ] Basic React UI
- [ ] AI player integration

### Phase 2: Complete Gameplay
- [ ] All 18 card effects implemented
- [ ] Polished UI with animations
- [ ] Game log and history

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
