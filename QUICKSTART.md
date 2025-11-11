# GGLTCG Quick Start Guide

## What We've Built

You now have a **fully functional GGLTCG game** with both backend and frontend:

✅ **Complete project structure** - Backend and frontend fully implemented  
✅ **Core data models** - Card, Player, and GameState classes  
✅ **Card loading system** - All 18 cards from CSV  
✅ **Effect system** - All 18 card effects implemented (7 files, 1,433 lines)  
✅ **Game engine** - Turn management, card playing, tussle system (680 lines)  
✅ **FastAPI REST API** - 8 endpoints with auto-docs and CORS  
✅ **AI player** - Google Gemini integration for strategic opponent  
✅ **React frontend** - Complete UI with TypeScript, React Query, and game flow  
✅ **Comprehensive tests** - Card loading, effects, and game engine all passing  
✅ **Documentation** - Rules, design docs, and progress tracking  
✅ **First complete game played** - November 10, 2025 🎉

## Running the Game

### Backend Setup

```bash
cd backend
python3.13 -m venv venv  # Use Python 3.13
source venv/bin/activate  # On macOS/Linux; use venv\Scripts\activate on Windows
pip install -r requirements.txt

# Set up API key
cp .env.example .env
# Edit .env and add: GOOGLE_API_KEY=your_key_here
```

### Frontend Setup

```bash
cd frontend
npm install
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

## Next Development Session

Current focus: **Polish & Improvements**

### Known Issues (Tracked on GitHub)

- **Issue #4:** Display actual card names instead of "?" in player zones
- **Issue #5:** Additional UI/UX improvements

### Potential Enhancements

1. **Game Log Display** - Show event history in UI
2. **Animations** - Add card play and tussle animations
3. **Better Targeting** - Drag-and-drop for tussles
4. **Sound Effects** - Audio feedback for actions
5. **Card Tooltips** - Hover to see full card details

## Project Structure Reference

```
ggltcg/
├── backend/
│   ├── src/
│   │   ├── game_engine/
│   │   │   ├── models/          ✅ DONE - Card, Player, GameState
│   │   │   ├── rules/           ✅ DONE - TurnManager, TussleResolver
│   │   │   │   └── effects/     ✅ DONE - Effect system (7 files, 1,433 lines)
│   │   │   ├── ai/              ⏳ TODO - LLM player
│   │   │   ├── data/            ✅ DONE - CardLoader
│   │   │   └── game_engine.py   ✅ DONE - Main controller (680 lines)
│   │   └── api/                 ✅ DONE - FastAPI REST API (5 files)
│   ├── data/
│   │   └── cards.csv            ✅ DONE - 18 cards loaded
│   ├── tests/                   ✅ DONE - All tests passing
│   └── requirements.txt         ✅ DONE
├── frontend/                    ⏳ TODO - React app
├── docs/
│   ├── rules/                   ✅ DONE - Game rules
│   └── development/             ✅ DONE - Progress tracking
├── COPILOT_CONTEXT.md           ✅ DONE - Development guide
└── README.md                    ✅ DONE
```

## Key Files to Reference

When working with GitHub Copilot, keep these files open for context:

1. **COPILOT_CONTEXT.md** - Your development guide
2. **docs/rules/GGLTCG-Rules-v1_1.md** - Complete game rules
3. **backend/data/cards.csv** - All card definitions
4. **docs/development/MVP_PROGRESS.md** - Current progress

## GitHub Copilot Tips

### Getting Better Suggestions

1. **Write descriptive docstrings first:**
```python
def resolve_umbruh_effect(game_state: GameState, card: Card):
    """
    Resolve Umbruh's triggered effect: "When sleeped, gain 1 CC."
    
    This triggers when Umbruh is sleeped from play (not from hand).
    The card's controller gains 1 CC immediately.
    """
    # Copilot will generate the implementation
```

2. **Reference existing patterns:**
```python
# See TussleResolver._get_strength_modifiers for similar pattern
def apply_continuous_effects(game_state: GameState, card: Card):
```

3. **Use the chat for complex questions:**
- "How should I implement the Copy card mechanics?"
- "What's the best way to structure the effect registry?"
- "How do I handle Beary's tussle cancellation?"

## Common Development Tasks

### Add a New Card Effect

1. Identify effect type (Continuous/Triggered/Activated/Play)
2. Create effect class in appropriate file
3. Register in effect_registry.py
4. Write unit test
5. Update game engine to apply effect

### Test a Game Mechanic

1. Write a test in `backend/tests/`
2. Create sample game state
3. Execute the action
4. Assert expected outcome

### Run the API Server (once created)

```bash
cd backend
source venv/bin/activate
uvicorn src.api.main:app --reload
```

Visit: http://localhost:8000/docs for interactive API documentation

## Estimated Timeline

- ~~Effect System: 2-3 days~~ ✅ **COMPLETED**
- ~~Game Engine: 2-3 days~~ ✅ **COMPLETED**
- ~~FastAPI Endpoints: 1-2 days~~ ✅ **COMPLETED**
- **AI Player Integration:** 1-2 days ⏳ NEXT
- **Frontend Setup:** 2-3 days
- **UI Components:** 3-4 days
- **Testing & Polish:** 3-5 days

**Remaining:** 2-3 weeks (solo with Copilot)

## Questions or Issues?

Refer to:
- **Game Rules:** `docs/rules/GGLTCG-Rules-v1_1.md`
- **Design Doc:** `docs/GGLTCG-design.md`
- **Progress:** `docs/development/MVP_PROGRESS.md`
- **Copilot Guide:** `COPILOT_CONTEXT.md`

## Ready to Play

The MVP is complete! You can:

1. **Play the game** - Full gameplay with AI opponent
2. **Report issues** - Use GitHub issues for bugs or improvements
3. **Add features** - Check issues #4 and #5 for next priorities
4. **Explore the API** - Visit <http://localhost:8000/docs> when backend is running
