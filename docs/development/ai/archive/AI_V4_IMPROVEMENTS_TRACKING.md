# AI V4 Improvements Tracking

**Purpose**: Track potential fixes and improvements for AI V4 based on production game analysis  
**Status**: Active - Updated as new patterns are discovered  
**Methodology**: Data-driven approach using production game logs

---

## Iteration Process (V4)

**Optimization target**:
- Model: `gemini-2.5-flash-lite`
- Request 1 (sequence generation) temperature: `0.2`
- Request 2 (strategic selection) temperature: `0.7`

**Guardrails (keep us honest)**:
- Change **1–2 things max** per iteration (prompt or logic). No grab-bag PRs.
- Keep planning prompt context optimized; avoid adding more and more instructions.
- Avoid card-specific fixes. If we add examples using cards that are not in the active 12-card pool, we’re probably overfitting.

### Baseline Test (Fast Gate)

Run a small mirror test using `User_Slot3` (Archer/Knight tempo). This is a quick “did we break planning?” check before broader sims.

```bash
cd backend
python -m simulation.cli quick User_Slot3 User_Slot3 --iterations 20 --model gemini-2.5-flash-lite --ai-version 4
```

Notes:
- Turn limit is `20` by default (`SimulationConfig.max_turns`). 

### Draft Success Criteria (Iteration 0)

- **0/20 games** hit the 20-turn limit.
- **Turn 1–2 wasteful plans** below `X%`.
  - Definition: “wasteful” is `cc_wasted >= 4` per `backend/src/game_engine/ai/quality_metrics.py`.
  - We specifically care about early turns because prompt/plan quality issues show up there first.

### Non-Mirror Test (Broader Gate)

Mirror is useful as a “did we break planning?” sanity check, but it can overproduce stalemates.

This suite runs `User_Slot3` against four baseline decks (5 games each):

```bash
cd backend
python scripts/gate_user_slot3_suite_v4.py
```

**Most recent run (20 games)**:
- Overall: P1 wins 9/20, P2 wins 4/20, draws 7/20 (**turn-limit hits 7/20**), **avg turns 18.9**
- By matchup:
  - User_Slot3 vs Aggro_Rush: P1 1/5, P2 2/5, draws 2/5 (TL 2/5), avg turns 21.4
  - User_Slot3 vs Control_Ka: P1 2/5, P2 2/5, draws 1/5 (TL 1/5), avg turns 13.8
  - User_Slot3 vs Tempo_Charge: P1 3/5, P2 0/5, draws 2/5 (TL 2/5), avg turns 20.0
  - User_Slot3 vs Disruption: P1 3/5, P2 0/5, draws 2/5 (TL 2/5), avg turns 20.6
- Early turns (T1/T2) unused CC (active player `cc_end`): avg 1.30; unused >=1 in 26/40; unused >=2 in 16/40

**Recurring symptom counters (counts in stdout/stderr)**:
- `cc_went_negative`: 29
- `didnt_specify_target`: 19
- `sequence_rejected`: 19
- `invalid_sequence_index`: 2
- `json_parse_error`: 1
- `plan_deviation`: 1
- `ai_failed_to_select_action`: 1

### Session Kickoff Prompt (Copy/Paste)

```
We are improving AI V4 for gemini-2.5-flash-lite using simulation.

Constraints:
- Make at most TWO changes total.
- Prefer non-card-specific fixes (avoid hard-coding card names).
- Keep prompt context budget flat: do not add large new instruction blocks.
- Request 1 temp = 0.2, Request 2 temp = 0.7.

Process:
1) Pick one concrete symptom to target (planning or execution).
2) Reproduce with a small sim first (20 games, User_Slot3 mirror).
3) Implement the smallest fix.
4) Re-run the small sim, then a larger sim.
5) If results hold, create a PR.

Output:
- What changed, where
- Before/after results summary
- Next single best follow-up (do not implement)
```

## Diagnostic Improvements

### ✅ COMPLETED

