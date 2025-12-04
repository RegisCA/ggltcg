---
applyTo: '*'
description: "Comprehensive coding standards, architecture principles, and development best practices for GGLTCG"
---

# GGLTCG Coding Standards & Best Practices

## Core Architecture Principles

### 1. ID-Based Lookups (NEVER Use Names)

**CRITICAL**: Always use unique card IDs for lookups, NEVER use card names.

**Why**: Multiple cards can have the same name in different zones. Name-based lookups cause bugs when targeting/finding cards.

**✅ CORRECT**:
```python
# Backend
card = game_state.find_card_by_id(card_id)
target = game_state.find_card_by_id(target_id)

# API Request
{
  "card_id": "uuid-1234-5678",
  "target_id": "uuid-9876-5432"
}
```

**❌ WRONG**:
```python
# Backend
card = next((c for c in cards if c.name == "Ka"), None)  # NEVER DO THIS

# API Request
{
  "card_name": "Ka",  # WRONG
  "target_card_name": "Knight"  # WRONG
}
```

**Exceptions**: NONE. Even Knight/Beary interactions use effect types, not names.

### 2. Method-Based State Modification (NEVER Direct Assignment)

**CRITICAL**: Always use proper methods to modify card state. NEVER assign to attributes directly.

**Why**: Direct modification bypasses game logic, stat calculations, and effect triggers.

**✅ CORRECT**:
```python
# Damage
card.apply_damage(amount)  # Updates current_stamina

# Check if defeated
if card.is_defeated():  # Checks current_stamina
    game_engine._sleep_card(card, owner, was_in_play=True)

# Healing
card.heal(amount)  # If such method exists

# Stat modifications
card.modifications["strength"] = 2  # Via effect system
```

**❌ WRONG**:
```python
# NEVER modify stats directly
card.stamina -= 1  # Modifies base stat, not current!
card.strength = 5  # Bypasses effect calculations!
card.speed += 1  # Wrong layer of abstraction!

if card.stamina <= 0:  # Checks wrong attribute!
    sleep_card()
```

**Exceptions**: Initial card creation in constructors/factories only.

### 3. GameEngine vs GameState Separation

**Architecture Rule**: GameState is pure data, GameEngine contains all game logic.

**GameState** (Data Container):
- Stores current game state (players, turn, phase, etc.)
- Provides data access methods (get_active_player, find_card_by_id, etc.)
- NO game logic, NO effect triggering, NO cost calculations

**GameEngine** (Logic Orchestrator):
- All game rules and mechanics
- Effect triggering and resolution
- Cost calculations
- Victory condition checking
- Turn management

**✅ CORRECT**:
```python
# Call GameEngine methods that trigger effects
game_engine._sleep_card(card, owner, was_in_play=True)
game_engine.play_card(player, card, target_ids=[target.id])

# Use GameState for data access only
player = game_state.get_active_player()
cards = game_state.get_cards_in_play(player)
```

**❌ WRONG**:
```python
# Don't call GameState methods that should trigger effects
game_state.sleep_card(card, was_in_play=True)  # Bypasses when-sleeped effects!

# Don't put game logic in GameState
if game_state.calculate_cost(card):  # Logic belongs in GameEngine!
    ...
```

**When to use which**:
- Need to trigger effects? → `game_engine`
- Need to access data? → `game_state`
- Unsure? → Use `game_engine` (it will use `game_state` internally)

### 3.1 Owner vs Controller (Stolen Cards)

**CRITICAL**: Understand the difference between `card.owner` and `card.controller`.

| Property | Meaning | Changes? |
|----------|---------|----------|
| `owner` | Original card owner | NEVER changes |
| `controller` | Who currently controls the card | Changes via Twist |

**Key Rules**:
- Cards always sleep to **owner's** sleep zone
- "Your cards" effects check **controller**, not owner
- When sleeping a stolen card, remove from **controller's** `in_play`, add to **owner's** `sleep_zone`

