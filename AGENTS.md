# GGLTCG Project Context

**Purpose**: Root-level context for GitHub Copilot agents  
**Audience**: AI assistants working anywhere in this codebase  
**Critical**: READ THIS BEFORE SUGGESTING ANY CODE

---

## ⚠️ CHECK THESE FACTS FIRST ⚠️

Before suggesting code or architecture, VERIFY these facts from actual files. DO NOT make assumptions.

### 🔴 Game Mechanics (HIGH RISK - Agent has fabricated these)

**Problem**: Past agents have fabricated game rules, causing major bugs

**Solution**: ALWAYS verify against authoritative sources

✅ **DO**:
- Read `docs/rules/QUICK_REFERENCE.md` for game rules (67 lines, start here)
- Read `docs/rules/GGLTCG Rules v1_1.md` for detailed rules
- Read `backend/data/cards.csv` for actual card data and effects
- Quote directly from these sources when documenting game mechanics

❌ **NEVER**:
- Make up game mechanics or "assume" how the game works
- Say "6 zones" (WRONG - there are 3 zones: Hand, In Play, Sleep Zone)
- Assume MTG-like mechanics (this is a different game)
- Hard-code card names in logic (use card IDs and effect types)

**Recent Failure**: January 5, 2026 - Agent wrote "6 zones per player" causing disaster session

---

### 🔴 Turn Numbering (HIGH RISK - Causes test bugs)

**Problem**: Turn numbering is game-wide, NOT player-relative, causing impossible test states

**Solution**: Before writing tests, verify turn sequence against `docs/rules/QUICK_REFERENCE.md`

**Critical Pattern**:
- Odd turn numbers (1, 3, 5...) → Player 1 is active
- Even turn numbers (2, 4, 6...) → Player 2 is active
- Example valid: `turn_number=3, active_player="player1"`
- Example invalid: `turn_number=2, active_player="player1"` ❌