#### 1. V4 Request 2 Prompt Logging (PR #TBD)
**Status**: ✅ Implemented  
**Issue**: Admin logs showed empty `"prompt": ""` for V4 Request 2  
**Fix**: Enhanced `get_last_decision_info()` to include V4-specific fields:
- `v4_request1_prompt` and `v4_request1_response`
- `v4_request2_prompt` and `v4_request2_response`

**Impact**: Full visibility into dual-request architecture for debugging

#### 2. Execution Logging Enhancement (PR #TBD)
**Status**: ✅ Implemented  
**Issue**: Couldn't see what actions were available or what was actually executed  
**Fix**: Enhanced execution log entries with:
- `available_actions_count`: Total valid actions available
- `matched_action`: Details of action that was actually executed

**Impact**: Can now diagnose why heuristic matching fails and what LLM fallback does

---

## Prompt Architecture Fixes

### 🔴 HIGH PRIORITY

#### 3. State-Change Pre-Computation
**Status**: 🔴 Not started  
**Pattern**: Game 5c54f1b8 Turn 2 missed direct_attack after tussle cleared board  
**Issue**: Request 1 doesn't reliably apply mid-sequence state changes  
**Proposed Fix**: Pre-compute state changes and make them explicit

**Example**:
```
After tussle 3fbbdfd9->c76e7c4a (which sleeps opponent's LAST toy):
  ✓ direct_attack becomes LEGAL (opponent now has 0 toys)
  ✓ You have 3 CC remaining (enough for direct_attack)
  → RECOMMENDED: Include direct_attack in this sequence
```

**Test Scenario**: 4 CC, Surge + Knight in hand, opponent has 1 toy  
**Expected**: At least one sequence includes `tussle → direct_attack`  
**Current**: ❌ No sequences include direct_attack

**Effort**: Medium (requires state simulation logic)  
**Risk**: Low (makes implicit rules explicit)

