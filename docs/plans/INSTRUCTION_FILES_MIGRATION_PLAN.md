# Instruction Files Migration Plan

**Created**: January 6, 2026  
**Updated**: January 6, 2026  
**Status**: Phase 1-2 Recovered, Ready to Resume  
**Purpose**: Migrate from `.github/instructions/*.md` files to hierarchical AGENTS.md + COPILOT.md system

---

## Current Status

### What Happened

Phases 1 and 2 were completed locally on January 6, 2026 but the commits were lost when main was reset to `origin/main`. The files have been recovered from git reflog commit `e758c31`.

### Recovered Files

| File | Status | Action Needed |
|------|--------|---------------|
| `AGENTS.md` | ✅ Recovered | Review and commit |
| `COPILOT.md` | ✅ Recovered | Review and commit |
| `docs/rules/QUICK_REFERENCE.md` | ✅ Recovered | Review and commit |

### Current Instruction Files

```
.github/instructions/
├── architecture.instructions.md      # Keep - core patterns
├── backend-python.instructions.md    # Keep - Python style
├── bot-workflow.instructions.md      # Keep - Git workflow
├── coding.instructions.md            # Keep - universal (references others)
├── frontend-css.instructions.md      # Keep - CSS tokens
├── frontend-react.instructions.md    # Keep - React patterns
├── markdown.instructions.md          # Keep - MD style
├── security-and-owasp.instructions.md # Keep - security
└── testing.instructions.md           # Keep - test patterns
```

---

## Executive Summary

**Problem**: 11 instruction files (1,500+ lines total) create context overload, leading to:

- Fabricated information (e.g., "6 zones" instead of 3)
- Missing critical facts (API key locations, environment setup)
- Inconsistent patterns across sessions
- No systematic learning from failures

**Solution**: Adopt a 3-tier documentation system:

1. **AGENTS.md** (hierarchical) - Contextual facts that vary by subsystem
2. **COPILOT.md** (single file) - Architectural decisions and learnings
3. **QUICK_REFERENCE.md** (existing) - Authoritative game rules

**Key Insight**: Recent disasters were caused by:

1. **Too much generic advice** → Need "Check These Facts First" pattern
2. **No failure memory** → Need COPILOT.md to capture learnings
3. **Fabrication freedom** → Need explicit "verify first" instructions

---

## Phase 0: Assessment (Complete)

✅ **Current State**:

- 10 instruction files (just cleaned up from 11)
- Total: ~1,500 lines across multiple domains
- Recent cleanup removed operational content and consolidated deployment info
- Created QUICK_REFERENCE.md (67 lines) for game rules

✅ **Recent Learnings Captured**:

- January 5 disaster: Agent fabricated game mechanics
- Turn number confusion: Tests used invalid turn_number/active_player combinations
- Instruction bloat: Operational content mixed with coding standards

---

## Phase 1: Create Living Memory System (Priority 1)

**Goal**: Capture architectural decisions and failure learnings that persist across sessions

**Time**: 2-3 hours

### Step 1.1: Create COPILOT.md

Create `/Users/regis/Projects/ggltcg/COPILOT.md` with sections:

