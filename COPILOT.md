# GGLTCG Architectural Decisions

**Purpose**: Quick reference to key architectural decisions and their rationale  
**Audience**: GitHub Copilot agents working on this codebase  
**Last Updated**: January 6, 2026

---

## Core Architecture

### ID-Based Lookups Only

**Decision**: Use `card.id` for all lookups, NEVER `card.name`

**Rationale**: Multiple cards can have the same name in different zones. Name-based lookups cause targeting bugs.

**Implementation**:
- `GameState.find_card_by_id(card_id)` is the only lookup method
- All targeting uses card IDs
- Card loader generates unique IDs immediately when loading from CSV

**Exception**: NONE

---

### Method-Based State Modification

**Decision**: Always use methods to modify card state, NEVER direct attribute assignment

**Rationale**: Direct modification bypasses game logic, stat calculations, and effect triggers. The current_stats vs base_stats distinction requires method-based updates.

**Implementation**:
- Damage: `card.apply_damage(amount)` → updates `current_stamina`
- Defeat check: `card.is_defeated()` → checks `current_stamina`
- Stat mods: `card.modifications["strength"] = 2` via effect system

**Exception**: NONE

---

### GameEngine for Logic, GameState for Data

**Decision**: `GameEngine` contains all game logic, `GameState` is pure data

**Rationale**:
- Clear separation of concerns
- GameState is serializable for database storage
- Multiple GameEngines can operate on same GameState (used in simulations)

**Implementation**:
\`\`\`python
# ✅ CORRECT
engine = GameEngine(game_state)
engine.play_card(player, card)

# ❌ WRONG
game_state.play_card(card)  # GameState shouldn't have logic
\`\`\`

---

### Data-Driven Effects

**Decision**: Card effects defined in `backend/data/cards.csv`, parsed by `EffectRegistry`

**Rationale**:
- New cards can be added without code changes
- Effects are testable in isolation
- CSV format is human-readable and maintainable

**Implementation**:
- CSV file: `backend/data/cards.csv`
- Parser: `backend/src/game_engine/effects/effect_loader.py`
- See `docs/development/EFFECT_SYSTEM_ARCHITECTURE.md`

**Limitation**: Complex effects (Copy, Transform) still require code

---

## AI System

### Dual-Request Architecture (V4)

**Decision**: Request 1 generates action sequences, Request 2 selects best sequence

**Rationale**:
- Better strategic planning than single-request V3
- Separates "what's possible" from "what's optimal"
- Request 1: fast, creative sequence generation
- Request 2: slow, analytical evaluation

**Tried and rejected**:
- V3 single-request: Too reactive, poor planning
- V2 and earlier: Even worse strategic planning

**Implementation**:
- Sequence Generator: `backend/src/game_engine/ai/prompts/sequence_generator.py`
- Strategic Selector: `backend/src/game_engine/ai/prompts/strategic_selector.py`
- Orchestration: `backend/src/game_engine/ai/prompts/turn_planner.py`

**Current Status**: V4 in development. See `docs/plans/AI_V4_REMEDIATION_PLAN.md`

---

## Testing Philosophy

### Explicit Test Setup

**Decision**: Tests must explicitly set `turn_number` and `active_player`

**Rationale**: Default values caused impossible game states. Explicit values make test intent clear.

**Pattern**:
\`\`\`python
# ✅ CORRECT - explicit and valid
setup, cards = create_game_with_cards(
    player1_hand=["Ka"],
    turn_number=1,           # P1's first turn (odd = P1)
    active_player="player1",
)

# ❌ WRONG - relies on unclear defaults
setup, cards = create_game_with_cards(player1_hand=["Ka"])
\`\`\`

**Rule**: Odd turns = P1 active, Even turns = P2 active

---

### Manual + Automated AI Testing

**Decision**: Turn 1 (P1) + Turn 2 (P2) as core regression test for AI development

**Rationale**:
- Quick to run (< 1 minute)
- Covers CC mechanics, effects, tussles, direct attacks
- Real LLM responses catch prompt issues that unit tests miss

**Implementation**:
- Manual: Start game, observe Turn 1 + Turn 2 behavior
- Automated: `test_ai_turn1_and_turn2_scenario()` (planned in AI V4 Phase 2)

---

## Common Pitfalls (Don't Repeat)

### Game Mechanics Fabrication

**What happened**: Agent wrote "6 zones per player" when actual game has 3

**Prevention**: ALWAYS verify against `docs/rules/QUICK_REFERENCE.md` before writing any game mechanics

---

### Invalid Turn States in Tests

**What happened**: Tests had `turn_number=2` with `active_player="player1"` (impossible)

**Prevention**: Turn parity rule - odd turns = P1, even turns = P2. Always be explicit.

---

### Git Work Lost

**What happened**: Local commits lost when main was reset

**Prevention**: Push early and often. Use feature branches for multi-step work.

---

## Documentation Map

| Document | Purpose |
|----------|---------|
| `CONTEXT.md` | Project context, verification checklist |
| `COPILOT.md` (this file) | Architectural decisions |
| `docs/rules/QUICK_REFERENCE.md` | Game rules (authoritative) |
| `backend/BACKEND_GUIDE.md` | Backend patterns |
| `frontend/FRONTEND_GUIDE.md` | Frontend patterns |
| `docs/development/EFFECT_SYSTEM_ARCHITECTURE.md` | Effect system details |
| `docs/plans/AI_V4_REMEDIATION_PLAN.md` | AI development roadmap |
