# AI v3 Follow-up Issues Implementation Plan

This document outlines the implementation plan for issues #252, #259, and #260, which build upon the AI v3 turn planning architecture, plus the ongoing v3 prompt optimization work.

> **Note**: Issue #258 (v2 vs v3 simulations) is deferred to a separate session focused on simulations.

## Issues Overview

| Issue | Title | Labels | Status |
|-------|-------|--------|--------|
| [#252](https://github.com/RegisCA/ggltcg/issues/252) | Add CC efficiency tracking to game logging | backend, enhancement | ✅ Complete |
| [#259](https://github.com/RegisCA/ggltcg/issues/259) | Admin - Playbacks enhancement/consolidation | frontend, simulations, refactor | ✅ Complete (Option A) |
| [#260](https://github.com/RegisCA/ggltcg/issues/260) | Update play by play and AI logs for Gemiknight v3 | AI, backend, enhancement | ✅ Complete |

### Open v3 Prompt Bugs

| Issue | Title | Root Cause |
|-------|-------|------------|
| [#267](https://github.com/RegisCA/ggltcg/issues/267) | CC budgeting - sequential state-tracking | Mid-turn CC gains not tracked |
| [#268](https://github.com/RegisCA/ggltcg/issues/268) | Exhaustive planning loop | AI stops early, doesn't maximize cards slept |
| [#271](https://github.com/RegisCA/ggltcg/issues/271) | CC efficiency for Drop card | Action card effects not counted |
| [#272](https://github.com/RegisCA/ggltcg/issues/272) | Drop action card not understood | Target-in-play constraint unclear |
| [#273](https://github.com/RegisCA/ggltcg/issues/273) | Archer action card not understood | Ability targeting rules unclear |

## Implementation Dependencies

```
#252 (CC Tracking) ───┐
                      ├──> #259 (Playback Consolidation)   ALL COMPLETE
#260 (AI Logs v3) ────┘

#267, #268, #271, #272, #273 ──> v3 Prompt Optimization (IN PROGRESS)
```

---

## Baseline Simulation Results

Baseline measurements before v3 prompt optimization. Both simulations ran 160 games (4 decks × 4 decks × 10 games each).

### Baseline 1: v2 AI with gemini-2.0-flash (Dec 17, 2025)

| P1 (Row) \ P2 (Col) | Aggro_Rush | Control_Ka | Disruption | Tempo_Charge |
|---------------------|------------|------------|------------|--------------|
| **Aggro_Rush**      | 60% (6-4)  | 60% (6-4)  | 100% (10-0)| 70% (7-3)    |
| **Control_Ka**      | 90% (9-1)  | 40% (4-6)  | 80% (8-2)  | 10% (1-9)    |
| **Disruption**      | 0% (0-10)  | 20% (2-8)  | 80% (8-2)  | 0% (0-10)    |
| **Tempo_Charge**    | 20% (2-8)  | 80% (8-1)  | 100% (10-0)| 60% (6-4)    |

- **Average game duration**: ~18-20 seconds
- **Average turns**: 5-7

### Baseline 2: v3 AI with gemini-2.5-flash-lite (Dec 31, 2025)

| P1 (Row) \ P2 (Col) | Aggro_Rush | Control_Ka | Disruption | Tempo_Charge |
|---------------------|------------|------------|------------|--------------|
| **Aggro_Rush**      | 50% (5-5)  | 10% (1-9)  | 100% (10-0)| 100% (10-0)  |
| **Control_Ka**      | 80% (8-2)  | 20% (2-8)  | 80% (8-2)  | 30% (3-7)    |
| **Disruption**      | 20% (2-8)  | 0% (0-10)  | 30% (3-7)  | 0% (0-10)    |
| **Tempo_Charge**    | 60% (6-4)  | 30% (3-7)  | 80% (8-2)  | 50% (5-5)    |

- **Average game duration**: ~7-14 seconds (much faster!)
- **Average turns**: 5-10

### Key Observations

1. **Speed**: v3 games complete 2-3x faster due to turn planning (one LLM call per turn vs multiple)
2. **Quality**: v3 shows bugs - Disruption deck performs worse, likely due to Drop/Archer misuse (#272, #273)
3. **Control_Ka mirror**: Dropped from 40% to 20%, suggesting mid-turn CC tracking issues (#267)
4. **CC Efficiency**: Many games show suboptimal CC usage due to early turn ending (#268)

---

## Issue #252: CC Efficiency Tracking for All Games ✅ COMPLETED

**PR**: [#265](https://github.com/RegisCA/ggltcg/pull/265) - Merged 2025-12-30

### What Was Implemented

1. **`TurnCCRecord` dataclass** in `game_state.py` with `to_dict()`/`from_dict()` serialization
2. **Simple 3-method CC tracking design**:
   - `start_turn_cc_tracking()` - snapshots CC before any gains
   - `record_cc_gained(amount)` - tracks CC gained during turn
   - `finalize_turn_cc_tracking()` - calculates `cc_spent = cc_start + cc_gained - cc_end`
3. **`get_cc_efficiency(player_id)`** method for calculating metrics
4. **Database migration 010** - added `cc_tracking` JSONB column to `game_playback` table
5. **Integration** in `game_engine.py` (start_turn/end_turn), `stats_service.py`, `game_service.py`, `routes_admin.py`
6. **9 tests** covering tracking, CC cap handling, efficiency calculation, serialization

### Key Design Decision

Opted for a **simple derivative calculation** rather than tracking CC spent throughout the codebase:
- Formula: `cc_spent = cc_start + cc_gained - cc_end`
- Only 3 method calls per turn (not scattered throughout action execution)
- CC gains are explicitly recorded; spending is derived

### Deployment Note

Render free tier doesn't support `preDeployCommand`. Updated `render.yaml` to run migrations in `startCommand`:
```
alembic upgrade head && cd src && uvicorn api.app:app --host 0.0.0.0 --port $PORT
```

---

## Issue #260: Update Play by Play and AI Logs for Gemiknight v3 ✅ COMPLETED

**PRs**: [#266](https://github.com/RegisCA/ggltcg/pull/266), [#269](https://github.com/RegisCA/ggltcg/pull/269) - Merged

### What Was Implemented

1. **Extended AI Log Schema** with v3 fields:
   - `ai_version` (2 or 3)
   - `turn_plan` (full JSON with threat_analysis, strategy, action_sequence)
   - `plan_execution_status` ("complete", "partial", "fallback")
   - `fallback_reason`, `planned_action_index`

2. **Turn Plan Logging**: v3 plans logged with full context

3. **Admin AI Logs View**: 
   - Groups logs by turn
   - Displays strategy, CC metrics, action sequence with status icons
   - Collapsible prompt/response details
   - Fallback warnings with reasons

---

## Issue #259: Admin Playbacks Enhancement ✅ COMPLETED

**Implementation**: Option A (minimal changes to admin.html)

### What Was Implemented

1. **CC Tracking display in Playbacks tab**:
   - Per-turn CC table showing Turn #, P1 CC, P2 CC
   - Format: `start→end` with color coding for active player
   - Totals row with gained/spent per player

2. **AI Log link from Playbacks**:
   - "View AI Logs for this Game" button in playback detail
   - Switches to AI Logs tab with `game_id` filter applied
   - "Clear Filter" button to remove filter

### Files Modified

- `frontend/admin.html` - Single file, ~100 lines added

---

## v3 Prompt Optimization Plan

Holistic fix for issues #267, #268, #271, #272, #273. All stem from three root causes:
1. **Mid-turn CC changes not tracked** during planning
2. **AI stops planning early** instead of maximizing cards slept
3. **Card targeting rules unclear** in prompt

### Implementation Steps

#### Step 1: Sequential CC State-Tracking (#267)

**File**: `backend/src/game_engine/ai/prompts/planning_prompt_v2.py`

Add requirement for step-by-step CC calculation in action sequence:

```
## CC BUDGET TRACKING (CRITICAL)

For EACH action in your sequence, you MUST track:
- Action: [what you're doing]
- CC Cost: [cost]
- New CC: [remaining CC after this action]

Example:
1. Play Surge (0 CC) → New CC: 2+1 = 3
2. Tussle Ka vs Knight (2 CC) → New CC: 3-2 = 1
3. End Turn → Final CC: 1
```

**File**: `backend/src/game_engine/ai/prompts/schemas.py`

Add `cc_after_action` field to action sequence schema:

```python
class PlannedAction(BaseModel):
    action_type: str
    card_name: Optional[str]
    target_name: Optional[str]
    cc_cost: int
    cc_after_action: int  # NEW: CC remaining after this action
    reasoning: str
```

#### Step 2: Exhaustive Action Loop (#268)

**File**: `backend/src/game_engine/ai/prompts/planning_prompt_v2.py`

Change persona and add exhaustive requirement:

```
## PERSONA: Aggressive Board Maximizer

Your goal is to SLEEP AS MANY OPPONENT CARDS AS POSSIBLE each turn.

## ACTION GENERATION RULE

Generate actions until BOTH conditions are met:
1. CC < 2 (cannot afford any more actions)
2. No valid targets remain for any playable card/ability

## VERIFICATION CHECKLIST (before ending turn)

□ Did I end with ≥2 CC remaining?
  → If YES: Why couldn't I attack? (must justify)
□ Are there opponent toys I could tussle/ability?
  → If YES: Why didn't I? (must justify)
□ Did I maximize cards slept this turn?
```

Add `residual_cc_justification` field to TurnPlan schema for explaining leftover CC.

#### Step 3: Card Targeting Constraints (#272, #273)

**File**: `backend/src/game_engine/ai/prompts/card_effect_docs.py`

Add explicit warnings for Drop and Archer:

```python
"Drop": """
**Drop** (Action Card, Cost: 2 CC)
Effect: Sleep target opponent toy IN PLAY

⚠️ CRITICAL CONSTRAINTS:
- **REQUIRES a valid target**: Opponent must have at least 1 toy in play
- **Turn 1 trap**: If you're Player 2 and opponent has 0 toys, DROP HAS NO VALID TARGETS
- Cannot target cards in hand or sleep zone
""",

"Archer": """
**Archer** (Toy Card, Cost: 0 CC to play)
Ability: Pay 1 CC to sleep target opponent toy IN PLAY

⚠️ CRITICAL CONSTRAINTS:
- **ONLY targets toys IN PLAY** - cannot target opponent's hand
- If opponent has 0 toys in play, Archer's ability has NO VALID TARGETS
- Must pay 1 CC to use ability (separate from play cost)
"""
```

#### Step 4: Controller-Centric Language

**File**: `backend/src/game_engine/ai/prompts/card_effect_docs.py`

Replace ambiguous "YOUR" with "controller's" to prevent perspective drift:

```python
# Before
"When YOUR toy wins a tussle..."

# After  
"When the controller's toy wins a tussle..."
```

Apply to all card descriptions that use second-person language.

#### Step 5: Backend CC Efficiency for Action Cards (#271)

**File**: `backend/src/game_engine/game_engine.py`

Track cards slept by Action card effects toward efficiency:

```python
def _apply_action_card_effect(self, action_card, target):
    # ... existing logic ...
    if target and target.zone == Zone.SLEEP:
        # Card was put to sleep by action card effect
        self.game_state.record_opponent_card_slept()
```

#### Step 6: Few-Shot Examples

**File**: `backend/src/game_engine/ai/prompts/planning_prompt_v2.py`

Add 2-3 worked examples showing multi-action sequences:

```
## EXAMPLE: Multi-Action Turn with CC Tracking

Starting: 4 CC, Hand: [Surge, Ka, Drop], Opponent has: Knight (in play)

Plan:
1. Play Surge (0 CC) → New CC: 4+1 = 5 (Surge grants +1)
2. Play Ka (0 CC) → New CC: 5
3. Tussle Ka vs Knight (2 CC) → New CC: 3
4. Play Drop targeting Knight (2 CC) → New CC: 1
   [Wait - Knight already sleeping from tussle loss, invalid target]
   REVISED: Direct Attack with Ka (2 CC) → New CC: 1
5. End Turn → Final CC: 1

Result: 4 CC spent (5 gained - 1 remaining), 1 card slept = 4.0 efficiency
```

### Testing Approach

Manual testing via admin UI:
1. Play games against v3 AI on one screen
2. View AI planning logs in admin UI on second screen
3. Verify:
   - CC tracking shows correct `cc_after_action` values
   - AI doesn't play Drop/Archer without valid targets
   - AI exhausts CC before ending turn
   - Leftover CC has justification

### Estimated Effort

| Step | Hours | Files |
|------|-------|-------|
| Step 1 (CC tracking) | 2-3h | planning_prompt_v2.py, schemas.py |
| Step 2 (Exhaustive loop) | 2-3h | planning_prompt_v2.py, schemas.py |
| Step 3 (Card constraints) | 1-2h | card_effect_docs.py |
| Step 4 (Controller language) | 1h | card_effect_docs.py |
| Step 5 (Backend efficiency) | 2h | game_engine.py |
| Step 6 (Few-shot examples) | 1-2h | planning_prompt_v2.py |
| Testing & iteration | 4-6h | - |

**Total**: 13-19 hours

---

## Summary of Files to Modify/Create

### Completed (PRs #265, #266, #269)

| File | Changes | Status |
|------|---------|--------|
| `game_engine/models/game_state.py` | `TurnCCRecord`, `cc_history` field | ✅ |
| `game_engine/game_engine.py` | CC tracking during game execution | ✅ |
| `game_engine/ai/llm_player.py` | v3 plan logging, execution status | ✅ |
| `api/db_models.py` | Extended `AILogModel` with v3 fields | ✅ |
| `api/routers/game.py` | CC efficiency on game completion | ✅ |
| `api/routers/admin.py` | CC stats in playback response | ✅ |
| `frontend/admin.html` | CC tracking display, AI log links | ✅ |

### Remaining (v3 Prompt Optimization)

| File | Changes |
|------|---------|
| `game_engine/ai/prompts/planning_prompt_v2.py` | Sequential CC tracking, exhaustive loop, few-shot examples |
| `game_engine/ai/prompts/schemas.py` | `cc_after_action`, `residual_cc_justification` fields |
| `game_engine/ai/prompts/card_effect_docs.py` | Drop/Archer constraints, controller-centric language |
| `game_engine/game_engine.py` | Track Action card sleeps for efficiency |

---

## Estimated Effort Summary

| Work Item | Hours | Status |
|-----------|-------|--------|
| #252 (CC Tracking) | 8-12h | ✅ Complete |
| #260 (AI Logs v3) | 12-16h | ✅ Complete |
| #259 (Playback Enhancement) | 4-5h | ✅ Complete |
| v3 Prompt Optimization | 13-19h | 🔄 Planned |

**Remaining**: 13-19 hours for prompt optimization

## Next Steps

1. ~~#252 CC Tracking~~ ✅
2. ~~#260 AI Logs v3~~ ✅
3. ~~#259 Admin Playback Enhancement~~ ✅
4. **v3 Prompt Optimization** - Fix #267, #268, #271, #272, #273
5. Run post-optimization simulation to compare against baselines

