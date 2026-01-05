# AI V4 Analysis: Game 5c54f1b8-2471-4e93-a12a-1369a43bc01b

**Date**: January 3, 2026  
**Purpose**: Identify patterns in AI V4 failures to develop systematic fine-tuning approach  
**Methodology**: Analyze specific failures across the dual-request architecture

---

## Executive Summary

This analysis examines two failure patterns from a production game:
1. **Turn 2**: Left 2 CC unused, missed optimal Surge→Knight→Tussle→DirectAttack sequence
2. **Turn 4**: Attempted to play Knight from sleep zone (illegal action)

Both failures occurred despite the dual-request V4 architecture. The analysis traces each failure through the decision pipeline to identify root causes.

---

## Turn 2 Analysis: Unused CC and Missed Optimal Play

### Context
- **Starting CC**: 4
- **Hand**: Surge, Wake, Knight, Umbruh, Paper Plane, Archer
- **Opponent Board**: 1 Umbruh (4/4)
- **Opponent Slept**: 0/6

### What Should Have Happened
**Optimal sequence**: 
```
play Surge → play Knight → tussle (sleep opponent Umbruh) → direct_attack → end_turn
CC: 5/5 spent (Surge +1, Knight 1, Tussle 2, Direct Attack 2, noting tussle clears last toy)
Sleeps: 2 (opponent's Umbruh + direct attack damage)
```

This sequence:
- Uses **all available CC** (5 total: 4 base + 1 from Surge)
- Sleeps 2 opponent cards in a single turn
- Achieves 2.5 CC/card efficiency
- Leverages the critical state change: tussle sleeping opponent's LAST toy enables direct_attack

### What Actually Happened
**Actual sequence selected (Sequence 0)**:
```
play Surge → play Knight → tussle → end_turn
CC: 2/5 spent
Sleeps: 1
Left 2 CC unused
```

---

## Request 1 Analysis (Sequence Generation)

### Request 1 Prompt Quality ✅

The prompt correctly:
1. **Identified starting CC**: `## CC: 4 (Surge adds +1, Rush adds +2 when played)` ✅
2. **Stated direct_attack unavailability**: `direct_attack: NO - opponent has 1 toys` ✅
3. **Included STATE CHANGES section**: 
   ```
   ## STATE CHANGES (CRITICAL!)
   - Tussle that sleeps opponent's LAST toy → direct_attack becomes legal!
   - Example: Surge→Knight→tussle(sleeps last toy)→direct_attack→end_turn
   ```
   ✅ **This is EXACTLY the scenario present in the game state**

4. **Provided explicit example matching the scenario**: The example in the prompt is literally what should happen ✅

5. **Tasked model with finding aggressive sequences**:
   ```
   ## TASK
   Generate 5-10 LEGAL sequences:
   1. Aggressive (maximize attacks, use ALL CC)
   2. Board-building (play toys without attacking)
   3. Conservative (minimal CC)
   4. If tussle clears opponent's board AND CC remains → INCLUDE direct_attack!
   ```
   ✅ Point #4 explicitly asks for exactly this pattern

### Request 1 Response Analysis ❌

The LLM generated 8 sequences, including:

**Sequence 0** (what was selected):
```json
"play Surge [id] -> play Knight [id] -> tussle knight->umbruh -> end_turn | CC: 2/4 spent | Sleeps: 1"
```

**Sequence 7** (Last in the list - uses more CC but still not optimal):
```json
"play Surge [id] -> play Knight [id] -> tussle knight->umbruh -> play Umbruh [id] -> end_turn | CC: 3/4 spent | Sleeps: 1"
```

**Note**: Looking at this more carefully, Sequence 7 actually plays another Umbruh after the tussle. Since the tussle would sleep the opponent's last toy, the optimal play would have been to follow with direct_attack instead of playing Umbruh.

**⚠️ CRITICAL FINDING**: None of the 8 sequences included direct_attack, despite:
- The prompt **explicitly stating** this scenario enables direct_attack
- The prompt **providing an example** of exactly this scenario
- The prompt **requesting** sequences that include direct_attack after clearing the board

#### Request 1 Root Cause Hypothesis

**The sequence generator (gemini-2.5-flash-lite, temp 0.2) failed to apply the state change rule.**

Possible reasons:
1. **Information overload**: The prompt is ~2300 chars with many rules. The STATE CHANGES section may be lost in context.
2. **Conditional logic complexity**: "If tussle clears opponent's LAST toy" requires forward-thinking that low-temperature models struggle with.
3. **Format confusion**: The model correctly calculated CC costs but didn't simulate the state change mid-sequence.
4. **Example placement**: The example is in the prompt but not near the TASK section where the model is generating.

---

## Request 2 Analysis (Strategic Selection)

### Sequences Provided to Selector

