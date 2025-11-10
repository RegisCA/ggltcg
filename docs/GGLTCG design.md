<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# I want to create an app to support the Googooland TCG (GGLTCG) game my son designed. Here are my requirements and roadmap thoughts. Help me structure those ideas so that we can start defining requirements, tech stack, etc.

1) The game is defined with "GGLTCG-Rules-v1_1.md" for the rules and "GGLTCG-cards-18starterpack.csv" for card details.
2) We have tested the game with several LLM models using  "GGLTCG game starting prompt v0_3.md" as the prompt, proving that the game works and the game mechanics are sound and well codified. 
3)The app will eventually have 3 main UIs: 
3a) a responsive web UI for human players to play against an AI player (that's what we want to start with)
3b) an admin UI to manage the card sets (currently just 18 cards, but designed to be extended over time)
3c) An admin UI to setup simulations, to run a number of automated games and generate statistics based on cards used, player to take 1st turn, etc.
3) From an architecture and tech stack perspective, I would like:
4a) I want to be able to develop the application entirely with GitHub Copilot. [https://github.com/RegisCA/portodash](https://github.com/RegisCA/portodash) is a good showcase of what I'm capable of doing.
4b) A clean, easy, and satisfying user interface to play the game against an AI player. The UX should be consistent with the themes of the game. 
4c) At some point we will provide graphics for the cards. They are currently hand drawn (poker card format), so we’ll have to figure that out.
4d) The card definitions can probably stay in a csv file rather than in a database.
4e) Eventually we’d like to track players and detailed statistics (to identify winning strategies and potential game imbalances)
4f) The rules should be translated into easily readable Python code. It should be easy to audit how tussles are resolves for example.
4g) Currently the rules document contain card details, as a way to explain the mechanics of the effect. We need a design for this, so that we have a clear process to add a new card to the game for example (add it to the CSV, but also needing to write new Python code to handle effects?)
4) From a process perspective, I want to act as a product owner, and treat this as a software development might be handled by a SaaS startup (those are the tools and processes I'm most familiar with). I want to start with an MVP by creating a clear "seed" prompt in GitHub Copilot (using Claude Sonnet 4.5) that gets us a simple application able to facilitate a one-player game (which we were able to do through an AI chat).

Based on your game documentation and requirements, here's a comprehensive structure for building the Googooland TCG app.[^1]

## MVP Scope Definition

Your MVP should focus on delivering a playable single-player experience against an AI opponent through a web interface. The core MVP includes game state management, rule enforcement, and basic AI decision-making capabilities.[^1]

### Core MVP Features

- **Game Engine**: Python-based rules implementation with complete tussle resolution logic
- **Web UI**: React-based responsive interface for card selection, game play, and state visualization
- **AI Player**: LLM-powered opponent using game prompt (Claude Sonnet 4.5 via Anthropic API)
- **State Management**: Track all three zones (Hand, In Play, Sleep), CC counts, and turn phases
- **Victory Condition**: Automatic win detection when opponent's cards are all sleeped


## Technical Architecture

### Recommended Tech Stack

**Backend (Game Engine)**

- **Language**: Python 3.11+
- **Framework**: FastAPI (lightweight, async support, excellent GitHub Copilot support)
- **Data Storage**: CSV file for cards + JSON files for game states/history
- **AI Integration**: Anthropic SDK for Claude Sonnet 4.5

**Frontend (Player Interface)**

- **Framework**: React with Vite (fast development, Copilot-friendly)
- **Styling**: Tailwind CSS (rapid prototyping, theme customization)
- **State Management**: React Context API or Zustand (lightweight)
- **Communication**: REST API calls to FastAPI backend

**Development Tools**

- **Version Control**: Git/GitHub
- **IDE**: VS Code with GitHub Copilot
- **Testing**: pytest for backend, Vitest for frontend (future phase)


### Architecture Pattern

Use a **Model-View-Controller (MVC)** approach adapted for web:

1. **Model Layer** (Python): Core game logic, card definitions, rule enforcement
2. **Controller Layer** (FastAPI): API endpoints, game state management, AI orchestration
3. **View Layer** (React): UI rendering, player interactions, game visualization

## System Design Structure

### Backend Components

**Core Modules** (`/backend/src/`)

```
game_engine/
├── models/
│   ├── card.py          # Card class with stats, effects
│   ├── player.py        # Player state (zones, CC)
│   ├── game_state.py    # Complete game state tracking
│   └── zones.py         # Zone management (Hand, InPlay, Sleep)
│
├── rules/
│   ├── turn_manager.py     # Phase management (Start/Main/End)
│   ├── cost_calculator.py  # CC costs, reductions, caps
│   ├── tussle_resolver.py  # Combat resolution logic
│   ├── effect_handler.py   # Card effect implementations
│   └── validators.py       # Action validation, legal move checking
│
├── ai/
│   ├── llm_player.py       # AI decision making via Claude
│   ├── prompt_builder.py   # Dynamic prompt generation from game state
│   └── action_parser.py    # Parse AI responses into game actions
│
└── data/
    ├── card_loader.py      # CSV parsing and card initialization
    └── game_history.py     # Save/load game states (future)
```

**API Layer** (`/backend/api/`)

```
routes/
├── game.py          # POST /game/new, GET /game/{id}
├── actions.py       # POST /game/{id}/play-card, /tussle, /end-turn
└── state.py         # GET /game/{id}/state
```


### Frontend Components

**UI Structure** (`/frontend/src/`)

```
components/
├── GameBoard.jsx        # Main game container
├── PlayerZone.jsx       # Shows zones (Hand/InPlay/Sleep)
├── CardDisplay.jsx      # Individual card rendering
├── ActionPanel.jsx      # Play card/Tussle/End turn controls
├── TussleModal.jsx      # Target selection for tussles
├── GameLog.jsx          # Action history display
└── ResourceDisplay.jsx  # CC counter

utils/
├── api.js              # API client functions
└── gameHelpers.js      # UI state calculations
```


## Data Model Design

### Card Representation

The CSV structure works well for the MVP. In Python, create a `Card` class:[^1]

```python
@dataclass
class Card:
    name: str
    card_type: str  # 'Toy' or 'Action'
    cost: int | str  # str for '?' (Copy)
    effect: str
    speed: int | None
    strength: int | None
    stamina: int | None
    
    # Runtime properties
    current_stamina: int | None = None
    damage_taken: int = 0
    zone: str = 'deck'  # 'hand', 'in_play', 'sleep'
    owner: str = None
    controller: str = None
```


### Effect Implementation Pattern

Rather than storing card mechanics in the CSV, implement a **plugin-based effect system**:[^1]

```python
class EffectRegistry:
    """Maps card names to effect handlers"""
    
    @staticmethod
    def get_handler(card_name: str):
        handlers = {
            'Knight': KnightEffect(),
            'Beary': BearyEffect(),
            'Wizard': WizardEffect(),
            # ... etc
        }
        return handlers.get(card_name)
```

Each effect is a separate class implementing standard interfaces:

- `ContinuousEffect` (Ka, Wizard, Demideca)
- `TriggeredEffect` (Beary, Umbruh, Snuggles)
- `ActivatedEffect` (Archer)
- `PlayEffect` (Action cards)

This allows you to:

1. Add cards by creating new effect classes
2. Audit logic by reviewing individual effect implementations
3. Test effects in isolation

## Development Roadmap

### Phase 1: MVP Foundation (Weeks 1-2)

**Week 1: Core Engine**

- Set up project structure (backend/frontend separation)
- Implement card loading from CSV
- Build basic game state classes (Player, GameState, Zone)
- Create turn manager with phase progression
- Implement CC system (gain, spend, cap at 7)

**Week 2: Rules \& UI**

- Build tussle resolution engine (speed calculation, strike order, damage)
- Implement card playing logic with cost validation
- Create basic React UI showing game state
- Build FastAPI endpoints for game initialization and actions
- Integrate LLM for AI decision-making (using your game prompt)


### Phase 2: Complete Gameplay (Weeks 3-4)

**Week 3: Effect System**

- Implement all 18 card effects as separate handlers
- Add effect registry and lookup system
- Build state-based action checking (zero stamina, win condition)
- Implement special mechanics (Copy, Direct Attack, Unsleep)

**Week 4: Polish \& Testing**

- Enhance UI with card animations and visual feedback
- Add game log/history display
- Manual testing of all card interactions
- Bug fixes and edge case handling


### Phase 3: Admin UI - Card Management (Week 5)

- Create admin interface for viewing/editing card CSV
- Add card validation rules
- Build effect template/documentation system
- Implement card testing sandbox


### Phase 4: Simulation System (Weeks 6-7)

- Design simulation configuration (deck compositions, first player, iterations)
- Build headless game runner (no UI)
- Implement statistics collection (win rates, card usage, turn counts)
- Create results dashboard/reporting


## GitHub Copilot Development Strategy

### Seed Prompt Structure

Create a comprehensive seed prompt in your repository's root as `COPILOT_CONTEXT.md`:

````markdown
# GGLTCG Development Context

## Project Overview
We are building a web application for the Googooland TCG (GGLTCG), a two-player tactical card game with no randomness in draws. The game is fully codified in rules and currently supports 18 unique cards.

## Core Game Rules Summary
[Include Quick Rules Summary from your rules doc]

## Technical Stack
- Backend: Python 3.11+ with FastAPI
- Frontend: React with Vite and Tailwind CSS
- AI Player: Claude Sonnet 4.5 via Anthropic API
- Data: CSV for cards, JSON for game states

## Architecture Principles
1. Separate game logic (Python) from presentation (React)
2. Plugin-based effect system for card mechanics
3. RESTful API communication
4. State immutability where possible
5. Clear separation between card data (CSV) and card logic (Python classes)

## Development Guidelines
- All card effects must be implemented as separate classes in /backend/src/game_engine/rules/effects/
- Game state must be serializable to JSON for API transport
- UI components should be functional React components with hooks
- Use TypeScript for frontend type safety
- Follow Python type hints for all backend code

## Current Implementation Status
[Update as you progress]

## Next Tasks
[Maintain a prioritized list]
```

### Copilot Usage Pattern

When starting a coding session:

1. **Context Setting**: Reference your rules document and current task
2. **Function-Level Prompts**: Write clear docstrings describing what you want
3. **Test-Driven Suggestions**: Ask Copilot to generate test cases first
4. **Iterative Refinement**: Use Copilot chat to refactor and improve generated code

Example Copilot prompt in code:

```python
def resolve_tussle(attacker: Card, defender: Card, 
                   active_player: Player, game_state: GameState) -> TussleResult:
    """
    Resolve a tussle between two Toy cards following GGLTCG rules.
    
    Rules:
    1. Calculate effective speed (base + modifiers + turn bonus for active player)
    2. Determine strike order (higher speed first, tied = simultaneous)
    3. Apply damage (strength reduces stamina)
    4. Check for sleep condition (stamina <= 0)
    5. Handle special cases (Knight auto-win on active turn, Beary immunity)
    
    Args:
        attacker: The attacking Toy card
        defender: The defending Toy card
        active_player: Player whose turn it is (for turn bonus)
        game_state: Current game state for continuous effects
        
    Returns:
        TussleResult containing outcome, damage dealt, and cards sleeped
    """
    # Copilot will generate the implementation
```

## Critical Design Decisions

### Card Effect Extensibility

**Problem**: How to add new cards without hardcoding logic everywhere[^1]

**Solution**: Effect registration pattern

1. Card CSV contains only data (stats, cost, effect text for display)
2. Each card with special mechanics has a corresponding Python class
3. Effect classes implement standard interfaces (`apply()`, `can_activate()`, `cleanup()`)
4. Registry maps card names to effect handlers

**Adding a New Card Process**:
1. Add row to CSV with card data
2. Create effect class in `/effects/` if card has special mechanics
3. Register effect in `effect_registry.py`
4. Write unit test for effect behavior
5. Update card pool in UI

### AI Player Integration

**Approach**: Use your existing LLM prompt as the AI "brain"[^1]

```python
class LLMPlayer:
    def __init__(self, model="claude-sonnet-4.5"):
        self.client = anthropic.Anthropic()
        self.model = model
        
    def get_action(self, game_state: GameState, player_id: str) -> Action:
        """
        Generate AI decision by:
        1. Build prompt from game state (cards in zones, CC, etc)
        2. Include game rules and card details
        3. Request specific action format from LLM
        4. Parse response into Action object
        """
        prompt = self._build_prompt(game_state, player_id)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return self._parse_action(response.content)
```

The prompt should include:
- Current game state (all zones, CC counts)
- Available actions (playable cards, possible tussles)
- Game rules reminder
- Request for structured output (JSON format for easy parsing)

### UI Theme & Card Graphics

**MVP Approach**:
- Use card data (name, stats, effect text) to generate simple card visuals
- Create CSS-based card layout with distinct styling for Toys vs Actions
- Color-code by stats (high speed = blue, high strength = red, etc.)

**Future Enhancement**:
- When hand-drawn graphics are ready, store as image files (e.g., `/assets/cards/{card_name}.png`)
- Update `CardDisplay.jsx` to show images instead of generated cards
- Keep stats/text as overlay or back-face for accessibility

### Statistics & Analytics Design

**Data to Track** (Phase 4):
- Game-level: Winner, turns to win, first player advantage
- Card-level: Play rate, win rate when played, average turns in play
- Interaction-level: Tussle outcomes, card synergies

**Storage Approach**:
- Save complete game history as JSON files
- Run batch analysis with pandas/numpy
- Generate reports with visualization (matplotlib/plotly)

**Key Metrics**:
1. **Balance**: Card win rates should cluster around 50%
2. **First Player Advantage**: Should be minimal given CC adjustment
3. **Dominant Strategies**: Identify overpowered card combinations
4. **Underused Cards**: Find cards that need buffs or clearer use cases

## Requirements Documentation

### Functional Requirements (MVP)

**Game Setup**
- FR-1: System shall load 18 cards from CSV on initialization
- FR-2: Each player shall select 6 unique cards from the pool
- FR-3: System shall randomly determine first player
- FR-4: Starting player begins with 2 CC, second player with 0 CC

**Turn Management**
- FR-5: Active player shall gain 4 CC at turn start (2 on Turn 1 for first player)
- FR-6: CC shall be capped at maximum 7 per player
- FR-7: Player shall be able to play cards, initiate tussles, and activate abilities during main phase
- FR-8: Unspent CC shall be banked for next turn (subject to cap)

**Card Playing**
- FR-9: System shall validate sufficient CC before allowing card play
- FR-10: Toy cards shall enter In Play zone when played
- FR-11: Action cards shall resolve effect then move to Sleep zone

**Tussle System**
- FR-12: System shall calculate effective speed including turn bonus and continuous effects
- FR-13: Higher speed Toy shall strike first; tied speed strikes simultaneously
- FR-14: Toy reduced to 0 or less stamina shall be sleeped immediately
- FR-15: Direct attacks (vs no defenders) shall sleep random card from opponent hand, max twice per turn

**Victory Condition**
- FR-16: Game shall end immediately when all opponent cards are in Sleep zone

**AI Player**
- FR-17: AI shall make legal moves within game rules
- FR-18: AI shall use LLM (Claude Sonnet 4.5) for decision-making
- FR-19: AI response time shall be reasonable (<10 seconds per action)

### Non-Functional Requirements

**Performance**
- NFR-1: Game state updates shall render in UI within 500ms
- NFR-2: API response time for actions shall be <1 second (excluding AI thinking time)

**Usability**
- NFR-3: UI shall be responsive and playable on desktop browsers (1920x1080 minimum)
- NFR-4: All game actions shall provide visual feedback
- NFR-5: Game state shall be clearly visible (zones, CC, cards)

**Maintainability**
- NFR-6: Code shall follow PEP 8 (Python) and Airbnb style guide (React)
- NFR-7: All functions shall have type hints and docstrings
- NFR-8: Card effects shall be modular and independently testable

**Extensibility**
- NFR-9: Adding new cards shall require only CSV update and effect class (if special mechanics)
- NFR-10: System shall support future features (multiplayer, animations, card graphics)

## Success Metrics for MVP

1. **Functional Completeness**: All 18 cards work correctly with proper effect resolution
2. **AI Quality**: AI player makes legal, strategically reasonable moves 90%+ of the time
3. **Playability**: Human player can complete full game against AI without bugs
4. **Development Speed**: GitHub Copilot assistance enables solo development within 4-6 weeks
5. **Code Quality**: Codebase is maintainable with clear separation of concerns

## Next Steps

1. **Immediate**: Create GitHub repository with folder structure
2. **This Week**: 
   - Set up FastAPI backend skeleton
   - Implement card loader from CSV
   - Create basic game state classes
3. **Copilot Seed Prompt**: Copy the COPILOT_CONTEXT.md template above into your repo
4. **First Feature**: Build turn manager and CC system (simplest rules to validate architecture)
5. **First UI**: Create simple React app that displays game state from API

This structure provides a clear path from your current design documents to a working application, leveraging GitHub Copilot throughout while maintaining professional software development practices. The modular architecture allows you to build incrementally and validate each component before moving to the next.[^1]
<span style="display:none">[^2][^3][^4]</span>

<div align="center">⁂</div>

[^1]: image.jpg
[^2]: GGLTCG-Rules-v1_1.md
[^3]: GGLTCG-game-starting-prompt-v0_3.md
[^4]: GGLTCG-cards-18starterpack.csv````