```markdown
# GGLTCG Project Memory

## Critical Failures & Learnings

### Disaster: Fabricated Game Mechanics (Jan 5, 2026)
**What Happened**: Agent wrote "6 zones per player" when actual game has 3 zones
**Root Cause**: No verification step, no authoritative source checking
**Fix**: Created QUICK_REFERENCE.md, rewrote ai-prompts.instructions.md with verified-only content
**Prevention**: ALWAYS verify game mechanics against docs/rules/QUICK_REFERENCE.md before writing

### Bug: Invalid Turn Number Combinations (Jan 6, 2026)
**What Happened**: Tests had turn_number=2 with active_player="player1" (impossible state)
**Root Cause**: Confusing turn numbering (game turns vs player-relative turns)
**Fix**: Updated conftest.py defaults, made all tests explicit about turn numbers
**Prevention**: Turn sequence is P1(T1) → P2(T2) → P1(T3) → P2(T4). Always explicit.

## Architectural Decisions

### Decision: ID-Based Lookups Only
**Decision**: Use card.id for all lookups, NEVER card.name
**Rationale**: Multiple cards can have same name in different zones
**Tried and rejected**: Name-based lookups caused targeting bugs
**Implementation**: GameState.find_card_by_id() is the only lookup method

### Decision: Data-Driven Effects
**Decision**: Card effects defined in cards.csv, parsed by EffectRegistry
**Rationale**: New cards without code changes, easier testing
**Tried and rejected**: Hard-coded effects per card (unmaintainable)
**Implementation**: See backend/src/game_engine/effects/

### Decision: Dual-Request AI System (V4)
**Decision**: Request 1 generates sequences, Request 2 selects best
**Rationale**: Better strategic planning than single-request V3
**Tried and rejected**: V3 single-request (too reactive, poor planning)
**Status**: V4 in development, Phase 0 of remediation plan pending

## Testing Philosophy

### Decision: Manual + Automated Smoke Tests
**Decision**: Turn 1 (P1) + Turn 2 (P2) as core regression test
**Rationale**: Quick to run, covers CC mechanics, effects, tussles, direct attacks
**Implementation**: See AI_V4_REMEDIATION_PLAN.md Phase 2

### Decision: Explicit Test Setup
**Decision**: Tests must explicitly set turn_number and active_player
**Rationale**: Default values caused impossible game states
**Implementation**: No defaults in conftest.py anymore (or explicit valid defaults)

## Environment Facts

### Development Setup
- **Local backend**: http://localhost:8000 (FastAPI + SQLite)
- **Local frontend**: http://localhost:5173 (Vite + React)
- **Production backend**: https://ggltcg.onrender.com (PostgreSQL)
- **Production frontend**: Vercel auto-deploy from main

### API Keys & Secrets
- **Google Gemini API**: backend/.env (GOOGLE_API_KEY)
- **Database**: backend/ggltcg.db (local), Render PostgreSQL (prod)
- **Git workflow**: regisca-bot for automated PRs, RegisCA for reviews

## Tech Stack

### Backend
- Python 3.13, FastAPI, SQLAlchemy
- Game engine: Custom state machine with effect system
- AI: Google Gemini 1.5 Flash (dual-request V4 architecture)

### Frontend
- TypeScript, React, TanStack Query
- Vite build, CSS custom properties for design tokens

### CI/CD
- Commits to main → auto-deploy to Render + Vercel
- GitHub Actions for future automation
- Snyk integration planned but not active
```

**Acceptance Criteria**:

- [ ] COPILOT.md created with all sections
- [ ] January 5 + January 6 disasters documented
- [ ] All major architectural decisions captured
- [ ] Committed to main

---

## Phase 2: Create Root AGENTS.md with "Check Facts First" (Priority 2)

**Goal**: Replace generic instruction files with verification-focused root context

**Time**: 2 hours

### Step 2.1: Create Root AGENTS.md

Create `/Users/regis/Projects/ggltcg/AGENTS.md`:

```markdown
# GGLTCG Project Context

## ⚠️ CHECK THESE FACTS FIRST ⚠️

Before suggesting code or architecture, VERIFY these facts from actual files:

### Game Mechanics (HIGH RISK - Agent has fabricated these)
- ✅ **DO**: Read docs/rules/QUICK_REFERENCE.md for authoritative rules
- ✅ **DO**: Read backend/data/cards.csv for actual card data
- ❌ **NEVER**: Make up game mechanics or "assume" how cards work
- ❌ **NEVER**: Say "6 zones" (there are 3: Hand, In Play, Sleep Zone)

### Turn Numbering (HIGH RISK - Causes test bugs)
- Turn sequence: P1(T1) → P2(T2) → P1(T3) → P2(T4)...
- turn_number=1, active_player="player1" ✅ Valid
- turn_number=2, active_player="player2" ✅ Valid
- turn_number=2, active_player="player1" ❌ IMPOSSIBLE
- CC: P1 gains 2 on T1, everyone gains 4 on T2+, cap at 7

### Environment Setup (Frequently missed)
1. **Backend start**: `cd backend && python run_server.py`
2. **Frontend start**: `cd frontend && npm run dev`
3. **API Key location**: `backend/.env` (GOOGLE_API_KEY)
4. **Database**: `backend/ggltcg.db` (local), Render PostgreSQL (prod)
5. **Tests**: `cd backend && pytest tests/` (activate venv first)

### Git Workflow (Use correct account)
- **regisca-bot**: For automated PRs (security updates, bot changes)
- **RegisCA**: For reviews and manual work
- **Check active account**: `gh auth status`
- **Switch accounts**: `gh auth switch -u <username>`

### GitHub Integration (When context unclear)
- Use GitHub MCP tools to check issues and PRs
- Search for past decisions: `mcp_github_github_search_issues`
- Check recent changes: `mcp_github_github_list_pull_requests`

## Project Overview

GGLTCG is a 2-player custom trading card game with:
- **Backend**: Python FastAPI, custom game engine with data-driven effects
- **Frontend**: React TypeScript with TanStack Query
- **AI Integration**: Google Gemini dual-request architecture (V4)
- **Deployment**: Render (backend) + Vercel (frontend), auto-deploy from main

## Critical Architecture Principles

See COPILOT.md for detailed decisions and rationale.

**Key patterns** (detailed in subsystem AGENTS.md):
1. **ID-based lookups** - Use card.id, NEVER card.name
2. **Method-based state** - Use card.apply_damage(), NEVER card.stamina -= 1
3. **Data-driven effects** - Define in cards.csv, parse with EffectRegistry
4. **Explicit test setup** - Always specify turn_number and active_player

## Documentation Structure

- **COPILOT.md** - Architectural decisions and failure learnings (READ THIS FIRST)
- **QUICK_REFERENCE.md** - Game rules (authoritative source)
- **docs/development/** - Architecture, effect system, feature specs
- **AGENTS.md** (this file) - Root context and verification checklist
- **backend/AGENTS.md** - Backend-specific context (to be created)
- **frontend/AGENTS.md** - Frontend-specific context (to be created)

## When Instructions Conflict

**Code is source of truth**. If these instructions conflict with actual code:
1. Code is correct
2. Update AGENTS.md or COPILOT.md to match reality
3. Document why the pattern exists in COPILOT.md
```