Request 2 received 8 validated sequences, all legal but suboptimal. The best available option was Sequence 0 (which it selected):
- Sleeps 1 card for 2 CC (2.0 CC/card)
- Leaves 2 CC unused

### Request 2 Decision ⚠️

**Selected**: Sequence 0  
**Reasoning**: "None of the sequences achieve a lethal check. Sequence 0 is the best as it sleeps 1 opponent card using minimal CC, prioritizing removal over board setup."

#### Request 2 Root Cause Analysis

**The strategic selector made a reasonable decision given the options it received.**

However, there are issues:
1. **CC efficiency misunderstanding**: The reasoning says "using minimal CC" is good, but the goal is **maximum CC utilization** (2.5 CC/card target means SPENDING efficiently, not SAVING).
2. **No questioning of unused CC**: Sequence 0 leaves 2 CC unused. Request 2 should recognize this is suboptimal.
3. **Lack of strategic context**: The selector didn't flag that "spending only 2 of 5 CC when opponent has 6 cards remaining is strategically bad."

The selector's **goal formulation** needs strengthening:
- Current: "minimal CC" sounds like conservation
- Should be: "maximize cards slept per turn" or "maximize CC utilization"

---

## Turn 4 Analysis: Attempted Play from Sleep Zone

### Context
- **Turn**: 4
- **Starting CC**: 6
- **Hand**: Umbruh, Archer
- **In Play**: (empty)
- **Sleep Zone**: Surge, Knight, Wake, Paper Plane

### The Failure

The plan shows:
```json
"action_sequence": [
  {"action_type": "play_card", "card_name": "Umbruh", "cc_cost": 1},
  {"action_type": "play_card", "card_name": "Knight", "cc_cost": 0},  // ❌ Knight is in sleep zone!
  {"action_type": "tussle", "cc_cost": 2},
  {"action_type": "tussle", "cc_cost": 2},
  {"action_type": "end_turn", "cc_cost": 0}
]
```

### Request 1 Prompt Analysis ✅

The prompt correctly shows:
```
## YOUR HAND (cards you can play)
- Umbruh (id=fe830919-4526-41b5-a5ab-229f2dbe2536, cost=1, STR=4, HP=4)
- Archer (id=661a2d1e-3ca1-4643-94e9-041d515ce74c, cost=0, STR=0, HP=5)

## YOUR TOYS IN PLAY (you control these - use their IDs for tussle/direct_attack)
(no toys - must play from hand first to attack)

## YOUR SLEEP ZONE (for Wake targeting)
- Surge (id=6bd2fe20-d5a9-47eb-a5cf-55a952fcea04)
- Knight (id=3fbbdfd9-66ba-4445-9cd9-05041e7792c9)
- Wake (id=003798fb-81a3-4bac-b88b-a855cd55180d)
- Paper Plane (id=001c1ab5-9765-4905-9849-a1c06aafe953)
```

**Knight is clearly listed in SLEEP ZONE, not in HAND.** ✅ Prompt is correct.

### Request 1 Response Analysis ❌

Despite the correct prompt, the LLM generated this sequence:
```
"play Umbruh [fe830919...] -> play Knight [3fbbdfd9...] -> tussle -> tussle -> end_turn | CC: 5/9 spent | Sleeps: 2"
```

**The model used Knight's ID from the sleep zone section.**

#### Request 1 Root Cause Hypothesis

**Zone confusion**: The model saw Knight's name and ID but didn't properly filter by zone context.

Possible causes:
1. **Format ambiguity**: All zones use similar formatting. The model may pattern-match card names without zone awareness.
2. **ID-based hallucination**: Once the model decided to play Knight, it retrieved an ID from the prompt (which happened to be the sleep zone instance).
3. **Name-based planning**: The model may plan with card names first ("play Knight") then search for IDs, grabbing the first match.

### Request 2 Selection Analysis

Request 2 selected Sequence 4 (the one with the illegal Knight play). The selector's reasoning:
> "Sequence 4 is the best removal option, sleeping 2 opponent cards for 5 CC..."

**Request 2 didn't validate zone legality.** It assumed all sequences from Request 1 were legal.

---

## Execution Analysis

### Turn 4 Execution Log

```json
"execution_log": [
  {
    "method": "heuristic",
    "status": "success",
    "action_index": 0,
    "planned_action": "play_card Umbruh",
    "execution_confirmed": true
  },
  {
    "method": "llm",
    "reason": "Action not available (heuristic match failed)",
    "status": "success",
    "action_index": 1,
    "planned_action": "play_card Knight"
  }
]
```