#### 11. Pre-Compute Available CC Budget 🚨 **BLOCKING ISSUE**
**Status**: ✅ Fixed (PR #TBD)
**Priority**: ⭐⭐⭐ CRITICAL - Blocks multiple production games  
**Pattern**: **Confirmed in 7 games** (39b9a27c T4, 4d80a9c6 T3, be31bc7d T3, 67b79fa0 T1/T3, 4308a90a T1/T5)  
**Issue**: Request 1 prompt says "CC: X (Surge adds +1, Rush adds +2 when played)" but LLM systematically miscalculates actual CC  
**Impact**: Results in ALL sequences being illegal → complete turn failure  
**Fix Implemented**: 
- Dynamic header generation in `sequence_generator.py`
- Only shows "Max potential" text if Surge/Rush are actually in hand
- Removes static rule text that caused hallucinations

**Verification**:
- Added regression test `backend/tests/test_ai_prompts_v4.py`
- Confirmed clean header for no-Surge case
- Confirmed correct potential calculation for Surge case

**Current Prompt (Fixed)**:
```
## CC: 4
```
OR (if Surge in hand):
```
## CC: 4 (Max potential: 5 via Surge +1)
```

**What Happened (3 confirmed instances)**:
- Game 39b9a27c T4: Claimed 7 CC, had 4 CC → All 10 sequences illegal
- Game 4d80a9c6 T3: Claimed 7 CC, had 4 CC → All 7 sequences illegal
- Game be31bc7d T3: Claimed 8 CC, had 5 CC → All 8 sequences illegal (selected Raggy+Dream=7CC, only had 5CC)

**Test Scenario**: 4 CC base, no CC-boost cards in hand  
**Expected**: All sequences ≤ 4 CC total  
**Current**: ❌ Generates sequences assuming 7-8 CC (systemic pattern)

**Effort**: Low (calculation already exists, needs clearer prompt formatting)  
**Risk**: Very low (prevents hallucinations)  
**Blocker for**: Multiple production games failing due to this issue

#### 12. Validate Generated Sequences Before Request 2 ⭐ NEW
**Status**: 🔴 Not started  
**Pattern**: Game 39b9a27c Turn 4 strategic selector chose illegal sequence  
**Issue**: No validation layer between Request 1 and Request 2  
**Proposed Fix**: Parse and validate sequences after Request 1

**Implementation**:
```python
def validate_sequences(sequences, available_cc):
    valid_sequences = []
    for seq in sequences:
        total_cc = calculate_sequence_cc_cost(seq)
        if total_cc <= available_cc:
            valid_sequences.append(seq)
        else:
            logger.warning(f"Filtered illegal sequence: {seq} (needs {total_cc}, have {available_cc})")
    
    if not valid_sequences:
        logger.error("All sequences invalid! Regenerating Request 1...")
        return regenerate_request_1()
    
    return valid_sequences
```

**What Happened**:
- Request 1 generated 10 sequences (all 5-7 CC)
- Strategic selector chose sequence 0 (needs 5 CC)
- Execution failed (only had 4 CC)
- No validation caught this

**Test Scenario**: Generated sequences exceed CC budget  
**Expected**: Invalid sequences filtered, valid ones passed to Request 2  
**Current**: ❌ All sequences (even illegal ones) sent to Request 2

**Effort**: Medium (requires sequence parsing logic)  
**Risk**: Low (acts as safety net)

#### 4. Zone-Based Card Prefixes
**Status**: 🔴 Not started  
**Pattern**: Turn 4 tried to play Knight from sleep zone  
**Issue**: All zones use similar formatting, model confuses them  
**Proposed Fix**: Add zone prefixes to card names

**Example**:
```
## PLAYABLE CARDS (in your hand):
- [HAND] Umbruh (id=fe830919..., cost=1, STR=4, HP=4)
- [HAND] Archer (id=661a2d1e..., cost=0, STR=0, HP=5)

## SLEPT CARDS (cannot be played):
- [SLEEP] Surge (id=6bd2fe20...)
- [SLEEP] Knight (id=3fbbdfd9...)

RULE: Only cards marked [HAND] can be used in play_card actions.
```

**Test Scenario**: Hand = [Umbruh], Sleep = [Knight]  
**Expected**: No sequences include playing Knight  
**Current**: ❌ Generates `play Knight` using sleep zone ID

**Effort**: Low (formatting change only)  
**Risk**: Very low (adds clarity without changing logic)

#### Issue #295: Sleep Zone Formatting Too Sparse (Wake Targeting)
**Status**: ✅ Fixed

**Hypothesis**: Request 1’s sleep-zone listing (used for Wake targeting) didn’t include enough actionable info, causing weak planning and contributing to long games / stalemates.

**Fix Implemented**:
- V4 Request 1 now formats the sleep zone using the v3 compact card formatter, so entries include type/cost (and stats for toys) instead of just name/ID.
- Added a regression test asserting the sleep-zone section contains actionable fields.

**Where**:
- `backend/src/game_engine/ai/prompts/sequence_generator.py`
- `backend/src/game_engine/ai/prompts/planning_prompt_v3.py`
- `backend/tests/test_ai_prompts_v4.py`

**Result so far**: Mirror + non-mirror suites still show turn-limit draws, so this change is likely necessary-but-not-sufficient.

### Recurring Issues / Symptoms (for reproduction)

These are the highest-frequency “symptom signatures” seen in recent gate runs:

1) **"CC went negative … - capping at 0"**
  - Seen as: `CC went negative (-X) after … - capping at 0`
  - Likely origin:
    - `backend/src/game_engine/ai/prompts/strategic_selector.py` (selector-produced `cc_after` inconsistent)
    - `backend/src/game_engine/ai/validators/turn_plan_validator.py` (turn-plan validation)

2) **"AI didn't specify target, using first option"**
  - Likely origin: `backend/src/game_engine/ai/llm_player.py` (fallback target selection when LLM omits/invalidates target IDs)

