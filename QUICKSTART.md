# GGLTCG Quick Start Guide

## What We've Built So Far

You now have a fully functional GGLTCG game backend with:

✅ **Complete project structure** - Backend and frontend directories organized  
✅ **Core data models** - Card, Player, and GameState classes  
✅ **Card loading system** - Parses all 18 cards from CSV  
✅ **Effect system** - All 16 card effects implemented (7 files, 1,433 lines)  
✅ **Game engine** - Turn management, card playing, tussle system (680 lines)  
✅ **FastAPI REST API** - Full server with game management and player actions  
✅ **Comprehensive tests** - Card loading, effects, and game engine all passing  
✅ **Documentation** - Rules, design docs, and Copilot context  

## Testing the Setup

Verify everything works:

```bash
cd backend
python3.13 -m venv venv  # Use Python 3.13 (3.14 not yet supported by all dependencies)
source venv/bin/activate
pip install -r requirements.txt
python tests/test_card_loader.py
```

You should see: `✅ All card loading tests passed!`

**Note:** This project requires **Python 3.13**. Python 3.14 is too new and not yet supported by pydantic-core.

## Next Development Session

When you're ready to continue, here are the remaining tasks:

### 1. AI Player Integration (Next Priority)

Integrate the Anthropic Claude API to create an AI opponent:

**Files to create:**
- `backend/src/game_engine/ai/llm_player.py` - AI player using Claude API
- `backend/src/game_engine/ai/prompts.py` - System prompts for the AI

**Key features:**
- Query Claude for next action based on game state
- Parse AI responses into valid game actions
- Handle multi-turn strategies

### 2. Frontend Development

Create the React-based user interface:

**Files to create:**
- `frontend/src/App.tsx` - Main application component
- `frontend/src/components/GameBoard.tsx` - Game board layout
- `frontend/src/components/CardDisplay.tsx` - Card visualization
- `frontend/src/components/PlayerHand.tsx` - Hand management
- `frontend/src/services/api.ts` - API client for backend

**Key features:**
- Visual card display with stats
- Drag-and-drop for playing cards
- Click to select tussle targets
- Real-time game state updates

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

## Ready to Continue?

The backend is now complete! You can:

1. **Test the API** - Start the server and try the interactive docs:
   ```bash
   cd backend
   python run_server.py
   # Visit http://localhost:8000/docs
   ```

2. **Build the AI player** - Integrate Claude for AI opponents

3. **Create the frontend** - Build the React UI for gameplay