**Acceptance Criteria**:

- [ ] Root AGENTS.md created
- [ ] "Check Facts First" section captures recent failure patterns
- [ ] References COPILOT.md and QUICK_REFERENCE.md
- [ ] Committed to main

---

## Phase 3: Create Subsystem AGENTS.md (Priority 3)

**Goal**: Migrate domain-specific content from instruction files to subsystem AGENTS.md

**Time**: 3-4 hours

### Step 3.1: Create backend/AGENTS.md

Consolidate:

- `architecture.instructions.md` → Core patterns section
- `backend-python.instructions.md` → Python style section
- `testing.instructions.md` → Testing patterns section
- `ai-prompts.instructions.md` → AI dev section (or separate backend/src/game_engine/ai/AGENTS.md)

Structure:

```markdown
# Backend Context

## Check Backend Facts First
[Backend-specific facts to verify]

## Core Architecture Patterns
[From architecture.instructions.md]

## Python Code Style
[From backend-python.instructions.md]

## Testing Patterns
[From testing.instructions.md]

## Game Engine Specifics
[Link to game_engine/AGENTS.md if needed]
```

### Step 3.2: Create frontend/AGENTS.md

Consolidate:

- `frontend-react.instructions.md` → React/TypeScript patterns
- `frontend-css.instructions.md` → Design tokens and styling

Structure:

```markdown
# Frontend Context

## Check Frontend Facts First
[Frontend-specific facts to verify]

## React/TypeScript Patterns
[From frontend-react.instructions.md]

## Design System
[From frontend-css.instructions.md]

## API Integration
[TanStack Query patterns]
```

### Step 3.3: Keep Universal Files

**Keep as instruction files** (apply to all files):

- `security-and-owasp.instructions.md` - Security patterns (universal)
- `markdown.instructions.md` - Markdown style (applies to *.md)
- `bot-workflow.instructions.md` - Git/PR workflow (universal)
- `coding.instructions.md` - Universal standards (but trim further)

**Rationale**: These are truly universal and benefit from `applyTo: '*'` targeting

**Acceptance Criteria**:

- [ ] backend/AGENTS.md created
- [ ] frontend/AGENTS.md created
- [ ] Content migrated from relevant instruction files
- [ ] Old instruction files deleted or marked deprecated
- [ ] Committed to main

---

## Phase 4: Create Workflow Prompt Files (Priority 4)

**Goal**: Automate repetitive workflows

**Time**: 1-2 hours

### Step 4.1: Identify Repetitive Workflows

From recent sessions, common workflows:

1. **Start development environment** - backend + frontend + verify
2. **Run test suite** - activate venv, run pytest, check results
3. **Pre-deployment checklist** - tests, build, verify no errors
4. **Create PR with regisca-bot** - switch account, create branch, commit, PR

### Step 4.2: Create Starter Prompts

Create `.github/prompts/start-dev.prompt.md`:

```markdown
---
mode: ask
description: Start local development environment and verify
---

# Start Development Environment

## Steps
1. Check if backend is running: `curl http://localhost:8000/health`
2. If not running: `cd backend && python run_server.py`
3. Check if frontend is running: `curl http://localhost:5173`
4. If not running: `cd frontend && npm run dev`
5. Verify .env exists: `backend/.env` (contains GOOGLE_API_KEY)
6. Open browser to http://localhost:5173