**✅ CORRECT** (in `_sleep_card`):
```python
controller = game_state.players.get(card.controller)
owner = game_state.players.get(card.owner)

if controller != owner:
    # Stolen card - remove from controller's zone
    controller.in_play.remove(card)
    # Add to owner's sleep zone
    owner.sleep_zone.append(card)
```

### 3.2 Tussle Prediction (Single Source of Truth)

**RESOLVED**: Tussle logic is now consolidated in GameEngine with these key methods:

| Method | Purpose |
|--------|---------|
| `_execute_tussle()` | Actual tussle execution with side effects |
| `predict_tussle_winner()` | AI prediction (returns "attacker"/"defender"/"tie") |
| `get_effective_stamina()` | Get stamina with continuous effects applied |
| `is_card_defeated()` | Check if card should be sleeped |

All tussle-related logic lives in `game_engine.py`. The duplicate `TussleResolver` class has been removed.

### 4. Effect System - Data-Driven First

**Pattern**: Use data-driven CSV effect definitions. Only create custom effect classes for truly unique mechanics.

**Data-Driven (Preferred)**:
```csv
name,type,cost,effect_definitions,...
Ka,Toy,1,stat_boost:strength:2,...
Rush,Action,0,gain_cc:2:not_first_turn,...
Clean,Action,0,sleep_all,...
```

**Custom Effect Class (Only if necessary)**:
```python
class CopyEffect(PlayEffect):
    """Complex dynamic behavior that can't be parameterized."""
    def apply(self, game_state, **kwargs):
        # Custom logic here
        ...
```

**Migration Status** (56% complete - 10/18 cards data-driven):
- ✅ Data-driven: Ka, Demideca, Rush, Wake, Sun, Clean, Wizard, Dream, Umbruh, Raggy
- 🔧 Custom (keep): Knight, Beary, Copy, Twist, Toynado, Ballaber, Archer
- ❌ Remove: No legacy classes remain (RushEffect, CleanEffect deleted)

**Effect Type Checking**:
```python
# Use isinstance() to check effect types
if isinstance(effect, PlayEffect):
    ...
if isinstance(effect, ContinuousEffect):
    ...
if isinstance(effect, ActivatedEffect):
    ...
```

### 5. Testing Best Practices

**Unit Tests** (`backend/tests/test_*.py`):
- Test individual components in isolation
- Fast, focused, repeatable
- Use pytest framework
- Mock external dependencies

**Integration Tests**:
- Test full game flows
- Test all card effects with real game state
- Verify frontend-backend contracts

**Debug Scripts** (debugging only, not committed):
- Temporary `check_*.py` scripts for debugging
- Delete after fixing the bug
- Don't commit to repository

**Running Tests**:
```bash
# All tests
pytest backend/tests/

# Specific test file
pytest backend/tests/test_game_engine.py

# Specific test
pytest backend/tests/test_game_engine.py::test_play_card

# With coverage
pytest --cov=backend/src backend/tests/
```

**Test Organization**:
- Keep all tests in `backend/tests/`
- Name test files `test_<module>.py`
- One test file per module being tested
- Group related tests in classes

### 6. Frontend-Backend Contracts

**API Requests Use IDs**:
```typescript
// TypeScript API types
interface PlayCardRequest {
  player_id: string;
  card_id: string;  // NOT card_name
  target_ids?: string[];  // NOT target_card_names
  alternative_cost_card_id?: string;  // NOT card name
}
```

**Route Consistency**:
- Frontend: `/games/{game_id}/activate-ability`
- Backend: Must match exactly
- Use OpenAPI/Swagger for documentation

**Response Format**:
```typescript
interface GameStateResponse {
  game_id: string;
  turn: number;
  phase: "Start" | "Main" | "End";
  active_player_id: string;
  players: Record<string, PlayerState>;
  play_by_play: PlayByPlayEntry[];
}
```