**Key observation**: 
- Action 0 succeeded with heuristic matching
- Action 1 **failed heuristic match** (because Knight isn't in hand)
- System fell back to LLM execution, which somehow succeeded (???)

**Questions**:
1. How did LLM execution "succeed" for an illegal action?
2. What action was actually executed when it said "play Knight"?
3. Did the LLM execution actually play Knight from sleep zone (impossible), or did it do something else?

This suggests a **validation gap in the execution phase**.

---

## Root Cause Summary

### Turn 2 Failure: Missed Optimal Sequence

| Stage | Status | Root Cause |
|-------|--------|------------|
| **Request 1 Prompt** | ✅ Good | Contains all necessary information and explicit example |
| **Request 1 Execution** | ❌ **FAILURE** | Model failed to apply state-change rule despite explicit instruction |
| **Request 2 Selection** | ⚠️ Suboptimal | Made best choice from bad options, but reasoning conflated "minimal CC" with "good" |
| **Execution** | ✅ Correct | Executed the (suboptimal) plan correctly |

**Primary issue**: Request 1 sequence generation doesn't reliably handle conditional state changes.

### Turn 4 Failure: Illegal Card Play

| Stage | Status | Root Cause |
|-------|--------|------------|
| **Request 1 Prompt** | ✅ Good | Correctly separated zones |
| **Request 1 Execution** | ❌ **FAILURE** | Model confused zones, used ID from sleep zone for play action |
| **Request 2 Selection** | ⚠️ Assumed legality | No validation of zone rules |
| **Execution** | ⚠️ **MYSTERIOUS** | Heuristic failed (correct), LLM fallback "succeeded" (how?) |

**Primary issue**: Request 1 doesn't properly filter cards by zone context. Secondary issue: execution validation gap.

---

## Identified Patterns

### Pattern 1: State-Change Reasoning Failure
**Symptom**: Model doesn't generate sequences that leverage mid-sequence state changes (e.g., "tussle clears board → direct attack becomes legal")  
**Frequency**: High impact  
**Challenge**: Requires forward simulation during sequence generation

### Pattern 2: Zone Context Confusion  
**Symptom**: Model generates actions using cards from wrong zones (sleep zone instead of hand)  
**Frequency**: Critical when it happens  
**Challenge**: Zone information is present but not enforced structurally

### Pattern 3: CC Efficiency Misinterpretation
**Symptom**: Request 2 reasoning conflates "minimal CC spent" with "good play"  
**Frequency**: Moderate impact  
**Challenge**: Strategic goal needs clearer framing

### Pattern 4: Execution Validation Gap
**Symptom**: Heuristic-failed actions fall back to LLM and mysteriously "succeed"  
**Frequency**: Unknown  
**Challenge**: Execution phase may not be properly validating actions

---

## Diagnostic Tools Assessment

### What We Have ✅
1. **Admin API**: Successfully retrieved AI logs for game
2. **AI Decision Logs**: Captured full prompts and responses for both requests
3. **Turn Plan Structure**: Well-structured JSON showing action sequence and execution log
4. **Execution Tracking**: Can see which actions used heuristic vs LLM execution

### What We Need ❌

1. **Request 2 Prompt Visibility**: The admin logs show `"prompt": ""` (empty!) for Request 2. We can't see what was sent to the strategic selector. This is critical for debugging.

2. **Sequence Validation Report**: We need visibility into TurnPlanValidator results. Did it flag any issues? Were sequences filtered out?

3. **Strategic Selector Full Data**: We can see the selected sequence but not:
   - The full list of sequences with tactical labels as seen by Request 2
   - Examples that were included
   - Game phase classification

4. **Execution Action Details**: When heuristic fails and LLM takes over, what was the LLM's actual response? What action was executed?

5. **Available Actions at Each Step**: What was the actual `valid_actions` list when execution tried to play Knight from sleep zone?

6. **V4 Metrics Dashboard**: We have metrics tracked but no easy way to query:
   - V2 fallback rate by scenario
   - Request 1 vs Request 2 failure modes
   - Common patterns in failed sequences

---

## Recommendations for Systematic Improvement

### 1. Fix Diagnostic Gaps (Priority 1)

#### A. Log V4 Request 2 Prompts
**Current**: Request 2 prompts are not being saved to AI decision logs  
**Fix**: Update logging to capture both Request 1 and Request 2 prompts separately

```python
# In turn_planner.py _create_plan_v4
# After Request 2 generation:
self._v4_request2_prompt = select_prompt  # Already done ✅
# But this isn't being saved to DB. Need to add separate log entry.
```

#### B. Add Sequence Validation Report
**Current**: Sequences are validated but results aren't logged  
**Fix**: Log validation details for each sequence

```python
{
  "sequence_validation": {
    "total_generated": 8,
    "passed_validation": 8,
    "failed_validation": 0,
    "validation_errors": []
  }
}
```

#### C. Enhanced Execution Logging
**Current**: Execution log shows success/failure but not details  
**Fix**: Log available actions and actual action taken

```python
{
  "method": "llm",
  "status": "success",
  "action_index": 1,
  "planned_action": "play_card Knight",
  "available_actions": [...],  # ADD THIS
  "actual_action": {...}  # ADD THIS
}
```

### 2. Prompt Architecture Improvements (Priority 2)

#### A. State-Change Rule Enforcement
**Issue**: Request 1 doesn't reliably apply state-change rules  
**Approach**: Make state changes more explicit and testable

**Option 1**: Pre-compute legal follow-ups
```
After tussle 3fbbdfd9->c76e7c4a (which sleeps opponent's LAST toy):
  → direct_attack becomes LEGAL (opponent now has 0 toys)
  → You have 3 CC remaining (enough for direct_attack)
  → RECOMMENDED: Include direct_attack in sequence
```

**Option 2**: Two-phase generation
- Phase 1a: Generate base sequences
- Phase 1b: Augment sequences with state-change opportunities

#### B. Zone-Based Card Formatting
**Issue**: Cards from different zones use same format  
**Fix**: Structurally separate zones

```
## PLAYABLE CARDS (in your hand):
- [HAND] Umbruh (id=fe830919..., cost=1, STR=4, HP=4)
- [HAND] Archer (id=661a2d1e..., cost=0, STR=0, HP=5)

## SLEPT CARDS (cannot be played without Wake):
- [SLEEP] Surge (id=6bd2fe20...)
- [SLEEP] Knight (id=3fbbdfd9...)
```

Or use schema enforcement:
```
Only use IDs from "PLAYABLE CARDS" section for play_card actions.
```

#### C. Strategic Goal Clarification
**Issue**: "Minimal CC" sounds like conservation  
**Fix**: Reframe as maximization

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

### 3. Systematic Testing Protocol (Priority 3)

#### A. Regression Test Suite
Create test cases for each identified pattern:

**Test: State-Change Direct Attack**
```python
def test_ai_v4_turn2_direct_attack_after_board_clear():
    """Verify AI generates sequences with direct_attack when tussle clears board."""
    # Setup: 4 CC, Surge + Knight in hand, 1 opponent toy
    # Expected: At least one sequence includes tussle → direct_attack
```

**Test: Zone Isolation**
```python
def test_ai_v4_zone_filtering():
    """Verify AI only uses cards from hand for play_card actions."""
    # Setup: Hand has Umbruh, Sleep zone has Knight
    # Expected: No sequences include playing Knight
```

#### B. Prompt Ablation Tests
Test prompt variations to find what works:
- Remove STATE CHANGES section → measure direct_attack inclusion rate
- Add PLAYABLE CARDS header → measure zone confusion rate
- Reword strategic goals → measure CC utilization

#### C. Model Comparison
Compare gemini-2.5-flash-lite vs gemini-2.5-flash for Request 1:
- Does flash handle state changes better?
- Is zone confusion less frequent?

---

## Next Steps

### Immediate (This Session)
1. ✅ Document findings (this file)
2. ⏭️ Identify 2-3 more games for pattern validation
3. ⏭️ Create diagnostic tool improvement tickets

### Short-term (Next PR)
1. Fix Request 2 prompt logging
2. Add sequence validation logging
3. Enhance execution logging
4. Add zone prefix to card formatting

### Medium-term (Following PRs)
1. Implement state-change pre-computation
2. Create regression test suite
3. Run prompt ablation experiments
4. Build V4 metrics dashboard

---

## Open Questions

1. **Turn 4 Execution Mystery**: How did "play Knight" from sleep zone execute successfully? Did it actually happen? What action was taken?
2. **Validation Timing**: Are sequences validated after Request 1 but before Request 2? Or only after selection?
3. **Example Selection**: What examples were chosen for Turn 2 Request 2? Did they show state-change sequences?
4. **Temperature Tuning**: Would Request 1 temp 0.4 (vs 0.2) improve state-change reasoning without generating illegal sequences?
5. **Model Selection**: Should we use gemini-2.5-flash for Request 1 instead of flash-lite for better reasoning?

---

## Conclusion

The V4 architecture is sound, but the LLM's execution has two critical failure modes:
1. **State-change reasoning**: Doesn't reliably simulate mid-sequence state changes
2. **Zone filtering**: Occasionally confuses cards across zones

Both failures occur in Request 1 (sequence generation). Request 2 makes reasonable decisions given the options but could better flag suboptimal scenarios.

The path forward is:
1. **Improve diagnostics** (log Request 2 prompts, validation results, execution details)
2. **Strengthen prompts** (zone prefixes, state-change pre-computation, goal clarification)
3. **Build regression tests** (systematically test known failure patterns)
4. **Iterate with data** (measure impact of each change through simulation)

This analysis establishes a systematic approach to AI fine-tuning based on production game data and failure pattern identification.