---
**Usage**: Type `/start-dev` in Copilot Chat
```

Create `.github/prompts/run-tests.prompt.md`:

```markdown
---
mode: ask
description: Run full test suite and report results
---

# Run Test Suite

## Steps
1. Activate venv: `source .venv/bin/activate`
2. Run tests: `cd backend && pytest tests/ -v`
3. Check for failures
4. If failures: Show failure details
5. Report: X passed, Y failed

---
**Usage**: Type `/run-tests` in Copilot Chat
```

**Acceptance Criteria**:

- [ ] 2-3 prompt files created for actual repetitive workflows
- [ ] Tested and verified they work
- [ ] Committed to main

---

## Phase 5: Gradual Cutover & Monitoring (Ongoing)

**Goal**: Monitor effectiveness and iterate

### Step 5.1: Trial Period (2 weeks)

**Monitor**:

- Are sessions starting faster (less context to digest)?
- Are "Check Facts First" violations decreasing?
- Is COPILOT.md being referenced and updated?
- Are prompt files being used?

**Metrics** (informal):

- Fabrication incidents (goal: 0)
- Sessions requiring re-reading game rules (goal: decrease)
- Time to productive coding (goal: decrease)

### Step 5.2: Iterate

**After 2 weeks**:

- Review COPILOT.md - Is it helpful? Missing anything?
- Review AGENTS.md structure - Is nesting helping or hurting?
- Review prompt files - Being used? Need more?
- Update or remove instruction files that aren't helping

### Step 5.3: Delete Old Instruction Files

**Only after verification**:

- Confirm AGENTS.md is being loaded by Copilot
- Confirm no loss of critical context
- Delete migrated instruction files
- Update coding.instructions.md to reference new system

---

## Migration Mapping

| Current Instruction File | New Location | Status |
|--------------------------|--------------|---------|
| `ai-prompts.instructions.md` | `backend/src/game_engine/ai/AGENTS.md` | Phase 3 |
| `architecture.instructions.md` | `backend/AGENTS.md` | Phase 3 |
| `backend-python.instructions.md` | `backend/AGENTS.md` | Phase 3 |
| `testing.instructions.md` | `backend/AGENTS.md` | Phase 3 |
| `frontend-react.instructions.md` | `frontend/AGENTS.md` | Phase 3 |
| `frontend-css.instructions.md` | `frontend/AGENTS.md` | Phase 3 |
| `coding.instructions.md` | Keep (trim to reference new system) | Phase 5 |
| `bot-workflow.instructions.md` | Keep (universal) | N/A |
| `security-and-owasp.instructions.md` | Keep (universal) | N/A |
| `markdown.instructions.md` | Keep (universal) | N/A |

---

## Success Criteria

**Phase 1 Success**:

- COPILOT.md exists and captures all major decisions and failures
- Team (you) references it when starting sessions

**Phase 2 Success**:

- Root AGENTS.md exists with "Check Facts First"
- Agent verifies facts before suggesting code (measured by fewer corrections needed)

**Phase 3 Success**:

- Subsystem AGENTS.md files exist
- Context is more relevant to current working directory
- Overall instruction file count reduced from 10 to ~6

**Phase 4 Success**:

- 2-3 prompt files exist for repetitive workflows
- Used at least weekly

**Overall Success** (3-month horizon):

- Zero fabrication incidents
- Sessions start productively within 5 minutes
- Architectural decisions are documented and discoverable
- New contributors can understand patterns from COPILOT.md

---

## Implementation Schedule

**Week 1 (Current)**:

- ✅ Clean up existing instruction files
- Phase 1: Create COPILOT.md
- Phase 2: Create root AGENTS.md

**Week 2**:

- Phase 3: Create subsystem AGENTS.md
- Begin trial period

**Week 3**:

- Phase 4: Create prompt files
- Continue monitoring

**Week 4+**:

- Phase 5: Iterate based on effectiveness
- Consider deleting old instruction files

---

## Risks & Mitigations

**Risk**: Copilot doesn't load AGENTS.md

- **Mitigation**: Test with simple queries, verify context appears in responses

**Risk**: Too much nested AGENTS.md creates different confusion

- **Mitigation**: Start with just root + 2 subsystems, evaluate before adding more

**Risk**: COPILOT.md becomes another unread document

- **Mitigation**: Keep it focused on actual failures and decisions, not generic advice

**Risk**: Losing good content from current instruction files

- **Mitigation**: Migrate carefully, don't delete until new system verified

---

## Next Steps

1. Review this plan with user
2. Execute Phase 1: Create COPILOT.md
3. Execute Phase 2: Create root AGENTS.md
4. Commit and test
5. Continue to Phase 3 in next session
