# GGLTCG Development Context

## Project Status: Production-Ready MVP ✅

The GGLTCG web application is **fully complete and production-ready** with polished features including:
- Complete 18-card gameplay with all effects working
- AI opponent powered by Google Gemini
- Deck customization and player name editing
- Victory screen with factual and narrative play-by-play modes
- Backend CSV as single source of truth for card data
- Clean, tested, documented codebase

**First complete game played:** November 10, 2025 🎉

## Project Overview

We are building a web application for the Googooland TCG (GGLTCG), a two-player tactical card game with no randomness in draws. The game is fully codified in rules and currently supports 18 unique cards.

## Core Game Rules Summary

### Objective
Win immediately by putting all your opponent's cards into their Sleep Zone.

### Turn Structure
1. **Start Phase:** Gain 4 CC (Player 1 on Turn 1 gains only 2 CC)
2. **Main Phase:** Play cards, initiate tussles, activate abilities
3. **End Phase:** Unspent CC is saved for next turn (max 7 CC cap)

### Key Mechanics
- **Command Counters (CC):** Resource for playing cards and tussling
- **Three Zones:** Hand (hidden), In Play (active), Sleep Zone (defeated)
- **Tussle:** Combat between Toys. Higher speed strikes first (+1 speed bonus on your turn)
- **Direct Attack:** When opponent has no Toys in play, sleep random card from their hand (max 2/turn)
- **Card Types:** Toys (have stats) and Actions (resolve immediately, then sleep)

### Special Rules
- CC is banked between turns (max 7)
- Zone changes reset all modifications
- "When sleeped" triggers only work if card was in play
- Cards sleeped from hand don't trigger abilities

## Technical Stack

### Backend (Game Engine)

- **Language:** Python 3.13
- **Framework:** FastAPI 0.115.6 (async, lightweight, excellent Copilot support)
- **Data Storage:** CSV for cards (single source of truth), JSON for game states
- **AI Integration:** Google Gemini (gemini-2.0-flash or gemini-2.5-flash)

### Frontend (Player Interface)

- **Framework:** React 19 with TypeScript and Vite 7.2
- **Styling:** TailwindCSS 4.1
- **State Management:** React Query (@tanstack/react-query)
- **Communication:** REST API to FastAPI backend
- **Card Data:** Loaded from backend `/games/cards` endpoint

### Development Tools
- **Version Control:** Git/GitHub
- **IDE:** VS Code with GitHub Copilot
- **Testing:** pytest (backend), Vitest (frontend - future)

## Architecture Principles

1. **Separation of Concerns:** Game logic (Python) separate from presentation (React)
2. **Plugin-Based Effects:** Each card effect is a separate class implementing standard interfaces
3. **RESTful API:** Clean communication between frontend and backend
4. **State Immutability:** Game state modifications create new state objects
5. **Clear Data vs Logic:** Card data in CSV, card mechanics in Python classes

## Code Structure

### Backend Module Organization
```
backend/src/game_engine/
├── models/              # Data classes (Card, Player, GameState, Zone)
├── rules/               # Game logic (turn_manager, tussle_resolver, cost_calculator)
│   └── effects/         # Individual card effect handlers
├── ai/                  # LLM player (prompt_builder, action_parser, llm_player)
└── data/                # Card loader, CSV parser
```

### Effect System Pattern
Each card with special mechanics has a corresponding effect class:
- `ContinuousEffect`: Ka, Wizard, Demideca (always active)
- `TriggeredEffect`: Beary, Umbruh, Snuggles (condition-based)
- `ActivatedEffect`: Archer (player-activated)
- `PlayEffect`: Action cards (one-time resolution)

### Adding New Cards

1. Add row to `data/cards.csv` with card data (SINGLE SOURCE OF TRUTH)
2. Frontend automatically loads via `/games/cards` API endpoint
3. Create effect class in `rules/effects/` if special mechanics needed
4. Register effect in `effect_registry.py`
5. Write unit test for effect behavior
6. No frontend changes needed - backend is source of truth

## Development Guidelines

### Python Backend
- Use type hints for all function signatures
- Follow PEP 8 style guide
- Write docstrings for all classes and public methods
- Keep game state immutable where possible
- Use dataclasses for data models

**Example:**
```python
@dataclass
class Card:
    """Represents a card in the game."""
    name: str
    card_type: str  # "Toy" or "Action"
    cost: int
    effect_text: str
    speed: Optional[int] = None
    strength: Optional[int] = None
    stamina: Optional[int] = None
```

### React Frontend
- Use functional components with hooks
- Keep components small and focused
- Follow Airbnb React style guide
- Use meaningful component and variable names
- Extract reusable logic into custom hooks