## Local Development Environment

### Backend Setup

```bash
# Activate virtual environment
cd /Users/regis/Projects/ggltcg
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run server
cd backend
python run_server.py

# Server runs on: http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Frontend Setup

```bash
cd /Users/regis/Projects/ggltcg/frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Frontend runs on: http://localhost:5173
```

### Testing a Full Game

**Quick Start Script** (human vs AI):
1. Start backend server
2. Start frontend dev server
3. Open browser to `http://localhost:5173`
4. Click "Start Game"
5. Play as player 1, AI plays as player 2

**Testing Specific Cards**:
1. Modify `backend/data/cards.csv` if needed
2. Restart backend server
3. Start new game to load updated cards

**Common Test Scenarios**:
- Play various card combinations
- Test targeting (Wake, Sun, Twist, Copy)
- Test tussles with stat modifiers (Ka, Demideca)
- Test protection effects (Knight immunity)
- Test activated abilities (Archer)

## Code Quality Standards

### Python

**Style**: PEP 8 with line length 100
```python
# Use type hints
def play_card(
    player: Player,
    card: Card,
    target_ids: Optional[List[str]] = None
) -> None:
    ...

# Use dataclasses for data structures
@dataclass
class ValidAction:
    action_type: str
    card_id: str
    target_options: Optional[List[str]] = None
```

**Imports**:
```python
# Standard library
import os
from typing import List, Optional

# Third-party
from fastapi import APIRouter

# Local
from ..models.card import Card
from ..models.game_state import GameState
```

**Logging**:
```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed info for debugging")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

### TypeScript/React

**Style**: Airbnb with Prettier
```typescript
// Use interfaces for props
interface CardDisplayProps {
  card: Card;
  onClick?: () => void;
  isSelected?: boolean;
}

// Use functional components
export const CardDisplay: React.FC<CardDisplayProps> = ({
  card,
  onClick,
  isSelected = false
}) => {
  // Component logic
  return (...)
};
```

**React Query Hooks**:
```typescript
const { data: gameState } = useQuery({
  queryKey: ['game', gameId],
  queryFn: () => gameService.getGameState(gameId),
  refetchInterval: 1000  // Poll for updates
});
```

### Frontend Spacing Design System

**CRITICAL**: ALWAYS use spacing design tokens, NEVER hardcode spacing values.

**Spacing Tokens** (defined in `frontend/src/index.css`):
```css
@theme {
  --spacing-component-xs: 8px;   /* Tight spacing within components */
  --spacing-component-sm: 12px;  /* Standard component padding */
  --spacing-component-md: 16px;  /* Default content spacing */
  --spacing-component-lg: 24px;  /* Section separation */
  --spacing-component-xl: 32px;  /* Major layout spacing */
}
```

**Utility Classes**:
- `.panel-padding` - Standard panel padding (md)
- `.modal-padding` - Modal content padding (lg)
- `.card-padding` - Card component padding (sm)
- `.content-spacing` - Content element gaps (md)

**✅ CORRECT Usage**:
```tsx
// Use design tokens in inline styles
<div style={{ padding: 'var(--spacing-component-md)' }}>
  <div style={{ gap: 'var(--spacing-component-sm)' }}>
    Content
  </div>
</div>

// Use utility classes
<div className="panel-padding">
  <div className="content-spacing">
    Content
  </div>
</div>

// Use in styled components
const Container = styled.div`
  padding: var(--spacing-component-lg);
  gap: var(--spacing-component-md);
`;
```

**❌ WRONG Usage**:
```tsx
// NEVER hardcode spacing values
<div style={{ padding: '16px' }}>  // BAD!
<div className="p-4">  // BAD! (Tailwind utility)
<div style={{ gap: '12px' }}>  // BAD!
```

**Exceptions**: NONE. All spacing must use design tokens for consistency and maintainability.

**Responsive Spacing**:
```tsx
// Use design tokens with responsive conditionals
const spacing = isMobile 
  ? 'var(--spacing-component-xs)' 
  : 'var(--spacing-component-md)';

