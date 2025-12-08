# GGLTCG Architecture Documentation

**Version:** 3.0  
**Date:** December 8, 2025  
**Status:** Current production implementation

**Major Changes:**
- Added ActionValidator and ActionExecutor classes
- Eliminated ~457 lines of code duplication
- Unified validation and execution logic for human and AI players

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Backend Architecture](#backend-architecture)
3. [Effects System](#effects-system)
4. [Game State Management](#game-state-management)
5. [Card Lifecycle](#card-lifecycle)
6. [Target Selection System](#target-selection-system)
7. [API Layer](#api-layer)
8. [Frontend Architecture](#frontend-architecture)
9. [Frontend Design System](#frontend-design-system)
10. [Known Issues & Technical Debt](#known-issues--technical-debt)
11. [Migration Considerations](#migration-considerations)

---

## System Overview

### Technology Stack

**Backend:**
- FastAPI (Python 3.13+)
- Uvicorn (ASGI server)
- PostgreSQL database with SQLAlchemy ORM
- Alembic for database migrations

**Frontend:**
- React 19.2
- TypeScript 5.9
- Vite 7.2
- TanStack Query (React Query)
- Tailwind CSS 4.1

**AI Integration:**
- Google Gemini API (primary and fallback endpoints)

### Architecture Pattern

**Current:** Monolithic backend with RESTful API supporting:
- Quick Play vs AI
- 1v1 Online Multiplayer via lobby system (polling-based)
- Google OAuth authentication
- Persistent game state in PostgreSQL

---

## Backend Architecture

### Directory Structure

```
backend/
├── src/
│   ├── api/                    # FastAPI application layer
│   │   ├── app.py             # Main FastAPI app, CORS config
│   │   ├── routes_actions.py  # Game actions (play, tussle, AI turn)
│   │   ├── routes_games.py    # Game management (create, get state)
│   │   ├── routes_lobby.py    # Multiplayer lobby system
│   │   ├── routes_auth.py     # Google OAuth authentication
│   │   ├── routes_stats.py    # Player stats and leaderboard
│   │   ├── routes_admin.py    # Admin endpoints (logs, playbacks)
│   │   ├── routes_maintenance.py # Database cleanup tasks
│   │   ├── schemas.py         # Pydantic models for API
│   │   ├── game_service.py    # Game state management with DB persistence
│   │   ├── database.py        # SQLAlchemy setup
│   │   └── db_models.py       # Database models
│   │
│   └── game_engine/           # Core game logic (domain layer)
│       ├── game_engine.py     # Main game orchestrator
│       ├── ai/                # AI player implementation
│       │   ├── llm_player.py # LLM-based AI decision making
│       │   └── prompts.py    # Prompt templates
│       ├── data/
│       │   └── card_loader.py # Load cards from CSV
│       ├── models/
│       │   ├── card.py       # Card data model
│       │   ├── game_state.py # Game state container
│       │   ├── player.py     # Player data model
│       │   └── actions.py    # Structured action types
│       ├── rules/
│       │   ├── turn_manager.py
│       │   └── effects/       # Card effects system
│       │       ├── base_effect.py
│       │       ├── action_effects.py
│       │       ├── triggered_effects.py
│       │       ├── continuous_effects.py
│       │       └── effect_registry.py
│       └── validation/        # Action validation and execution
│           ├── __init__.py
│           ├── action_validator.py  # Validates valid actions
│           └── action_executor.py   # Executes actions
```

### Separation of Concerns

**✅ Well Separated:**
- API layer (`api/`) cleanly separated from game logic (`game_engine/`)
- Effect types properly abstracted (base classes)
- Turn management isolated in `turn_manager.py`
- Validation logic centralized in `ActionValidator`
- Execution logic centralized in `ActionExecutor`
- Database layer abstracted through SQLAlchemy ORM
- Authentication handled separately in `auth_routes.py`

**Recent Improvements (Nov 2025):**
- Eliminated ~457 lines of code duplication with ActionValidator/ActionExecutor refactor
- Migrated from in-memory storage to PostgreSQL with Alembic migrations
- Unified AI and human player code paths through structured actions

---

## Effects System

The effects system is the core of card behavior. It uses inheritance and polymorphism to handle different effect types, with support for both **legacy card-specific effects** and **modern data-driven generic effects**.

### Data-Driven Effects (New Approach)

**Goal:** Enable adding new cards via CSV without writing Python code.

**Architecture:**
1. **Generic Effect Classes** - Parameterized effects that work for multiple cards
2. **CSV Effect Definitions** - Card data includes `effects` column with effect strings
3. **EffectFactory Parser** - Parses effect strings into effect instances
4. **Priority System** - Check CSV effects first, fallback to legacy name-based registry

**CSV Format:**
```csv
name,type,cost,effects,...
Ka,Toy,1,stat_boost:strength:2,...
Rush,Action,0,gain_cc:2:not_first_turn,...
Wake,Action,1,unsleep:1,...
```

**Effect String Syntax:**
- Format: `effect_type:param1:param2:...`
- Multiple effects: `effect1:param1;effect2:param1:param2`
- Examples:
  - `stat_boost:strength:2` - Ka gains +2 strength
  - `stat_boost:all:1` - Demideca gains +1 to all stats
  - `gain_cc:2:not_first_turn` - Rush gains 2 CC (not on first turn)
  - `unsleep:2` - Sun unsleeps 2 cards
  - `sleep_all` - Clean sleeps all cards in play

**Current Status:**
- ✅ Data-driven effects implemented for 10+ cards
- ✅ StatBoostEffect, GainCCEffect, UnsleepEffect, SleepAllEffect
- ✅ Complex cards use custom effects (Knight, Beary, Copy, Twist, Archer)
- 📊 27 cards total in production

### Effect Type Hierarchy

```
BaseEffect (abstract)
├── ContinuousEffect
│   ├── StatBoostEffect (GENERIC - data-driven)
│   ├── KaEffect (LEGACY - to be deprecated)
│   ├── DemidecaEffect (LEGACY - to be deprecated)
│   └── CostModificationEffect
│       ├── DreamCostEffect
│       └── WizardCostEffect
├── TriggeredEffect
│   ├── SnugglesWhenPlayedEffect
│   ├── SnugglesWhenSleepedEffect
│   └── UmbruhEffect
├── PlayEffect
│   ├── GainCCEffect (GENERIC - data-driven)
│   ├── UnsleepEffect (GENERIC - data-driven)
│   ├── SleepAllEffect (GENERIC - data-driven)
│   ├── WakeEffect (LEGACY - to be deprecated)
│   ├── SunEffect (LEGACY - to be deprecated)
│   ├── RushEffect (LEGACY - to be deprecated)
│   ├── CleanEffect (LEGACY - to be deprecated)
│   ├── TwistEffect
│   └── CopyEffect
└── ActivatedEffect
    └── ArcherEffect
```

### Effect Lifecycle

#### 1. Registration (Startup)

Effects are registered in `effect_registry.py`:

```python
# Example: Register Twist effect
EffectRegistry.register("Twist", TwistEffect)
```

**When:** Application startup  
**Where:** `effect_registry.py` static initialization

#### 2. Instantiation (Card Creation)

Effects are instantiated when cards are loaded:

```python
effects = EffectRegistry.get_effects(card)
# Returns list of effect instances bound to that card
```

**When:** Card loader creates cards from CSV  
**Where:** `EffectRegistry.get_effects()`

#### 3. Execution (During Play)

Different effect types execute at different times:

**PlayEffect** - Executed when action card is played:
```python
# In game_engine.py -> _resolve_action_card()
effects = EffectRegistry.get_effects(card)
for effect in effects:
    if isinstance(effect, PlayEffect):
        effect.apply(game_state, player=player, **kwargs)
```

**TriggeredEffect** - Executed when trigger condition met:
```python
# In game_engine.py -> _trigger_when_played_effects()
if effect.trigger == TriggerTiming.WHEN_PLAYED:
    if effect.should_trigger(game_state, played_card=card):
        effect.apply(game_state, player=player, **kwargs)
```

**ContinuousEffect** - Checked during stat calculations:
```python
# In game_engine.py -> get_card_stat()
for effect in all_continuous_effects:
    value = effect.modify_stat(card, stat_name, value, game_state)
```

**CostModificationEffect** - Checked during cost calculation:
```python
# In game_engine.py -> calculate_card_cost()
for effect in cost_modifying_effects:
    cost = effect.modify_card_cost(card, cost, game_state, player)
```

### Effect Execution

See [EFFECT_SYSTEM_ARCHITECTURE.md](EFFECT_SYSTEM_ARCHITECTURE.md) for detailed effect execution flows and examples.

---

## Game State Management

### State Container: GameState

```python
@dataclass
class GameState:
    game_id: str
    players: Dict[str, Player]          # player_id -> Player
    active_player_id: str
    first_player_id: str
    turn_number: int = 1
    phase: Phase = Phase.START
    play_by_play: List[Dict] = field(default_factory=list)
    game_log: List[str] = field(default_factory=list)
```

**Key Methods:**
- `get_active_player()` - Returns Player object for current turn
- `get_opponent(player_id)` - Returns opponent Player object
- `get_card_controller(card)` - **⚠️ Searches in_play lists, doesn't use card.controller field**
- `find_card_by_name(name)` - **⚠️ Returns first match across all zones (problematic)**
- `change_control(card, new_controller)` - Used by Twist effect

### State Persistence

**Current:** PostgreSQL with in-memory caching

```python
# game_service.py
class GameService:
    def __init__(self):
        self.games: Dict[str, GameEngine] = {}  # In-memory cache
    
    def get_game(self, game_id: str) -> Optional[GameEngine]:
        # Check cache first
        if game_id in self.games:
            return self.games[game_id]
        
        # Load from database if not cached
        game_state = self._load_game_from_db(game_id)
        if game_state:
            self.games[game_id] = GameEngine(game_state)
            return self.games[game_id]
```

**Benefits:**
- ✅ Games persist across server restarts
- ✅ Production-ready persistence layer
- ✅ Two-tier caching (memory + database)
- ✅ JSONB storage for flexible schema

**Database Schema (PostgreSQL):**
```sql
-- Implemented schema
CREATE TABLE games (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    player1_id VARCHAR NOT NULL,
    player1_name VARCHAR NOT NULL,
    player2_id VARCHAR NOT NULL,
    player2_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL,  -- 'active', 'completed', 'abandoned'
    winner_id VARCHAR,
    turn_number INTEGER DEFAULT 1,
    active_player_id VARCHAR NOT NULL,
    phase VARCHAR NOT NULL,
    game_state JSONB NOT NULL  -- Complete serialized GameState
);

-- Indexes for common queries
CREATE INDEX idx_games_player1 ON games(player1_id);
CREATE INDEX idx_games_player2 ON games(player2_id);
CREATE INDEX idx_games_status ON games(status);
CREATE INDEX idx_games_updated_at ON games(updated_at DESC);
```

**See Also:** `docs/development/archive/POSTGRES_IMPLEMENTATION.md` for implementation details.

### Turn Flow

```
START PHASE
├── Gain CC (2 on turn 1, 4 after)
├── Check state-based actions
└── Transition to MAIN

MAIN PHASE
├── Player can:
│   ├── Play cards (pay CC)
│   ├── Initiate tussles (pay CC)
│   └── End turn
└── Check state-based actions after each action

END PHASE
├── Reset turn counters
├── Switch active player
├── Increment turn number
└── Transition back to START (new game)
```

**Implemented in:** `turn_manager.py` and `game_engine.py`

### State-Based Actions

Checked after every game action:

1. **Sleep cards with 0 stamina** - Cards reduced to 0 stamina go to sleep zone
2. **Trigger "when sleeped" effects** - Snuggles, Umbruh
3. **Check victory conditions** - Opponent has no cards in hand and no cards in play

**Where:** `game_engine.check_state_based_actions()`

---

## Card Lifecycle

### Card States (Zones)

```python
class Zone(Enum):
    HAND = "hand"
    IN_PLAY = "in_play"
    SLEEP = "sleep"
```

### Card Data Model

```python
@dataclass
class Card:
    # Static properties (from CSV)
    name: str
    card_type: CardType  # TOY or ACTION
    cost: int
    effect_text: str
    speed: Optional[int]
    strength: Optional[int]
    stamina: Optional[int]
    
    # Ownership & Control
    owner: str = ""           # ⚠️ Player ID who owns card (original deck)
    controller: str = ""      # ⚠️ Player ID who controls card (can change via Twist)
    
    # Current state
    zone: Zone = Zone.HAND
    current_stamina: Optional[int] = None
    modifications: Dict[str, int] = field(default_factory=dict)
```

**⚠️ Critical Issue:** `controller` field is not always kept in sync with `in_play` lists!

### Card Movement

#### Creation (Deck Building)

```python
# game_service.py -> _create_deck()
card = Card(
    name=template.name,
    # ... other fields
    owner=owner_id,
    controller=owner_id,  # Initially same as owner
)
```

**Starting zone:** HAND

#### Playing a Card

**TOY Cards:**
```python
# game_engine.py -> play_card()
card.zone = Zone.IN_PLAY
card.controller = player.player_id  # ✅ FIX: Set controller when entering play
player.in_play.append(card)
```

**ACTION Cards:**
```python
# game_engine.py -> play_card()
engine._resolve_action_card(card, player, **kwargs)
card.zone = Zone.SLEEP
player.sleep_zone.append(card)
```

#### Sleeping a Card

```python
# game_state.py -> sleep_card()
if was_in_play:
    player.in_play.remove(card)
card.zone = Zone.SLEEP
player.sleep_zone.append(card)
# Trigger "when sleeped" effects
```

#### Unsleping a Card (Wake effect)

```python
# game_state.py -> unsleep_card()
player.sleep_zone.remove(card)
card.zone = Zone.HAND
player.hand.append(card)
```

#### Control Change (Twist effect)

```python
# game_state.py -> change_control()
old_controller.in_play.remove(card)
card.controller = new_controller.player_id
new_controller.in_play.append(card)
```

**⚠️ Key Issue:** Ownership vs Control
- `card.owner` never changes (used when card leaves play)
- `card.controller` changes with Twist
- **Problem:** Some code uses `card.controller`, some uses `get_card_controller()` which searches lists

---

## Target Selection System

### Frontend Flow

1. **User clicks "Play Card"** on action card requiring targets
2. **Frontend checks** if card requires targets (hardcoded per card name)
3. **Target Selection Modal** appears with available targets
4. **User selects target(s)** from filtered list
5. **API request sent** with `target_card_name` or `target_card_names`

### Frontend Target Filtering

```typescript
// GameBoard.tsx -> getAvailableTargets()
const getAvailableTargets = (actionName: string): Card[] => {
  if (actionName === 'Wake') {
    return gameState.players[playerId].sleep_zone;
  }
  if (actionName === 'Copy') {
    return gameState.players[playerId].in_play;
  }
  if (actionName === 'Sun' || actionName === 'Twist') {
    const opponentId = // ... find opponent
    return gameState.players[opponentId].in_play;
  }
  // ... etc
};
```

**⚠️ Issue:** Zone filtering logic duplicated in backend and frontend.

### Backend Target Resolution

```python
# routes_actions.py -> play_card endpoint
if request.target_card_name:
    # Zone-specific search to avoid duplicate names
    if card.name == "Twist":
        opponent = game_state.get_opponent(player.player_id)
        target = next((c for c in opponent.in_play 
                      if c.name == request.target_card_name), None)
    elif card.name == "Wake":
        target = next((c for c in player.sleep_zone 
                      if c.name == request.target_card_name), None)
    # ... etc
```

**⚠️ Critical Problem:** Matching by `name` fails when multiple cards have same name in different zones!

**Example Bug Scenario:**
- Player has Ka in hand
- Opponent has Ka in play
- Player plays Twist targeting opponent's Ka
- `find_card_by_name("Ka")` returns player's Ka from hand (wrong!)
- Twist effect fails because target.controller is player, not opponent

**Current Workaround:** Zone-specific searching (implemented Nov 20, 2025)

**Proper Solution:** Use unique card IDs instead of names

### Effect Target Validation

```python
class PlayEffect:
    def requires_targets(self) -> bool:
        """Override to return True if effect needs targets."""
        return False
    
    def get_valid_targets(self, game_state: "GameState") -> List["Card"]:
        """Override to return list of valid target cards."""
        return []
```

**Used by:** AI player to determine valid actions

---

## API Layer

### Endpoint Categories

**Game Management** (`routes_games.py`):
- `POST /games` - Create new game
- `GET /games/{game_id}` - Get game state
- `GET /games/{game_id}/logs` - Get debug logs (for development)
- `POST /games/narrative` - Generate bedtime story narrative

**Game Actions** (`routes_actions.py`):
- `POST /games/{game_id}/play-card` - Play card from hand
- `POST /games/{game_id}/tussle` - Initiate tussle
- `POST /games/{game_id}/end-turn` - End current turn
- `POST /games/{game_id}/ai-turn` - AI takes turn (auto-selects action)
- `GET /games/{game_id}/valid-actions` - Get available actions for current player

### Request/Response Flow

**Example: Play Twist Card**

```
Frontend Request:
POST /games/{game_id}/play-card
{
  "player_id": "alice",
  "card_name": "Twist",
  "target_card_name": "Ka"
}

Backend Processing:
1. Find player by player_id
2. Find Twist card in player.hand
3. Calculate cost (check for cost modifications)
4. Find target card (zone-specific search)
5. Validate can_play_card (enough CC, right phase, etc.)
6. Execute play_card:
   - Remove from hand
   - Resolve effect (TwistEffect.apply)
   - Move to sleep zone
7. Check state-based actions
8. Update play-by-play log

Frontend Response:
{
  "success": true,
  "message": "Successfully played Twist (took control of Ka)",
  "game_state": { "turn": 2, "phase": "Main" }
}
```

### State Serialization

**Backend → Frontend:**

```python
# routes_games.py -> get_game_state()
return GameStateResponse(
    game_id=game_id,
    turn=game_state.turn_number,
    phase=game_state.phase.value,
    active_player_id=game_state.active_player_id,
    players={
        p_id: PlayerState(
            player_id=p.player_id,
            name=p.name,
            cc=p.cc,
            hand_count=len(p.hand),
            hand=cards if reveal_hand else None,
            in_play=[_card_to_state(c) for c in p.in_play],
            sleep_zone=[_card_to_state(c) for c in p.sleep_zone]
        )
        for p_id, p in game_state.players.items()
    },
    play_by_play=game_state.play_by_play
)
```

**⚠️ Issue:** Full state sent on every request (no delta updates)

---

## Frontend Architecture

For a high-level tour of the frontend codebase and how it
integrates with the backend, see `FRONTEND_OVERVIEW.md` in this
folder.

### State Management

**React Query** for server state:
```typescript
// useGame.ts
const { data: gameState } = useQuery({
  queryKey: ['game', gameId, playerId],
  queryFn: () => gameService.getGameState(gameId, playerId),
  refetchInterval: 1000  // Poll every second
});
```

**Local React state** for UI:
- Selected card
- Target selection modal state
- Card hover preview

### Component Hierarchy

```
App
└── GameBoard
    ├── PlayerZone (opponent)
    │   ├── PlayerInfoBar
    │   ├── InPlayZone
    │   └── SleepZoneDisplay
    ├── PlayerZone (current player)
    │   ├── PlayerInfoBar
    │   ├── InPlayZone
    │   ├── SleepZoneDisplay
    │   └── HandZone
    ├── ActionPanel
    ├── TargetSelectionModal
    ├── CardHoverPreview
    ├── LoadingScreen
    └── VictoryScreen
```

### Card Rendering

```typescript
<CardDisplay
  card={card}
  onClick={() => handleCardClick(card)}
  isSelected={selectedCard?.name === card.name}
  effectiveStats={calculateEffectiveStats(card)}
/>
```

**⚠️ Issue:** Card selection uses `card.name` for matching (should use ID)

---

## Frontend Design System

The GGLTCG frontend uses a comprehensive design system to ensure visual consistency and maintainability.

### Spacing Design System

All spacing uses CSS custom properties (design tokens) defined in `frontend/src/index.css`:

| Token | Value | Usage |
|-------|-------|-------|
| `--spacing-component-xs` | 8px | Tight spacing (buttons, compact cards) |
| `--spacing-component-sm` | 12px | Compact spacing (mobile, card padding) |
| `--spacing-component-md` | 16px | Standard spacing (most components) |
| `--spacing-component-lg` | 24px | Generous spacing (panels, modals) |
| `--spacing-component-xl` | 32px | Large spacing (page sections) |

**Usage:**
```tsx
<div style={{ padding: 'var(--spacing-component-md)' }}>
<div style={{ gap: 'var(--spacing-component-sm)' }}>
```

**Rule:** NEVER use hardcoded pixel values or Tailwind spacing utilities (`p-4`, `gap-2`) for component spacing.

See: `.github/instructions/coding.instructions.md` for complete standards.

### Typography Design System

Typography follows WCAG AA accessibility standards:

| Element | Classes | Example |
|---------|---------|---------|
| H1 | `text-4xl font-bold text-white` | Victory screen |
| H2 | `text-2xl font-bold text-game-highlight` | Panel titles |
| Body | `text-base text-white` | Content |
| Secondary | `text-sm text-gray-300` | Descriptions |
| Muted | `text-xs text-gray-400` | Metadata |

**Fonts:**
- **Bangers:** Headings, card names, game branding
- **Lato:** Body text, labels, UI text

See: `docs/development/TYPOGRAPHY_DESIGN_SYSTEM.md` for complete documentation.

### Responsive Strategy

The `useResponsive` hook provides consistent breakpoint detection:

```tsx
const { isDesktop, isTablet, isMobile, isLandscape } = useResponsive();
```

**Breakpoints:**
- **Desktop:** ≥1024px - Full 2-column layout
- **Tablet:** 768-1023px - Compact spacing, side-by-side zones
- **Mobile:** <768px - Stacked layout, scrollable

### Component Patterns

**Unified Components:**
- `Button` - Consistent button variants (primary, secondary, danger)
- `Modal` - Accessible modal wrapper with focus trap

**Zone Layout (Desktop):**
```
┌─────────────────────────────────────┬──────────────┐
│  Opponent InPlay  │  Opponent Sleep │              │
│─────────────────────────────────────│   Messages   │
│  My InPlay        │  My Sleep       │   + Actions  │
│─────────────────────────────────────│   (350px)    │
│            My Hand (full-width)     │              │
└─────────────────────────────────────┴──────────────┘
```

---

## Known Issues & Technical Debt

### ~~Critical Issues~~ ✅ RESOLVED

1. ~~**Code Duplication Between AI and Human Player Paths**~~ ✅ RESOLVED (Nov 21, 2025)
   - **Solution Implemented:** Created `ActionValidator` and `ActionExecutor` classes
   - **Result:** 
     - ~457 lines of duplication eliminated
     - Single source of truth for validation (`ActionValidator`)
     - Single source of truth for execution (`ActionExecutor`)
     - Both human and AI paths use identical logic
     - Bugs only need to be fixed once
   - **Files Created:**
     - `/backend/src/game_engine/validation/action_validator.py` (372 lines)
     - `/backend/src/game_engine/validation/action_executor.py` (420 lines)
   - **Files Refactored:**
     - `/backend/src/api/routes_actions.py` (880 → 523 lines, -357 lines)
   - **Status:** Complete and validated with full game playthrough

2. ~~**Complex and Ambiguous Function Arguments**~~ ✅ PARTIALLY RESOLVED (Nov 21, 2025)
   - **Solution Implemented:** 
     - Created structured action types in `/backend/src/game_engine/models/actions.py`
     - ActionExecutor uses explicit parameters instead of kwargs
     - All target and cost handling consolidated in executor
   - **Remaining Work:**
     - Consider updating `game_engine.play_card()` signature to accept action objects
     - Could further type-safe the internal game engine methods
   - **Status:** Significantly improved, further improvements optional

### Critical Issues 🔴

1. **Card Identification by Name (Partially Resolved)**
   - **Problem:** Multiple cards with same name can cause targeting bugs
   - **Current Solution:** Unique card IDs implemented, zone-specific searching
   - **Status:** Working reliably in production
   - **Future Improvement:** Use IDs throughout frontend API calls

### High Priority Issues 🟡

4. **Target Filtering Logic Duplication**
   - Target filtering logic in both frontend and backend
   - Cost calculation partially duplicated
   - Valid action checking scattered across multiple files

5. **Effect Registration is Manual**
   - Easy to forget to register effects
   - No compile-time checking
   - Hard to discover which effects exist

6. ~~**AI Can't Handle Targets**~~ ✅ FIXED (Nov 20, 2025)
   - ~~AI doesn't select targets for Sun, Twist, Wake, Copy~~
   - ~~AI doesn't decide on Ballaber alternative cost~~
   - **Status:** AI now successfully selects targets and alternative costs

### Medium Priority Issues 🟢

8. **No Card ID in Frontend**
   - Frontend uses card names for keys (`key={card.name}`)
   - Causes React warnings when duplicates exist

9. **Hardcoded Card Names**
   - Special handling for Copy, Twist, Wake hardcoded in routes
   - Should use effect metadata

10. **No Game History**
    - Can't replay games
    - Can't undo moves (for development)
    - No statistics accumulated to support game and card development

---

## Migration Considerations

### Database Schema Evolution

**Current Implementation (Phase 1):** ✅ Complete
- Two-tier caching (in-memory + PostgreSQL)
- Serialized GameState in JSONB column
- Denormalized metadata for efficient queries
- Survives server restarts

**Potential Future Enhancements (Phase 2):**
- Normalize schema into separate tables
- Add action logging to `game_actions` table
- Populate `game_stats` table for leaderboards
- Enable event sourcing for replay capability

**See:** `docs/development/archive/POSTGRES_IMPLEMENTATION.md` for implementation details.

### Card ID Migration Strategy

**Step 1: Add UUID to Card Model**
```python
@dataclass
class Card:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    # ... rest of fields
```

**Step 2: Update All Card Matching**
- Replace `find_card_by_name()` with `find_card_by_id()`
- Update API schemas to accept card IDs
- Update frontend to send card IDs

**Step 3: Update Frontend**
- Use `card.id` for React keys
- Send card IDs in API requests
- Remove zone-specific workarounds

### Multiplayer Migration Strategy

**Requirements:**
- WebSocket for real-time updates
- Player authentication
- Matchmaking system
- Game lobbies

**Architecture Change:**
```
Current:  Client → HTTP → Game Service
Future:   Client → WebSocket → Game Room → Game Service
```

---

## Recommendations

### Immediate (Before Adding Features)

1. **✅ Document architecture** (this document)
2. **Implement unique card IDs**
   - Highest impact/effort ratio
   - Fixes critical bug class
   - Prerequisite for database migration

3. **Consolidate target selection logic**
   - Single source of truth for valid targets
   - Use effect metadata instead of hardcoded names

### Short Term

1. **Add integration tests**
   - Test full game flows
   - Test all card effects
   - Regression protection

2. **Complete data-driven effect migration**
   - Migrate remaining cards from legacy effects
   - Improve effect factory with better error handling
   - Document effect string syntax

### Medium Term (Future Enhancements)

1. **Normalize database schema**
   - Separate tables for structured queries
   - Enable advanced analytics
   - Optimize for leaderboards

2. **Add WebSocket support** (for online multiplayer)
   - Real-time state updates
   - Reduce polling overhead
   - Foundation for 1v1 online play

---

## Glossary

**CC (Command Counters):** Currency for playing cards and initiating tussles  
**Sleep Zone:** Where cards go when defeated or slept  
**In Play:** Active toys that can tussle  
**Controller:** Player who currently controls a card (can change via Twist)  
**Owner:** Player whose deck the card came from (never changes)  
**Effect:** Card behavior (continuous, triggered, activated, or play)  
**State-Based Action:** Automatic game rule check (sleep 0-stamina cards, check victory)

---

**Document End**

*This document will be updated as the architecture evolves. Please keep it in sync with code changes.*