3) **"Sequence X rejected: …"**
  - Likely origin: `backend/src/game_engine/ai/turn_planner.py` (sequence validation/rejection between Request 1 and Request 2)

4) **"Invalid sequence index, using 0"**
  - Likely origin: `backend/src/game_engine/ai/turn_planner.py` (strategic selector returns out-of-range index)

5) **"JSON parse error"**
  - Indicates malformed JSON from Request 1 or Request 2 response parsing.

When you dig into reproductions, these signatures are a good first “grep target” in logs.

### 🟡 MEDIUM PRIORITY

#### 5. Strategic Goal Clarification
**Status**: 🟡 Not started  
**Pattern**: Turn 2 selector chose sequence leaving 2 CC unused  
**Issue**: Request 2 reasoning said "minimal CC" is good (sounds like conservation)  
**Proposed Fix**: Reframe goals to emphasize CC utilization

**Current Wording**:
```
<goal>
Select the sequence that maximizes your chance of winning.
Priority order:
1. LETHAL — Can you win THIS turn?
2. REMOVAL — Sleep opponent's toys to reduce threats
3. TEMPO — Build board advantage
4. EFFICIENCY — Spend less CC per card slept
```

**Proposed Wording**:
```
<goal>
Select the sequence that maximizes your chance of winning.
Priority order:
1. LETHAL — Win THIS turn by sleeping all remaining opponent cards
2. MAXIMUM REMOVAL — Sleep the MOST opponent cards this turn
3. FULL CC UTILIZATION — Spend ALL available CC efficiently (ending with 0-1 CC is ideal)
4. TEMPO — Build board advantage when removal isn't possible

⚠️ Leaving CC unused (ending with 2+ CC) is almost always wrong unless saving for next turn's lethal.
```

**Test Scenario**: 5 CC available, best sequence uses 3 CC  
**Expected**: Flag as suboptimal or generate better sequence  
**Current**: ⚠️ Selects low-CC sequence, says "minimal CC" is good

**Effort**: Low (wording change only)  
**Risk**: Low (clarifies intent without changing architecture)

#### 6. Sequence Validation Reporting
**Status**: 🟡 Not started  
**Issue**: Can't see which sequences passed/failed validation or why  
**Proposed Fix**: Log validation results with each turn plan

**Example Log Entry**:
```json
{
  "sequence_validation": {
    "total_generated": 8,
    "passed_validation": 7,
    "failed_validation": 1,
    "validation_errors": [
      {
        "sequence_index": 3,
        "error": "play_card action references card not in hand (Knight in sleep zone)",
        "action_index": 1
      }
    ]
  }
}
```

