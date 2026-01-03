# Session Handoff: AI V4 Simulations Baseline

**Created:** January 2, 2026  
**Purpose:** Next session starting point for V4 AI optimization

---

## Session Goals for Next Time

1. **Run V4 simulations to establish baseline metrics**
2. **Compare V4 vs V3 performance** (win rates, decision quality)
3. **Identify V4 strategic weaknesses** from game logs
4. **Optimize V4 prompts** based on data

---

## Current V4 Status (What's Working)

### Architecture
- **Dual-request system implemented and running**
  - Request 1: Sequence generation (~2.3k chars, temp 0.2)
  - Request 2: Strategic selection (~5k chars, temp 0.7)
- **Model:** gemini-2.5-flash-lite
- **Environment:** `AI_VERSION=4` in `.env`

### Tests Passing
- 11/11 V4 component tests (`test_ai_v4_components.py`)
- 14/14 card ID disambiguation tests (`test_card_id_disambiguation.py`)

### PR Status
- PR #280 ready for merge (review comments fixed)
- Branch: `feature/ai-v4-dual-request`

### Version Tracking
- UI correctly shows "v4" badge when V4 is running
- `ai_version` field in plan data tracks actual version used

---

## Simulation System Documentation

### Available Scripts

| Script | Purpose | Location |
|--------|---------|----------|
| `run_v4_simulation.py` | V4-specific simulation runner | `backend/scripts/` |
| `test_simulation.py` | Quick simulation test | `backend/scripts/` |
| `analyze_simulation_results.py` | Parse/analyze results | `backend/scripts/` |

### Key Files
- `backend/src/simulation/runner.py` - Core simulation runner
- `backend/src/simulation/config.py` - GameOutcome, simulation config
- `backend/src/simulation/deck_loader.py` - Load decks from CSV
- `backend/data/simulation_decks.csv` - Deck definitions for testing

### Running Simulations

```bash
cd backend
source ../.venv/bin/activate
python scripts/run_v4_simulation.py --games 10
```

### What Went Wrong This Session

1. **Terminal command got stuck** - simulation script started but produced no output
2. **Subagent researched but output wasn't captured** - user asked twice for findings
3. **Session ran long** before simulations could complete

### Lessons Learned

- Simulations may take significant time - run in background or with small game counts first
- The `test_simulation.py` script can be used for quick sanity checks
- Always verify the server isn't needed (simulations run headless)

---

## V4 Goals (Original Requirements)

### Primary Objectives
1. **Reduce prompt size** - V3 was ~13k chars, V4 targets <10k total
2. **Improve strategic quality** - Better lethal detection, CC efficiency
3. **Separate concerns** - Legal move generation vs strategic selection

### Success Metrics to Establish
- Win rate vs V3 (baseline comparison)
- Lethal detection rate (when lethal is available, does V4 find it?)
- CC efficiency (CC left unused at end of turn)
- Invalid action rate (should be lower with validator)

### Known V4 Weaknesses (Observed During Testing)
1. **Follow-up direct attacks** - Added "STATE CHANGES" section to prompt to teach that tussle clearing board enables direct_attack
2. **Card ID confusion** - Fixed with better ID display format: `CardName (ID xyz123)`

---

## Prompt to Start Next Session

```
I'm continuing work on AI V4 for GGLTCG. The V4 dual-request architecture is implemented and mechanically working (PR #280 ready to merge).

**Session Goals:**
1. Merge PR #280 if CI passes
2. Run V4 simulations to establish baseline metrics (win rate, lethal detection, CC efficiency)
3. Compare V4 vs V3 performance
4. Identify strategic weaknesses from game logs

**Current State:**
- AI_VERSION=4 in .env, server running V4
- 11/11 V4 component tests passing
- Prompt sizes: Request 1 ~2.3k chars, Request 2 ~5k chars
- Known scripts: run_v4_simulation.py, test_simulation.py, analyze_simulation_results.py

**Key Questions:**
1. What's the V4 win rate baseline?
2. Does V4 find lethal when available?
3. How much CC is V4 leaving unused?
4. What patterns emerge in V4 losses?

Please start by checking PR #280 CI status, then run a small simulation (5-10 games) to verify the simulation system works, then proceed to a larger baseline test.
```

---

## Files Changed This Session

### V4 Core
- `backend/src/game_engine/ai/turn_planner.py` - Added ai_version to plan data
- `backend/src/game_engine/ai/prompts/sequence_generator.py` - Condensed prompt, added STATE CHANGES section
- `backend/src/game_engine/ai/prompts/strategic_selector.py` - Fixed unused imports

### Version Tracking
- `backend/src/api/routes_actions.py` - Read actual version from plan
- `frontend/src/components/VictoryScreen.tsx` - Dynamic version badge
- `frontend/src/pages/AdminDataViewer.tsx` - Dynamic version badge

### Tests
- `backend/tests/test_card_id_disambiguation.py` - New file, 14 tests
- `backend/tests/test_ai_v4_components.py` - Fixed unused import

### Cleanup (PR Review Fixes)
- `backend/src/game_engine/ai/prompts/examples/loader.py` - Removed unused variable
- `backend/src/game_engine/ai/validators/turn_plan_validator.py` - Removed unused variables/imports
- `backend/scripts/run_v4_simulation.py` - Removed unused import

---

## Quick Reference Commands

```bash
# Activate environment
cd /Users/regis/Projects/ggltcg
source .venv/bin/activate

# Run V4 component tests
cd backend && pytest tests/test_ai_v4_components.py -v

# Quick simulation test
cd backend && python scripts/test_simulation.py 2>&1 | head -100

# V4 simulation (10 games)
cd backend && python scripts/run_v4_simulation.py --games 10

# Check AI version in .env
cat backend/.env | grep AI_VERSION

# Start server (for manual testing)
cd backend && python run_server.py
```
