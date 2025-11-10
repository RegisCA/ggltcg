# GGLTCG Quick Start Guide

## What We've Built So Far

You now have a solid foundation for the GGLTCG project with:

✅ **Complete project structure** - Backend and frontend directories organized  
✅ **Core data models** - Card, Player, and GameState classes  
✅ **Card loading system** - Parses all 18 cards from CSV  
✅ **Turn management** - CC system with banking (max 7), phase progression  
✅ **Tussle resolution** - Full combat logic with speed, strength, damage  
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

When you're ready to continue, here's what to work on next:

### 1. Effect System (Highest Priority)

Create the base effect classes that all card mechanics will use:

**Files to create:**
- `backend/src/game_engine/rules/effects/base_effect.py` - Abstract base classes
- `backend/src/game_engine/rules/effects/effect_registry.py` - Effect lookup
- `backend/src/game_engine/rules/effects/continuous_effects.py` - Ka, Wizard, Demideca
- `backend/src/game_engine/rules/effects/triggered_effects.py` - Beary, Umbruh, Snuggles
- `backend/src/game_engine/rules/effects/action_effects.py` - All Action cards

**Key Copilot Prompts:**
```python
class BaseEffect:
    """
    Abstract base class for all card effects.
    
    Effects are applied when:
    - Continuous: While card is in play
    - Triggered: When specific condition occurs
    - Activated: Player pays cost to activate
    - Play: When card is played (Actions)
    """
```

### 2. Game Engine

Complete the game engine to handle card playing and effect resolution:

**File to create:**
- `backend/src/game_engine/game_engine.py` - Main game controller

**Responsibilities:**
- Validate and execute player actions
- Apply card effects
- Check state-based actions (sleep defeated cards, check victory)
- Handle special cards (Copy, Twist, Ballaber)

### 3. FastAPI Server

Set up the REST API so the frontend can communicate:

**Files to create:**
- `backend/src/api/main.py` - FastAPI app initialization
- `backend/src/api/routes/game.py` - Game creation and state endpoints
- `backend/src/api/routes/actions.py` - Play card, tussle, end turn endpoints

**Example endpoint:**
```python
@router.post("/game/new")
async def create_game(player1_deck: List[str], player2_deck: List[str]):
    """
    Create a new game with selected decks.
    
    Both players select 6 unique cards from the 18-card pool.
    Randomly determine first player.
    Initialize game state with proper CC.
    """
```

## Project Structure Reference

```
ggltcg/
├── backend/
│   ├── src/
│   │   ├── game_engine/
│   │   │   ├── models/          ✅ DONE - Card, Player, GameState
│   │   │   ├── rules/           ✅ DONE - TurnManager, TussleResolver
│   │   │   │   └── effects/     ⏳ TODO - Effect system
│   │   │   ├── ai/              ⏳ TODO - LLM player
│   │   │   └── data/            ✅ DONE - CardLoader
│   │   └── api/                 ⏳ TODO - FastAPI routes
│   ├── data/
│   │   └── cards.csv            ✅ DONE - 18 cards loaded
│   ├── tests/                   ✅ Basic test created
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

- **Effect System:** 2-3 days
- **Game Engine:** 2-3 days
- **FastAPI Endpoints:** 1-2 days
- **AI Player Integration:** 1-2 days
- **Frontend Setup:** 2-3 days
- **UI Components:** 3-4 days
- **Testing & Polish:** 3-5 days

**Total MVP:** 4-6 weeks (solo with Copilot)

## Questions or Issues?

Refer to:
- **Game Rules:** `docs/rules/GGLTCG-Rules-v1_1.md`
- **Design Doc:** `docs/GGLTCG-design.md`
- **Progress:** `docs/development/MVP_PROGRESS.md`
- **Copilot Guide:** `COPILOT_CONTEXT.md`

## Ready to Continue?

Pick up where we left off by working on the effect system. Start with:

```bash
# Create the base effect class
code backend/src/game_engine/rules/effects/base_effect.py
```

Then use Copilot to help implement each effect type systematically!