<div style={{ padding: spacing }}>
```

**Layout Patterns**:

**GameBoard Layout** (Desktop):
```tsx
// 2-column grid: game zones | messages+actions
<div className="grid" style={{ 
  gap: 'var(--spacing-component-sm)', 
  gridTemplateColumns: '1fr 350px' 
}}>
  <div className="space-y-3">
    {/* Left: Opponent zones, player zones, hand */}
  </div>
  <div className="space-y-3">
    {/* Right: Messages + Actions (350px fixed) */}
  </div>
</div>
```

**Zone Organization**:
- Each player's zones displayed side-by-side (InPlay + Sleep)
- Clear visual divider between opponent and player zones
- Hand positioned full-width below player's zones only
- Messages + Actions always visible on right side

## Common Patterns & Anti-Patterns

### ✅ Good Patterns

**1. Structured Actions**:
```python
@dataclass
class PlayCardAction:
    action_type: ActionType
    player_id: str
    card_id: str
    target_ids: List[str] = field(default_factory=list)
```

**2. Single Source of Truth**:
```python
# ActionValidator - one place for all validation
# ActionExecutor - one place for all execution
# Both AI and human use the same code paths
```

**3. Effect Metadata**:
```python
class PlayEffect:
    def requires_targets(self) -> bool:
        return True
    
    def get_valid_targets(self, game_state) -> List[Card]:
        return [...]  # Effect defines its own targets
```

### ❌ Anti-Patterns

**1. Magic Strings**:
```python
# BAD
if action_type == "play_card":
    ...

# GOOD
if action.action_type == ActionType.PLAY_CARD:
    ...
```

**2. Code Duplication**:
```python
# BAD - same logic in multiple places
def ai_play_card(...):
    # Check effects
    # Build description
    # Execute action

def human_play_card(...):
    # Same checks (duplicated!)
    # Same description logic (duplicated!)
    # Same execution (duplicated!)

# GOOD - shared logic
def play_card(action: PlayCardAction):
    ActionValidator.validate(action)
    ActionExecutor.execute(action)
```

**3. Hardcoded Card Names**:
```python
# BAD
if card.name == "Wake":
    # Special handling

# GOOD
effects = EffectRegistry.get_effects(card)
for effect in effects:
    if isinstance(effect, UnsleepEffect):
        # Handle based on effect type
```

## Security Considerations

### Input Validation

**Always validate API inputs**:
```python
# Validate UUIDs
if not is_valid_uuid(card_id):
    raise ValueError("Invalid card ID")

# Validate player owns card
if card not in player.hand:
    raise ValueError("Card not in player's hand")

# Validate targets are legal
if target not in effect.get_valid_targets(game_state):
    raise ValueError("Invalid target")
```

### OWASP Compliance

Follow all rules in `security-and-owasp.instructions.md`:
- No SQL injection (use parameterized queries when DB added)
- No XSS (sanitize user input)
- Validate all incoming data
- Use HTTPS in production
- Never hardcode secrets

## Documentation Standards

### Code Comments

**When to comment**:
- Complex algorithms that aren't self-explanatory
- Non-obvious design decisions
- Workarounds for known issues (with issue number)

**When NOT to comment**:
- Self-explanatory code
- What the code does (code should be readable)

**Good comment**:
```python
# FIX (Issue #70): Check protection before applying effect
# Knight has opponent_immunity which prevents Clean from sleeping it
if game_state.is_protected_from_effect(card, self):
    continue
```

**Bad comment**:
```python
# Loop through cards  ← Obvious from code
for card in cards:
    ...
