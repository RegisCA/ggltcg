# GGLTCG Architecture Documentation

**Version:** 1.0  
**Date:** November 20, 2025  
**Status:** Current implementation (feat/complete-card-effects branch)

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
9. [Known Issues & Technical Debt](#known-issues--technical-debt)
10. [Migration Considerations](#migration-considerations)

---

## System Overview

### Technology Stack

**Backend:**
- FastAPI (Python 3.13+)
- Uvicorn (ASGI server)
- In-memory game state (temporary - will migrate to PostgreSQL)

**Frontend:**
- React 19.2
- TypeScript 5.9
- Vite 7.2
- TanStack Query (React Query)
- Tailwind CSS 4.1

**AI Integration:**
- Google Gemini API (primary and fallback endpoints)

### Architecture Pattern

**Current:** Monolithic backend with RESTful API  
**Future:** Will need to support WebSocket for real-time 1v1 multiplayer

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
│   │   ├── schemas.py         # Pydantic models for API
│   │   └── game_service.py    # In-memory game storage (singleton)
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
│       │   └── player.py     # Player data model
│       └── rules/
│           ├── turn_manager.py
│           ├── tussle_resolver.py
│           └── effects/       # Card effects system
│               ├── base_effect.py
│               ├── action_effects.py
│               ├── triggered_effects.py
│               ├── continuous_effects.py
│               └── effect_registry.py
```

### Separation of Concerns

**✅ Well Separated:**
- API layer (`api/`) cleanly separated from game logic (`game_engine/`)
- Effect types properly abstracted (base classes)
- Turn management isolated in `turn_manager.py`

**⚠️ Needs Improvement:**
- Game service is singleton with in-memory dict (not scalable)
- Some game logic leaks into API routes (cost calculation, special card handling)
- Card searching logic scattered across multiple files

---

## Effects System

The effects system is the core of card behavior. It uses inheritance and polymorphism to handle different effect types.

### Effect Type Hierarchy

```
BaseEffect (abstract)
├── ContinuousEffect
│   └── CostModificationEffect
│       ├── DreamCostEffect
│       └── WizardCostEffect
├── TriggeredEffect
│   ├── SnugglesWhenPlayedEffect
│   ├── SnugglesWhenSleepedEffect
│   └── UmbruhEffect
├── PlayEffect
│   ├── WakeEffect
│   ├── SunEffect
│   ├── TwistEffect
│   ├── CopyEffect
│   └── RushEffect
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

### Effect Examples

#### Simple PlayEffect: Wake

```python
class WakeEffect(PlayEffect):
    """Wake: Unsleep a card from your Sleep Zone."""
    
    def requires_targets(self) -> bool:
        return True
    
    def get_valid_targets(self, game_state: "GameState") -> List["Card"]:
        player = game_state.get_active_player()
        return player.sleep_zone if player else []
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        target = kwargs.get("target")
        player = kwargs.get("player")
        if target and player and target in player.sleep_zone:
            game_state.unsleep_card(target, player)
```

**Flow:**
1. Player plays Wake from hand
2. Frontend shows target selection modal
3. Player selects target from their sleep zone
4. API receives play request with `target_card_name`
5. API finds target card (zone-specific search)
6. `WakeEffect.apply()` called with target
7. Card moved from sleep_zone to hand

#### Complex PlayEffect: Twist

```python
class TwistEffect(PlayEffect):
    """Twist: Take control of opponent's card in play."""
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        target = kwargs.get("target")
        player = kwargs.get("player")
        
        # Verify target is opponent's card
        opponent = game_state.get_opponent(player.player_id)
        target_controller = game_state.get_card_controller(target)
        
        if target_controller != opponent:
            return
        
        # Transfer control
        game_state.change_control(target, player)
```

**Key Point:** `change_control()` updates both:
- Card's `controller` field
- Player's `in_play` lists (remove from old, add to new)

#### CostModificationEffect: Dream

```python
class DreamCostEffect(CostModificationEffect):
    """Dream: Costs 1 less per sleeping card you have."""
    
    def modify_card_cost(self, card: "Card", base_cost: int, 
                        game_state: "GameState", controller: "Player") -> int:
        if card != self.source_card:
            return base_cost
        
        sleeping_count = len(controller.sleep_zone)
        reduction = min(sleeping_count, base_cost)
        return base_cost - reduction
```

**Execution:** Called in `calculate_card_cost()` before player pays CC.

#### TriggeredEffect: Snuggles

```python
class SnugglesWhenSleepedEffect(TriggeredEffect):
    """Snuggles: When sleeped, may sleep a card in play."""
    
    def __init__(self, source_card: "Card"):
        super().__init__(source_card, TriggerTiming.WHEN_SLEEPED, is_optional=True)
    
    def should_trigger(self, game_state: "GameState", **kwargs: Any) -> bool:
        sleeped_card = kwargs.get("sleeped_card")
        return sleeped_card == self.source_card
```

**Execution:** Called in `sleep_card()` after card is moved to sleep zone.

### Effect Registry Pattern

**Purpose:** Decouple effect definitions from card data.

**Benefits:**
- Cards can be loaded from CSV without Python code
- Effects can be reused across multiple cards
- Testing effects independently from cards

**Limitations:**
- ⚠️ Effect registration is manual (must remember to register)
- ⚠️ No validation that CSV references existing effects
- ⚠️ Hard to see which cards have which effects

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

**Current:** In-memory only
```python
# game_service.py
class GameService:
    def __init__(self):
        self.games: Dict[str, GameEngine] = {}  # game_id -> GameEngine
```

**Issues:**
- ❌ Server restart loses all games
- ❌ Not scalable (single process only)
- ❌ No game history or replay capability

**Future (PostgreSQL):**
```sql
-- Proposed schema
CREATE TABLE games (
    id UUID PRIMARY KEY,
    state JSONB NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE game_events (
    id SERIAL PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    event_type VARCHAR(50),
    event_data JSONB,
    timestamp TIMESTAMP
);
```

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

## Known Issues & Technical Debt

### Critical Issues 🔴

1. **Code Duplication Between AI and Human Player Paths**
   - **Problem:** Three separate code paths for action execution:
     1. Human player: `play_card` endpoint (lines 53-250 in routes_actions.py)
     2. AI player: `ai_take_turn` endpoint (lines 555-950 in routes_actions.py)
     3. Valid actions generation: `get_valid_actions` endpoint (lines 252-553)
   - **Symptoms:**
     - Effect checking logic duplicated in 2 places (valid actions + AI turn)
     - Target validation duplicated
     - Description building duplicated
     - Cost calculation duplicated
     - When bugs are fixed in one path, they remain in others
   - **Impact:** High maintenance burden, inconsistent behavior, bugs in one path don't appear in others
   - **Solution:** Create unified `ActionExecutor` and `ActionValidator` classes used by both paths
   - **Identified:** November 20, 2025 debugging session

2. **Complex and Ambiguous Function Arguments**
   - **Problem:** Functions pass around complex sets of loosely-typed arguments
   - **Example:**

     ```python
     engine.play_card(player, card, 
         target=card_obj,           # Sometimes present, sometimes not
         target_name=str,           # Why both target and target_name?
         targets=list,              # Plural version for Sun card
         alternative_cost_paid=bool,
         alternative_cost_card=str, # Wait, this is a name not a card?
         **kwargs                   # More unknown args
     )
     ```

   - **Symptoms:**
     - Hard to know what arguments are required for each card
     - Mixing card objects and card names
     - Kwargs make it unclear what's being passed
     - Easy to forget required arguments (e.g., "target not passed to engine" bug)
   - **Impact:** Bugs like target not passed, confusion about card references, difficult to refactor
   - **Solution:** Use structured action objects (dataclasses) with explicit, typed fields
   - **Identified:** November 20, 2025 debugging session

3. **Card Identification by Name**
   - **Problem:** Multiple cards with same name cause targeting bugs
   - **Impact:** Twist, Wake, Copy can target wrong card
   - **Workaround:** Zone-specific searching (temporary fix)
   - **Solution:** Implement unique card IDs
   - **Status:** Partially addressed with unique IDs (Nov 20), but still using names in some places

4. **In-Memory Game State**
   - **Problem:** Server restart loses all games
   - **Impact:** Not production-ready
   - **Solution:** PostgreSQL persistence layer

5. **Inconsistent Controller Tracking**
   - **Problem:** `card.controller` field vs `get_card_controller()` search
   - **Impact:** Twist effect initially broken
   - **Solution:** Always set `card.controller` when entering play
   - **Status:** Fixed Nov 20, 2025

### High Priority Issues 🟡

6. **Target Filtering Logic Duplication**
   - Target filtering logic in both frontend and backend
   - Cost calculation partially duplicated
   - Valid action checking scattered across multiple files

7. **No WebSocket Support**
   - Polling every second is inefficient
   - Needed for real-time multiplayer
   - Adds latency

8. **Effect Registration is Manual**
   - Easy to forget to register effects
   - No compile-time checking
   - Hard to discover which effects exist

9. ~~**AI Can't Handle Targets**~~ ✅ FIXED (Nov 20, 2025)
   - ~~AI doesn't select targets for Sun, Twist, Wake, Copy~~
   - ~~AI doesn't decide on Ballaber alternative cost~~
   - **Status:** AI now successfully selects targets and alternative costs

### Medium Priority Issues 🟢

10. **No Card ID in Frontend**
    - Frontend uses card names for keys (`key={card.name}`)
    - Causes React warnings when duplicates exist

11. **Hardcoded Card Names**
    - Special handling for Copy, Twist, Wake hardcoded in routes
    - Should use effect metadata

12. **No Game History**
    - Can't replay games
    - Can't undo moves (for development)
    - No statistics accumulated to support game and card development

---

## Migration Considerations

### Database Migration Strategy

**Phase 1: Add Persistence (Minimal Changes)**
- Keep current in-memory structure
- Serialize GameEngine to JSON
- Store in PostgreSQL JSONB column
- Load on server restart

**Phase 2: Normalize Schema**
- Separate tables for games, players, cards, events
- Use proper foreign keys
- Enable queries (leaderboards, statistics)

**Phase 3: Event Sourcing (Optional)**
- Store game events instead of state snapshots
- Rebuild state by replaying events
- Enables time-travel debugging

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

### Short Term (Before Database)

4. **Add integration tests**
   - Test full game flows
   - Test all card effects
   - Regression protection

5. **Refactor game service**
   - Abstract storage interface
   - Makes DB migration easier

### Medium Term (Before Multiplayer)

6. **Add WebSocket support**
   - Real-time state updates
   - Foundation for multiplayer

7. **Implement AI target selection**
   - AI can use all cards
   - Better testing coverage

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