**Example:**
```jsx
function CardDisplay({ card, zone, onClick }) {
  const isToy = card.card_type === 'Toy';
  
  return (
    <div className="card" onClick={onClick}>
      <h3>{card.name}</h3>
      {isToy && (
        <div className="stats">
          <span>Speed: {card.speed}</span>
          <span>Strength: {card.strength}</span>
          <span>Stamina: {card.stamina}</span>
        </div>
      )}
    </div>
  );
}
```

### API Design
- Use RESTful conventions
- Return consistent JSON structure
- Include proper HTTP status codes
- Validate all inputs
- Serialize game state to JSON

**Example Endpoints:**
```
POST /api/game/new          - Create new game
GET  /api/game/{id}         - Get game state
POST /api/game/{id}/play    - Play a card
POST /api/game/{id}/tussle  - Initiate tussle
POST /api/game/{id}/end     - End turn
```

## Current Implementation Status

### ✅ Completed - Production Ready

- [x] Project structure and documentation
- [x] Backend foundation (card loading from CSV, all models)
- [x] Core game engine (turn management, tussles, effects)
- [x] Effect system (all 18 cards fully implemented)
- [x] FastAPI REST API (9 endpoints with auto-docs)
- [x] AI player integration (Google Gemini with fallback)
- [x] React frontend (complete UI with 6 components)
- [x] Production features (deck picker, player names, narrative mode)
- [x] Code quality (clean, tested, documented)
- [x] Architecture (backend CSV as single source of truth)

### 🎯 Future Enhancements

- [ ] Animations and visual effects
- [ ] Sound effects  
- [ ] Game replay system
- [ ] Statistics and match history
- [ ] Additional card sets

## Critical Design Decisions

### Effect Extensibility
**Problem:** How to add new cards without hardcoding logic everywhere

**Solution:** Effect registration pattern
- Card CSV contains only data (stats, cost, effect text)
- Effect classes implement standard interfaces
- Registry maps card names to effect handlers
- Easy to audit, test, and extend

### AI Player Strategy
**Approach:** Use LLM prompt as AI "brain"
- Build dynamic prompt from current game state
- Request structured JSON output for easy parsing
- Include available actions and legal moves
- Provide context on game rules and strategy

### CC Banking System
**Key Rule:** Unspent CC is saved for next turn (max 7)
- Tracks CC separately in game state
- Validate CC cap on gain operations
- Display available CC prominently in UI

### Tussle Resolution
**Critical Logic:**
1. Calculate effective speed (base + turn bonus + modifiers)
2. Determine strike order (higher speed first, ties simultaneous)
3. Apply damage (Strength reduces Stamina)
4. Check for sleep (Stamina ≤ 0)
5. Handle first-strike prevention (defender sleeped before counter)

## Testing Strategy

### Unit Tests
- Test each effect class in isolation
- Test tussle resolution with various scenarios
- Test CC calculations and constraints
- Test zone transitions and state changes

### Integration Tests
- Test complete turn sequences
- Test card combinations and interactions
- Test win conditions
- Test AI decision making

### Manual Testing Checklist
- All 18 cards playable and functional
- Tussle resolution accurate
- CC banking and cap working
- Zone transitions correct
- Win detection immediate
- UI responsive and clear

## GitHub Copilot Usage Tips

### Context Setting
When starting a coding session, reference:
1. The specific game rule you're implementing
2. The module/component you're working in
3. Related classes or functions

### Function-Level Prompts
Write clear docstrings describing what you want:
```python
def resolve_tussle(attacker: Card, defender: Card, game_state: GameState) -> TussleResult:
    """
    Resolve a tussle between two Toys.
    
    Calculate effective speeds including turn bonus and continuous effects.
    Determine strike order based on speed comparison.
    Apply damage and sleep defeated Toys.
    Handle first-strike prevention.
    
    Returns TussleResult with outcome details.
    """
    # Copilot will generate implementation
```

### Iterative Refinement
1. Generate initial implementation
2. Review for correctness against rules
3. Use Copilot Chat to refactor and improve
4. Add error handling and edge cases

## Reference Files

- **Rules:** `docs/rules/GGLTCG-Rules-v1_1.md`
- **Cards:** `backend/data/cards.csv` (SINGLE SOURCE OF TRUTH)
- **Game Prompt:** `docs/GGLTCG-game-starting-prompt-v0_3.md`
- **Design Doc:** `docs/GGLTCG-design.md`
- **API Endpoints:** `backend/src/api/routes_games.py` (9 endpoints)
- **Progress:** `docs/development/MVP_PROGRESS.md`

## Success Metrics ✅ ACHIEVED

1. ✅ All 18 cards work correctly with proper effects
2. ✅ AI makes legal, strategic moves consistently
3. ✅ Human can complete full game without bugs
4. ✅ Code is maintainable and well-documented
5. ✅ Production-ready with polished features
6. ✅ Backend CSV is single source of truth for card data