```

### Docstrings

**Required for**:
- All public functions/methods
- All classes
- All modules

**Format**:
```python
def apply_damage(self, amount: int) -> None:
    """
    Apply damage to this card, reducing current stamina.
    
    Damage reduces current_stamina, not base stamina.
    If current_stamina reaches 0, card should be sleeped.
    
    Args:
        amount: Amount of damage to apply (positive integer)
        
    Raises:
        ValueError: If amount is negative
    """
    if amount < 0:
        raise ValueError("Damage amount must be non-negative")
    
    self.current_stamina = max(0, self.current_stamina - amount)
```

## Deployment

### Production Checklist

**Before deploying**:
- [ ] All tests pass (`pytest backend/tests/`)
- [ ] No TypeScript errors (`npm run build`)
- [ ] No console errors in browser
- [ ] API documentation updated
- [ ] Environment variables configured
- [ ] Database migrations applied (when DB added)

**Deployment Process** (see `bot-workflow.instructions.md`):
- Backend deploys to Render on merge to `main`
- Frontend deploys to Vercel on merge to `main`
- **CRITICAL**: Test thoroughly before merging to `main`!

## Git Workflow

### Branch Naming

```bash
feature/card-name-implementation  # New feature
fix/bug-description               # Bug fix
refactor/component-name           # Code refactoring
chore/update-dependencies         # Maintenance
```

### Commit Messages

```
feat: Add Archer activated ability
fix: Prevent direct stat modification in effects
refactor: Consolidate validation logic in ActionValidator
docs: Update architecture documentation
test: Add tests for UnsleepEffect
chore: Update dependencies
```

### Pull Requests

**Use regisca-bot for automated PRs** (see `bot-workflow.instructions.md`):
```bash
# Ensure regisca-bot is active account
gh auth status

# Create PR as bot
gh pr create --title "..." --body "..." --base main --head feature-branch
```

## Troubleshooting

### Common Issues

**Issue**: "Card not found by ID"
- Check that IDs are being passed, not names
- Verify card exists in the specified zone
- Check serialization/deserialization preserves IDs

**Issue**: "Card shows wrong stats (e.g., 1/2 instead of 2/4)"
- Direct stat modification detected
- Use `apply_damage()` instead of `card.stamina -= amount`
- Check `current_stamina` not `stamina`

**Issue**: "Effect doesn't trigger"
- Verify effect is in card's `effect_definitions` CSV field
- Check GameEngine is being used, not GameState
- Verify effect type (PlayEffect, TriggeredEffect, etc.)

**Issue**: "AI makes illegal moves"
- Check `prompts.py` card descriptions are accurate
- Verify `ActionValidator` returns correct valid actions
- Ensure AI sees buffed stats, not base stats

### Debug Endpoints

```bash
# Get full game state (when implemented)
GET /games/{game_id}/debug

# Get game logs
GET /games/{game_id}/logs

# Get valid actions for player
GET /games/{game_id}/valid-actions?player_id={id}
```

## Resources

### Internal Documentation

- `docs/GGLTCG design.md` - Original game design
- `docs/rules/GGLTCG Rules v1_1.md` - Game rules
- `docs/development/ARCHITECTURE.md` - System architecture
- `docs/development/EFFECT_SYSTEM_ARCHITECTURE.md` - Effect system design
- `docs/development/archive/` - Historical session notes

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Pytest Documentation](https://docs.pytest.org/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)

---

## Quick Reference

**Starting a game**:
1. `source .venv/bin/activate`
2. `cd backend && python run_server.py`
3. (New terminal) `cd frontend && npm run dev`
4. Open `http://localhost:5173`

**Running tests**:
```bash
pytest backend/tests/
```

**Making changes**:
1. Create feature branch
2. Make changes following these guidelines
3. Test manually + run pytest
4. Create PR using regisca-bot if automated
5. Review and merge to main

**Remember**:
- IDs not names
- Methods not direct assignment
- GameEngine for logic, GameState for data
- Data-driven effects when possible
- Test before deploying