**Effort**: Medium (requires validator integration)  
**Risk**: Low (additive logging, doesn't change behavior)

### 🔵 LOW PRIORITY

#### 13. Wake Card Syntax Clarification ⭐ NEW
**Status**: 🔵 Not started  
**Pattern**: Game 39b9a27c Turn 4 generated illegal Wake sequences  
**Issue**: Request 1 used wrong syntax: "activate Wake->Ka" instead of "play Wake [id]->target [id]"  
**Proposed Fix**: Add explicit Wake example to Request 1 prompt

**Current Prompt**: (generic ACTION card explanation)  

**Proposed Addition**:
```
## WAKE CARD SPECIAL SYNTAX
Wake is an ACTION card played FROM HAND (not an activated ability).

Correct format:
  play Wake [36f6603d]->target [knight_id]
  
Incorrect formats:
  ❌ activate Wake [36f6603d]  
  ❌ activate Wake->Ka [just_played_ka_id]

Example sequence with Wake:
  "play Wake [36f6603d]->e5fae4fa (Knight from sleep) → play Knight [e5fae4fa] → tussle → end_turn | CC: 4/4 spent"
```

**What Happened**:
- Generated: `activate 36f6603d->ca47331b` (wrong action type, wrong target)
- Should be: `play Wake [36f6603d]->target [knight_sleep_id]`
- Strategic selector chose this illegal sequence
- Would have failed during execution

**Test Scenario**: Hand = [Wake], Sleep zone = [Knight]  
**Expected**: Sequences use correct "play Wake [wake_id]->target [knight_id]" syntax  
**Current**: ❌ Uses "activate" verb and targets wrong cards

**Effort**: Low (add example to prompt)  
**Risk**: Very low (clarification only)

#### 7. Request 1 Temperature Tuning
**Status**: 🔵 Research needed  
**Current**: temp 0.2 (deterministic)  
**Question**: Would temp 0.4 improve state-change reasoning without generating illegal sequences?  
**Approach**: A/B test with simulation runs

**Test**: Run 100 games each with temp 0.2, 0.4, 0.6  
**Measure**:
- State-change sequence inclusion rate
- Illegal action rate
- Overall CC efficiency

**Effort**: Low (config change + testing)  
**Risk**: Medium (could increase illegal actions)

#### 8. Model Upgrade for Request 1
**Status**: 🔵 Research needed  
**Current**: gemini-2.5-flash-lite  
**Question**: Would gemini-2.5-flash handle state changes and zone filtering better?  
**Trade-off**: Better reasoning vs. increased API cost and latency

**Test**: Run simulation with both models  
**Measure**:
- State-change reasoning success rate
- Zone confusion rate
- V2 fallback rate
- API cost per game

**Effort**: Low (config change + testing)  
**Risk**: Medium (cost increase)


---

## Testing Infrastructure

### 🟡 MEDIUM PRIORITY

#### 9. Regression Test Suite
**Status**: 🟡 Not started  
**Purpose**: Automated tests for known failure patterns  
**Tests needed**:

**Test: State-Change Direct Attack**
```python
def test_ai_v4_turn2_direct_attack_after_board_clear():
    """Verify AI generates sequences with direct_attack when tussle clears board."""
    # Setup: 4 CC, Surge + Knight in hand, opponent has 1 toy
    # Expected: At least one sequence includes tussle → direct_attack
```

**Test: Zone Isolation**
```python
def test_ai_v4_zone_filtering():
    """Verify AI only uses cards from hand for play_card actions."""
    # Setup: Hand = [Umbruh], Sleep = [Knight]
    # Expected: No sequences include playing Knight
```

**Test: Full CC Utilization**
```python
def test_ai_v4_cc_utilization():
    """Verify AI prefers sequences that use more CC efficiently."""
    # Setup: 5 CC available
    # Expected: Selected sequence uses at least 3 CC or has good reason not to
```

**Effort**: Medium (test infrastructure + test cases)  
**Risk**: Low (helps prevent regressions)

#### 10. Prompt Ablation Framework
**Status**: 🟡 Not started  
**Purpose**: Test prompt variations systematically  
**Experiments**:
- Remove STATE CHANGES section → measure direct_attack inclusion rate
- Add [HAND] prefixes → measure zone confusion rate
- Reword goals → measure CC utilization improvement

**Approach**: Simulation-based A/B testing  
**Metrics**: Track improvements vs. baseline

**Effort**: High (requires test framework)  
**Risk**: Low (research only, doesn't affect production)

---

## Analysis Tools

### 🟡 MEDIUM PRIORITY

#### 11. V4-Specific Admin UI
**Status**: 🟡 Not started  
**Purpose**: Visualize dual-request architecture  
**Features**:
- Split view showing Request 1 (sequences) and Request 2 (selection)
- Sequence validation results inline
- Execution trace with action matching
- V4 metrics dashboard

**Effort**: High (frontend + backend)  
**Risk**: Low (UI only)

#### 12. V4 Metrics Dashboard
**Status**: 🟡 Not started  
**Purpose**: Track failure modes over time  
**Metrics**:
- V2 fallback rate (by reason)
- Request 1 failure patterns
- Request 2 selection quality
- State-change handling success rate
- Zone confusion incidents

**Effort**: Medium (data aggregation)  
**Risk**: Low (analytics only)

---

## Priority Matrix

| Priority | Item | Impact | Effort | Risk |
|----------|------|--------|--------|------|
| 🔴 HIGH | #11 Pre-Compute CC Budget ⭐ NEW | High | Low | Very Low |
| 🔴 HIGH | #12 Validate Sequences ⭐ NEW | High | Medium | Low |
| 🔴 HIGH | #3 State-Change Pre-Computation | High | Medium | Low |
| 🔴 HIGH | #4 Zone-Based Card Prefixes | High | Low | Very Low |
| 🟡 MEDIUM | #5 Strategic Goal Clarification | Medium | Low | Low |
| 🟡 MEDIUM | #6 Sequence Validation Reporting | Medium | Medium | Low |
| 🟡 MEDIUM | #9 Regression Test Suite | Medium | Medium | Low |
| 🔵 LOW | #13 Wake Syntax Clarification ⭐ NEW | Low | Low | Very Low |
| 🔵 LOW | #7 Request 1 Temperature Tuning | Unknown | Low | Medium |
| 🔵 LOW | #8 Model Upgrade for Request 1 | Unknown | Low | Medium |

**⭐ NEW** = Added from game 39b9a27c Turn 4 analysis

---

## Games Analyzed

### Game 5c54f1b8 (Turn 2 & Turn 4)
**Patterns Identified:**
- ❌ Turn 2: Missed direct_attack after board clear → #3 State-Change Pre-Computation
- ❌ Turn 4: Tried to play Knight from sleep zone → #4 Zone-Based Card Prefixes
- ✅ Turn 2: Strategic selector chose low-CC sequence → #5 Strategic Goal Clarification

**Outcome**: AI won in 4 turns despite mistakes

### Game 39b9a27c (Turn 4) - CC Hallucination Pattern #1
**Patterns Identified:**
- 🔴 Request 1 hallucinated CC budget (claimed 7, actually had 4) → #11 Pre-Compute CC Budget
- ❌ All generated sequences illegal (exceeded CC) → #12 Validate Sequences Before Request 2
- ❌ Wake sequences used wrong syntax ("activate" instead of "play") → #13 Wake Syntax Clarification
- ✅ Execution fallback prevented crash (chose end_turn when Raggy couldn't be played)

**Outcome**: AI won in 7 turns, but Turn 4 was wasted (only played Ka, 2 CC unspent)

### Game 4d80a9c6 (Turn 3) - CC Hallucination Pattern #2
**Patterns Identified:**
- 🔴 **IDENTICAL CC hallucination**: claimed 7 CC, actually had 4 CC → #11 Pre-Compute CC Budget
- ❌ All 7 sequences exceeded budget → #12 Validate Sequences Before Request 2

**Critical Finding**: Same 7 vs 4 CC mismatch as game 39b9a27c. Pattern confirmed.

### Game be31bc7d (Turn 3) - CC Hallucination Pattern #3
**Patterns Identified:**
- 🔴 CC hallucination: claimed 8 CC, actually had 5 CC (delta: +3) → #11 Pre-Compute CC Budget
- ❌ All 8 sequences exceeded budget (4-7 CC vs 5 CC available) → #12 Validate Sequences Before Request 2
- Selected sequence (Raggy 3 CC + Dream 4 CC = 7 CC) was illegal with only 5 CC

**Critical Finding**: Third confirmed instance. **SYSTEMIC FAILURE** in CC calculation.

### Game 67b79fa0 (Turns 1 & 3) - CC Hallucination Pattern #4 & #5
**Patterns Identified:**
- 🔴 Turn 1: CC hallucination: claimed 5 CC, actually had 2 CC (delta: +3) → #11 Pre-Compute CC Budget
- ❌ Turn 1: All 10 sequences exceeded budget → #12 Validate Sequences Before Request 2
- 🔴 Turn 3: CC hallucination: claimed 8 CC, actually had 5 CC (delta: +3) → #11 Pre-Compute CC Budget

**Critical Finding**: Fifth confirmed instance. Consistent +3 CC delta pattern continues.

### Game 4308a90a (Turns 1 & 5) - CC Hallucination Pattern #6 & #7
**Patterns Identified:**
- 🔴 Turn 1: CC hallucination: claimed 3 CC, actually had 2 CC (delta: +1) → #11 Pre-Compute CC Budget
- ❌ Turn 1: 3/10 sequences exceeded budget → #12 Validate Sequences Before Request 2
- 🔴 Turn 5: CC hallucination: claimed 9 CC, actually had 6 CC (delta: +3) → #11 Pre-Compute CC Budget

**Critical Finding**: Seventh confirmed instance. Pattern now confirmed across 4 games.

---

## Quick Diagnostic Tool

**New Script**: `backend/scripts/diagnose_ai_game.py`

```bash
# Analyze specific game and turn
python backend/scripts/diagnose_ai_game.py be31bc7d 3

# Analyze all turns in a game
python backend/scripts/diagnose_ai_game.py 4d80a9c6
```

**Features**:
- Automatic CC hallucination detection
- Illegal sequence identification
- Execution failure tracking
- Fallback detection
- Clear severity ratings (CRITICAL/HIGH/MEDIUM/LOW)

---

## Critical Pattern Discovery: CC Hallucination

**Status**: 🚨 SYSTEMIC FAILURE - 7 instances across 4 games confirmed  
**Root Cause**: LLM inferring CC from prompt text instead of computing precisely  
**Impact**: Complete Request 1 failure → all sequences illegal → wasted turns

**Evidence**:
1. Game 39b9a27c Turn 4: 7 CC claimed vs 4 CC actual (Δ+3)
2. Game 4d80a9c6 Turn 3: 7 CC claimed vs 4 CC actual (Δ+3)
3. Game be31bc7d Turn 3: 8 CC claimed vs 5 CC actual (Δ+3)
4. Game 67b79fa0 Turn 1: 5 CC claimed vs 2 CC actual (Δ+3)
5. Game 67b79fa0 Turn 3: 8 CC claimed vs 5 CC actual (Δ+3)
6. Game 4308a90a Turn 1: 3 CC claimed vs 2 CC actual (Δ+1)
7. Game 4308a90a Turn 5: 9 CC claimed vs 6 CC actual (Δ+3)

**Pattern**: Consistent +3 CC delta in 6 out of 7 instances. LLM appears to be adding CC bonuses from cards it hasn't played yet.

**Immediate Action**: Issue #11 is now **PRIORITY 1** - must be fixed before other improvements

---

## Next Steps

### Immediate (Current Session)
1. ✅ Implement diagnostic improvements (#1, #2)
2. ✅ Create this tracking document
3. ✅ Create diagnostic script (diagnose_ai_game.py)
4. ✅ Identify CC hallucination as systemic pattern (3 games)
5. 🔴 **NEXT**: Implement #11 (Pre-Compute CC Budget)

### Short-term (Next PR)
1. Implement #4 (Zone-Based Card Prefixes) - Quick win
2. Implement #5 (Strategic Goal Clarification) - Quick win
3. Test both with simulation runs
4. Measure improvement

### Medium-term (Following PRs)
1. Implement #3 (State-Change Pre-Computation) - Highest impact
2. Implement #9 (Regression Test Suite)
3. Research #7 and #8 (Temperature/Model tuning)
4. Build #11 (V4-Specific Admin UI)

---

## Pattern Validation Log

**Game 5c54f1b8-2471-4e93-a12a-1369a43bc01b** (Jan 3, 2026):
- ✅ Pattern 1: State-Change Reasoning Failure (Turn 2)
- ✅ Pattern 2: Zone Context Confusion (Turn 4)
- ✅ Pattern 3: CC Efficiency Misinterpretation (Turn 2)

**[Space for additional games]**

---

## Notes

- Always test prompt changes with simulation before deploying
- Document all pattern observations here for trend analysis
- Prioritize fixes with low effort + high impact
- Keep diagnostic tools updated as we learn more

