# GGLTCG Project - MVP Progress

## Project Created: November 10, 2025

### ✅ Completed Tasks

#### 1. Project Structure
- Created complete directory structure for backend and frontend
- Set up documentation folders with game rules and design docs
- Configured .gitignore for Python and Node.js
- Created README.md with project overview and roadmap

#### 2. Backend Foundation
**Core Models:**
- `Card` model with full stat tracking, zone management, and modifications
- `Player` model with CC management, three zones (Hand, In Play, Sleep)
- `GameState` model with turn tracking, phase management, and game log
- Proper serialization/deserialization for API transport

**Data Loading:**
- `CardLoader` to parse cards.csv file
- Support for 18 unique cards including Toys and Actions
- Handles special cases (Copy's variable cost, Dream's reduction)

**Game Rules:**
- `TurnManager` for phase progression and CC system
  - Gain 4 CC per turn (2 on Turn 1 for first player)
  - CC banking with 7 CC maximum cap
  - Turn bonus calculations
  - Cost modifiers (Dream, Wizard, Raggy)
  
- `TussleResolver` for combat resolution
  - Speed calculation with turn bonus (+1 for active player)
  - Strike order determination (first strike, simultaneous)
  - Damage application and sleep checking
  - Direct attacks when opponent has no Toys in play
  - Knight's auto-win ability (except vs Beary)
  - Continuous effects (Ka +2 Strength, Demideca +1 all stats)

#### 3. Documentation
- `COPILOT_CONTEXT.md` - Comprehensive development guide for GitHub Copilot
- Copied all game rules and design documents to `docs/` folder
- Created test file to verify card loading works

### 🚧 Next Steps (In Priority Order)

#### Phase 1: Complete Backend (Week 1-2)
1. **Effect System** - Create base effect classes and registry
   - `ContinuousEffect` (Ka, Wizard, Demideca)
   - `TriggeredEffect` (Beary, Umbruh, Snuggles)
   - `ActivatedEffect` (Archer)
   - `PlayEffect` (All Action cards)
   - Effect registry to map card names to handlers

2. **Game Engine** - Complete game logic
   - Card playing validation and resolution
   - Effect application and tracking
   - State-based actions (sleep defeated Toys, check victory)
   - Special card mechanics (Copy, Twist, Ballaber)

3. **FastAPI Endpoints** - Create REST API
   - `POST /api/game/new` - Initialize new game
   - `GET /api/game/{id}` - Get current state
   - `POST /api/game/{id}/play` - Play a card
   - `POST /api/game/{id}/tussle` - Initiate tussle
   - `POST /api/game/{id}/activate` - Activate ability (Archer)
   - `POST /api/game/{id}/end-turn` - End current turn

4. **AI Player** - Integrate Claude Sonnet 4.5
   - Prompt builder to create game state description
   - Action parser to interpret LLM responses
   - LLM player that makes decisions for AI opponent

#### Phase 2: Frontend (Week 2-3)
1. **React Setup**
   - Initialize Vite project
   - Configure Tailwind CSS
   - Set up API client utilities

2. **UI Components**
   - GameBoard - Main container
   - PlayerZone - Show zones (Hand/In Play/Sleep)
   - CardDisplay - Individual card rendering
   - ActionPanel - Play/Tussle/End Turn controls
   - GameLog - Event history
   - ResourceDisplay - CC counter

3. **Game Flow**
   - Card selection for deck building
   - Turn-by-turn gameplay
   - Tussle target selection
   - Victory screen

#### Phase 3: Testing & Polish (Week 3-4)
1. **Testing**
   - Unit tests for all effects
   - Integration tests for game flows
   - Manual testing of all card interactions

2. **Polish**
   - Card animations
   - Visual feedback for actions
   - Improved UI/UX

### 📊 Project Statistics

**Files Created:** 20+
- Backend models: 4 files
- Game rules: 2 files  
- Data handling: 2 files
- Configuration: 3 files
- Documentation: 4 files

**Lines of Code:** ~1,500+ (backend only)

**Cards Supported:** 18/18
- 13 Toys (with stats)
- 5 Actions (effects only)

**Game Mechanics Implemented:**
- ✅ CC system with banking (max 7)
- ✅ Turn structure (Start/Main/End)
- ✅ Tussle resolution with speed/strength/stamina
- ✅ Direct attacks
- ✅ Zone management
- ✅ Continuous effects (Ka, Wizard, Demideca)
- ⏳ Card effects (18 to implement)
- ⏳ Triggered abilities
- ⏳ Special mechanics

### 🎯 MVP Goals

**Target:** Playable single-player game vs AI in 4-6 weeks

**Current Progress:** ~25% complete (Foundation solid!)

**What's Working:**
- Card data loading from CSV ✅
- Game state management ✅
- Turn progression ✅
- Tussle mechanics ✅
- CC system with banking ✅

**What's Next:**
1. Implement all 18 card effects
2. Create FastAPI endpoints
3. Build React UI
4. Integrate AI player

### 🛠️ How to Test Current Progress

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
python tests/test_card_loader.py
```

This will verify that:
- Card CSV parsing works correctly
- All 18 cards load properly
- Toy and Action cards are differentiated
- Special cost handling works (Copy, Dream)

### 📝 Development Notes

**Key Design Decisions Made:**
1. **Effect System:** Plugin-based with separate classes per card effect
2. **State Management:** Immutable-friendly with clear serialization
3. **CC Banking:** Implemented with 7 CC maximum cap as per rules v1.1
4. **Tussle Resolution:** Complete implementation with all modifiers
5. **API Design:** RESTful with JSON state transport

**GitHub Copilot Usage:**
- Used for code generation with clear docstrings
- Leveraging COPILOT_CONTEXT.md for project context
- Following Python type hints and best practices

**Next Copilot Session Focus:**
- Effect system architecture
- Individual card effect implementations
- FastAPI route handlers