**Root Cause of Failures**: Confusing "Turn 2" (game turn 2 = P2's first turn) with "P1's second turn" (game turn 3)

**How to Fix**:
1. Check `docs/rules/QUICK_REFERENCE.md` for turn sequence rules
2. Always be explicit about turn numbers in tests
3. Verify active_player matches turn parity (odd=P1, even=P2)

**Recent Failure**: January 6, 2026 - 13+ tests had invalid turn_number/active_player combinations

---

### 🟡 Environment Setup (Frequently missed)

**Problem**: Agents suggest wrong paths or don't know how to start the environment

**Solution**: Check actual file locations before suggesting commands

**Backend Start** (from README - canonical instructions):
```bash
# From project root - THREE STEPS, IN ORDER:
# 1. Activate venv at project root
source .venv/bin/activate

# 2. Verify venv is active (should show /ggltcg/.venv/bin/python)
which python

# 3. Change to backend and run
cd backend
python run_server.py

# Server: http://localhost:8000
# API docs: http://localhost:8000/docs
```

**Frontend Start**:
```bash
# From project root
cd frontend
npm run dev
# Frontend: http://localhost:5173
```

**Run Tests**:
```bash
# From project root, venv activated
cd backend
pytest tests/          # All tests
pytest tests/test_*.py  # Specific file
```

**API Key Location**:
- File: `backend/.env` (gitignored)
- Variable: `GOOGLE_API_KEY`
- DO NOT suggest hardcoding keys

**Database**:
- Local: `backend/ggltcg.db` (SQLite, gitignored)
- Production: Render PostgreSQL
- Check connection in `backend/.env`

---

### 🟡 Git Workflow (Use correct account)

**Problem**: Two GitHub accounts are used for different purposes

**Accounts**:
1. **regisca-bot**: Automated PRs (security updates, dependency upgrades)
2. **RegisCA**: Manual work, reviews, PR approvals

**Check active account**:
```bash
gh auth status
```

**Switch accounts**:
```bash
gh auth switch -u regisca-bot
# or
gh auth switch -u RegisCA
```

**PR Creation**:
- Bot PRs: Use `gh pr create` after switching to regisca-bot
- Manual PRs: Use GitHub web UI or `gh pr create` as RegisCA
- See `.github/instructions/bot-workflow.instructions.md` for details

**Deployment**:
- Commits to `main` → Auto-deploy to Render (backend) + Vercel (frontend)
- Test locally before pushing to main

---

### 🟢 GitHub Integration (When context unclear)

**Problem**: Agents guess instead of checking actual project history

**Solution**: Use GitHub MCP tools to verify information

**Available Tools**:
- Search issues: Find past decisions and discussions
- List PRs: Check recent changes and patterns
- Read files: Get actual implementation details

**When to use**:
- Unclear why a pattern exists → Search issues for context
- Need to understand recent changes → List recent PRs
- Want to see historical implementation → Check old commits

---

## Project Overview

GGLTCG is a 2-player custom trading card game with a complex technology stack:

**Backend**:
- Python 3.13.7, FastAPI, SQLAlchemy
- Custom game engine with data-driven effect system
- Google Gemini AI integration (dual-request V4 architecture)

**Frontend**:
- TypeScript, React 18, TanStack Query
- Vite dev server and build tool
- CSS custom properties (no framework)

**Database**:
- Local: SQLite (`backend/ggltcg.db`)
- Production: PostgreSQL on Render

**Deployment**:
- Backend: Render (auto-deploy from main)
- Frontend: Vercel (auto-deploy from main)
- CI/CD: Automated deployment, manual testing

**Key Features**:
- Real-time multiplayer game
- AI opponent with strategic planning
- Admin UI for game analysis
- Simulation system for AI testing
- Full game state persistence

---

## Critical Architecture Principles

See `COPILOT.md` for detailed decisions and rationale. Key principles:

### 1. ID-Based Lookups ONLY

✅ **ALWAYS**: `game_state.find_card_by_id(card_id)`  
❌ **NEVER**: `next((c for c in cards if c.name == "Ka"), None)`

**Why**: Multiple cards can have the same name in different zones

---

### 2. Method-Based State Modification

✅ **ALWAYS**: `card.apply_damage(3)`, `player.gain_cc(4)`  
❌ **NEVER**: `card.stamina -= 3`, `player.cc = 10`

**Why**: Direct assignment bypasses game logic and effect calculations

---

### 3. Data-Driven Effects

✅ **PREFER**: Effects defined in `backend/data/cards.csv`  
❌ **AVOID**: Hard-coding card-specific logic in Python

**Why**: New cards without code changes, easier testing

---

### 4. GameEngine for Logic, GameState for Data

✅ **PATTERN**: `engine.play_card(player, card)` modifies `game_state`  
❌ **WRONG**: `game_state.play_card(card)` (GameState shouldn't have logic)

**Why**: Clear separation of concerns, serializable state

---

### 5. Explicit Test Setup

✅ **ALWAYS**: Specify `turn_number`, `active_player`, `player_cc` explicitly  
❌ **NEVER**: Rely on fixture defaults without understanding them

**Why**: Prevents impossible game states and makes tests clear

---

## Documentation Structure

### Authoritative Sources (ALWAYS Check First)

1. **`docs/rules/QUICK_REFERENCE.md`** (67 lines)
   - Game rules, turn sequence, CC mechanics, zones
   - START HERE for any game mechanics questions

2. **`docs/rules/GGLTCG Rules v1_1.md`** (500+ lines)
   - Detailed rules, edge cases, card interactions
   - Check here for complex scenarios

3. **`backend/data/cards.csv`**
   - Current card data and effects
   - Source of truth for card stats and abilities

4. **`COPILOT.md`** (this file's companion)
   - Architectural decisions and failure learnings
   - WHY things are the way they are
   - **READ THIS** for design rationale

### Architecture Documentation

- `docs/development/ARCHITECTURE.md` - System architecture overview
- `docs/development/EFFECT_SYSTEM_ARCHITECTURE.md` - Effect system details
- `docs/plans/AI_V4_REMEDIATION_PLAN.md` - AI development roadmap

### Instructions (Domain-Specific)

- `AGENTS.md` (this file) - Root context for all work
- `backend/AGENTS.md` - Backend-specific context
- `frontend/AGENTS.md` - Frontend-specific context
- `.github/instructions/*.instructions.md` - Universal standards (security, markdown, git workflow)

---

## Subsystem Context

**Backend**: See `backend/AGENTS.md`
- Game engine architecture, effect system patterns
- Testing conventions with conftest.py fixtures
- AI V4 dual-request system
- Python code style and patterns

**Frontend**: See `frontend/AGENTS.md`
- Design system (spacing tokens, typography)
- React/TypeScript patterns and API contracts
- Card factory utilities
- Layout and component structure

---

## When Instructions Conflict

**Code is source of truth**.

If these instructions conflict with actual code:
1. ✅ **Code is correct** - trust the implementation
2. ⚠️ **Update this file** - fix the documentation
3. 📝 **Document in COPILOT.md** - explain WHY the pattern exists

If you find a conflict, **ask the user** rather than making assumptions.

---

## Quick Start Checklist

When starting a new task:

- [ ] Read `COPILOT.md` for architectural context
- [ ] Check `docs/rules/QUICK_REFERENCE.md` if task involves game mechanics
- [ ] Verify turn numbering if writing tests (P1 = odd turns, P2 = even turns)
- [ ] Use card IDs for lookups, not names
- [ ] Use methods to modify state, not direct assignment
- [ ] Check actual file paths before suggesting commands
- [ ] Verify environment variables are in correct locations

---

## Recent Changes (Last 7 Days)

**January 6, 2026**:
- Fixed invalid turn number combinations in 13+ tests
- Updated `conftest.py` fixtures to valid defaults
- Clarified turn numbering in AI V4 remediation plan
- Cleaned up instruction files (removed operational content)
- Created this AGENTS.md file

**January 5, 2026**:
- Created `QUICK_REFERENCE.md` (67 lines) for game rules
- Rewrote `ai-prompts.instructions.md` after fabrication incident
- Organized `docs/development/` structure (44 files moved)
- Created `AI_V4_REMEDIATION_PLAN.md` with 6 phases

**Ongoing**: Phase 0 of AI V4 remediation (fix Turn 1 tussle bug)

---

## Need More Context?

**Game Mechanics**: Read `docs/rules/QUICK_REFERENCE.md`  
**Why Something Exists**: Read `COPILOT.md`  
**How to Implement**: Check subsystem AGENTS.md (when created)  
**Past Decisions**: Search GitHub issues or ask user

**Golden Rule**: When in doubt, verify from authoritative sources. Never fabricate.
