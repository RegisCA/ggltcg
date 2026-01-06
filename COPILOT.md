# GGLTCG Project Memory

**Purpose**: Capture architectural decisions and failure learnings that persist across sessions  
**Audience**: GitHub Copilot agents working on this codebase  
**Maintenance**: Update when you learn something worth remembering  
**Last Updated**: January 6, 2026

---

## Critical Failures & Learnings

### Disaster: Lost Documentation Work (Jan 6, 2026) ⭐ MOST RECENT

**What Happened**: 15+ local commits containing docs reorganization and planning files were lost when main was reset to `origin/main`

**Root Cause**:

- Commits made locally but never pushed to remote
- `git reset --hard origin/main` discarded local work
- No feature branch to protect work-in-progress

**Files Lost**:

- `docs/development/ai/` subdirectory (reorganized AI docs)
- `docs/development/sessions/SESSION_POSTMORTEM_2026_01_05.md`
- `docs/plans/AI_V4_REMEDIATION_PLAN.md`
- `docs/plans/INSTRUCTION_FILES_MIGRATION_PLAN.md`
- `AGENTS.md` and `COPILOT.md` (root context files)
- `docs/rules/QUICK_REFERENCE.md`

**Recovery**:

- Files existed in git reflog at commit `e758c31`
- Recovered using `git show e758c31:<path> > <path>`
- Created `docs/DOCS_RESTRUCTURING_PLAN.md` documenting recovery

**Prevention Going Forward**:

- **Push early, push often** - Local-only commits can be lost
- **Use feature branches** for multi-step work
- **Check `git status` and `git log origin/main..HEAD`** before resets
- If work spans multiple sessions, push to remote even if incomplete

---

### Disaster: Fabricated Game Mechanics (Jan 5, 2026)

**What Happened**: Agent wrote "6 zones per player" in instruction file when actual game has 3 zones (Hand, In Play, Sleep Zone)

**Root Cause**:

- No verification step before writing documentation
- No requirement to check authoritative sources
- Agent made assumptions instead of reading actual rules

**Fix Applied**:

- Created `docs/rules/QUICK_REFERENCE.md` (67 lines) as authoritative source
- Rewrote `.github/instructions/ai-prompts.instructions.md` with verified-only content
- All game mechanics now quote directly from rules document

**Prevention Going Forward**:

- ALWAYS verify game mechanics against `docs/rules/QUICK_REFERENCE.md` before writing ANY code or documentation
- NEVER make assumptions about game rules - read the source
- If unclear, ask user rather than fabricating

**User Quote**: "HOW DO WE FIX THAT?!?" - This was a serious trust violation

---

### Bug: Invalid Turn Number Combinations (Jan 6, 2026)

**What Happened**: Tests had `turn_number=2` with `active_player="player1"` - an impossible game state

**Root Cause**:

- Confusing turn numbering: "Turn 2" ambiguous (game turn 2 vs player's second turn)
- Fixture defaults created invalid combinations
- 13+ test instances relied on broken assumptions

**Fix Applied**:

- Updated `backend/tests/conftest.py` defaults to `turn_number=3` (P1's second turn)
- Made all tests explicit about turn numbers (no relying on defaults)
- Clarified turn sequence documentation: P1(T1) → P2(T2) → P1(T3) → P2(T4)

**Prevention Going Forward**:

- Turn sequence is ALWAYS: P1(T1) → P2(T2) → P1(T3) → P2(T4)...
- `turn_number=1, active_player="player1"` ✅ Valid
- `turn_number=2, active_player="player2"` ✅ Valid  
- `turn_number=2, active_player="player1"` ❌ IMPOSSIBLE
- Always be explicit about turn numbers in tests - never rely on defaults

---

### Session Pattern: Disaster Recovery (Jan 5-6, 2026)

**What Happened**: January 5 session with Sonnet 4.5 introduced regressions that broke AI V4

**Root Cause**:

- Agent added `"(unless it's Turn 1)"` restriction to sequence generator
- No tests caught this regression before deployment
- Manual testing revealed broken prompt after deployment

**Fix Applied**:

- Created `docs/development/ai/AI_V4_REMEDIATION_PLAN.md` - 6 phases with quality gates
- Reset `sequence_generator.py` to last known good version
- Deleted invalid test files from disaster session
- Phase 0: Fix Turn 1 bug (pending)

**Prevention Going Forward**:

- Phase 2 of remediation plan creates automated Turn 1 + Turn 2 regression test
- Never modify AI prompts without running real game tests first
- Commit often during AI work so we have known-good restore points

---

## Architectural Decisions

### Decision: ID-Based Lookups Only

**Decision**: Use `card.id` for all lookups, NEVER `card.name`

**Rationale**:

- Multiple cards can have the same name in different zones
- Name-based lookups cause targeting bugs when there are duplicate card names
- IDs are guaranteed unique per card instance

**Tried and rejected**:

- Name-based lookups: `next((c for c in cards if c.name == "Ka"), None)` caused bugs when multiple Ka cards existed in different zones

**Implementation**:

- `GameState.find_card_by_id(card_id)` is the only lookup method
- All targeting uses card IDs
- See `backend/src/game_engine/game_state.py`

**Exceptions**:

- NONE. Even Knight/Beary interactions use effect types, not card names
- Card loader reads from CSV by name, but generates unique IDs immediately

---

### Decision: Method-Based State Modification

**Decision**: Always use proper methods to modify card state, NEVER assign to attributes directly

**Rationale**:

- Direct modification bypasses game logic, stat calculations, and effect triggers
- Current stats vs base stats distinction requires method-based updates
- Effect system needs to intercept modifications

**Tried and rejected**:

- Direct assignment: `card.stamina -= 1` modifies base stat, not current stat
- Direct assignment: `card.strength = 5` bypasses effect calculations

**Implementation**:

- Damage: `card.apply_damage(amount)` updates `current_stamina`
- Defeat check: `card.is_defeated()` checks `current_stamina`
- Stat modifications: `card.modifications["strength"] = 2` via effect system
- See `backend/src/game_engine/models/card.py`

**Exceptions**:

- NONE. All state changes go through methods

---

### Decision: Data-Driven Effects

**Decision**: Card effects defined in `backend/data/cards.csv`, parsed by `EffectRegistry`

**Rationale**:

- New cards can be added without code changes
- Effects are testable in isolation
- CSV format is human-readable and maintainable
- Supports complex multi-phase effects (Phase 1: on_play, Phase 2: tussle/cost mods)

**Tried and rejected**:

- Hard-coded effects per card: Unmaintainable, requires code changes for new cards
- JSON/YAML format: CSV is simpler for card-centric data

**Implementation**:

- CSV columns: `name,cc,strength,stamina,speed,p1_effect,p2_effect,effect_targets,description`
- Parser: `backend/src/game_engine/effects/effect_loader.py`
- Registry: `backend/src/game_engine/effects/effect_registry.py`
- See `docs/development/EFFECT_SYSTEM_ARCHITECTURE.md` for details

**Current Limitations**:

- Some complex effects still require code (Copy, Transform)
- Ongoing work to make more effects data-driven

---

### Decision: Dual-Request AI System (V4)

**Decision**: Request 1 generates action sequences, Request 2 selects best sequence

**Rationale**:

- Better strategic planning than single-request V3
- Separates "what's possible" from "what's optimal"
- Request 1 focuses on valid sequences (fast, creative)
- Request 2 focuses on strategic evaluation (slow, analytical)

**Tried and rejected**:

- V3 single-request: Too reactive, poor planning, couldn't explore alternatives
- V2 and earlier: Even worse strategic planning

**Implementation**:

- Request 1: `backend/src/game_engine/ai/prompts/sequence_generator.py`
- Request 2: `backend/src/game_engine/ai/prompts/strategic_selector.py`
- Orchestration: `backend/src/game_engine/ai/prompts/turn_planner.py`
- See `docs/development/ai/AI_V4_REMEDIATION_PLAN.md`

**Current Status**:

- V4 in development
- Phase 0 pending: Fix Turn 1 tussle restriction bug
- Phases 1-5 planned: CC waste tracking, regression tests, instruction file, prompt tests, metadata

---

### Decision: GameEngine for Logic, GameState for Data

**Decision**: `GameEngine` contains all game logic, `GameState` is pure data

**Rationale**:

- Clear separation of concerns
- GameState is serializable for database storage
- GameEngine methods can be tested without persistence
- Multiple GameEngines can operate on same GameState (for simulations)

**Implementation**:

- `GameState`: Players, cards, zones, turn number, phase
- `GameEngine`: play_card(), tussle(), apply_effects(), validate_action()
- See `backend/src/game_engine/game_engine.py` and `game_state.py`

**Pattern**:

```python
# ✅ CORRECT
engine = GameEngine(game_state)
engine.play_card(player, card)

# ❌ WRONG
game_state.play_card(card)  # GameState shouldn't have logic
```

---

## Testing Philosophy

### Decision: Manual + Automated Smoke Tests

**Decision**: Turn 1 (P1) + Turn 2 (P2) as core regression test for AI development

**Rationale**:

- Quick to run (< 1 minute)
- Covers CC mechanics, effects, tussles, direct attacks, target selection
- Real LLM responses catch prompt quality issues that unit tests miss
- Easy to reproduce manually for debugging

**Tried and rejected**:

- Pure unit tests: Don't catch prompt quality issues
- Full game simulations: Too slow for rapid iteration
- POC (proof of concept) tests: Not comprehensive enough

**Implementation**:

- Manual: Start game, observe Turn 1 + Turn 2 behavior, check `/admin/ai-logs`
- Automated (Phase 2): `test_ai_turn1_and_turn2_scenario()` in remediation plan
- See `docs/development/ai/AI_V4_REMEDIATION_PLAN.md` Phase 2

**Expected Behavior**:

- Turn 1 (P1, 2 CC + Surge, if testing with that card): Use 3 CC, sleep 1 card, waste 0 CC
- Turn 2 (P2, 4 CC): Use 4-5 CC, sleep 1-2 cards, waste 0-1 CC

---

### Decision: Explicit Test Setup (No Default Assumptions)

**Decision**: Tests must explicitly set `turn_number` and `active_player`

**Rationale**:

- Default values caused impossible game states (turn_number=2 + active_player="player1")
- Explicit values make test intent clear
- Reduces cognitive load when reading tests

**Implementation**:

- `conftest.py` fixtures have valid defaults (turn_number=3) but tests override explicitly
- Pattern:

```python
setup, cards = create_game_with_cards(
    player1_hand=["Ka"],
    player1_cc=2,
    active_player="player1",
    turn_number=1,  # Explicit: P1's first turn
)
```

**No More**:

```python
# ❌ Relying on defaults - unclear what turn this is
setup, cards = create_game_with_cards(
    player1_hand=["Ka"],
)
```

---

## Environment Facts

### Development Setup

**Local Environment**:

- **Backend**: <http://localhost:8000> (FastAPI + SQLite `backend/ggltcg.db`)
- **Frontend**: <http://localhost:5173> (Vite dev server)
- **Start backend**: `cd backend && python run_server.py`
- **Start frontend**: `cd frontend && npm run dev`
- **Python venv**: `source .venv/bin/activate` (from project root)

**Production Environment**:

- **Backend**: <https://ggltcg.onrender.com> (Render + PostgreSQL)
- **Frontend**: Vercel auto-deploy from main branch
- **Deployment**: Commits to `main` trigger automatic deployments (see bot-workflow.instructions.md)

---

### API Keys & Secrets

**Google Gemini API**:

- Location: `backend/.env` file (gitignored)
- Variable: `GOOGLE_API_KEY`
- Usage: AI player integration (dual-request V4)
- DO NOT hardcode in code

**Database**:

- Local: `backend/ggltcg.db` (SQLite, gitignored)
- Production: Render PostgreSQL (connection string in Render dashboard)
- Migrations: Alembic (see `backend/alembic/`)

---

### Git Workflow

**Two GitHub Accounts**:

1. **regisca-bot**: For automated PRs (security updates, dependency upgrades, bot-driven changes)
2. **RegisCA**: For manual work, reviews, and PR approvals

**Check active account**: `gh auth status`  
**Switch accounts**: `gh auth switch -u regisca-bot` or `gh auth switch -u RegisCA`

**PR Workflow**:

- Bot creates PR → `gh pr create` (as regisca-bot)
- Human reviews → Approve and merge (as RegisCA)
- See `.github/instructions/bot-workflow.instructions.md` for details

---

## Tech Stack

### Backend

**Core**:

- Python 3.13.7
- FastAPI (REST API)
- SQLAlchemy (ORM)
- Alembic (migrations)

**Game Engine**:

- Custom state machine with effect system
- Data-driven effects from CSV
- Serializable game state for database storage

**AI Integration**:

- Google Gemini 2.5 Flash-lite
- Dual-request architecture (V4)
- Prompt files in `backend/src/game_engine/ai/prompts/`

---

### Frontend

**Core**:

- TypeScript 5.x
- React 18
- TanStack Query (React Query) for API state management
- Vite (build tool + dev server)

**Styling**:

- CSS custom properties for design tokens
- No CSS framework (custom styles)
- See `.github/instructions/frontend-css.instructions.md`

---

### CI/CD

**Current**:

- Commits to `main` → Auto-deploy to Render (backend) + Vercel (frontend)
- No automated tests in CI yet (manual pytest before merge)

**Planned**:

- GitHub Actions for automated testing
- Snyk integration (planned but not active currently)

---

## Documentation Structure

**Authoritative Sources** (ALWAYS check these):

- `docs/rules/QUICK_REFERENCE.md` - Game rules (67 lines)
- `docs/rules/GGLTCG Rules v1_1.md` - Full rules (500+ lines)
- `backend/data/cards.csv` - Current card data
- `COPILOT.md` (this file) - Architectural decisions and learnings

**Architecture & Design**:

- `docs/development/ARCHITECTURE.md` - System architecture overview
- `docs/development/EFFECT_SYSTEM_ARCHITECTURE.md` - Effect system details
- `docs/development/ai/AI_V4_REMEDIATION_PLAN.md` - AI development roadmap

**Instructions** (for GitHub Copilot):

- `AGENTS.md` - Root context (CHECK FACTS FIRST)
- `.github/instructions/*.instructions.md` - Domain-specific patterns

---

## When Instructions Conflict

**Code is source of truth**.

If these instructions conflict with actual code:

1. ✅ Code is correct
2. ⚠️ Update COPILOT.md or AGENTS.md to match reality
3. 📝 Document WHY the pattern exists in this file

If you find a conflict, ask the user before making assumptions.

---

## Maintenance Guidelines

**Update COPILOT.md when**:

- You make an architectural decision worth remembering
- You encounter a failure that should be prevented in future
- You learn something that changes how the project should be developed
- A pattern emerges from multiple similar issues

**Update frequency**: After significant sessions or milestones, not every commit

**Keep it focused**: This is not a changelog. Capture WHY, not just WHAT.
