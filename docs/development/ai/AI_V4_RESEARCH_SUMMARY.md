# AI V4 Research Summary

**Session Date**: January 3, 2026  
**Game Analyzed**: `5c54f1b8-2471-4e93-a12a-1369a43bc01b`  
**Full Analysis**: [AI_V4_GAME_ANALYSIS_5c54f1b8.md](./AI_V4_GAME_ANALYSIS_5c54f1b8.md)

---

## Key Findings

### Two Critical Failure Modes Identified

#### 1. State-Change Reasoning Failure (Turn 2)
**What happened**: AI left 2 CC unused and missed the optimal play sequence  
**Root cause**: Request 1 failed to generate sequences leveraging mid-sequence state changes  
**Example**: Didn't recognize that "tussle (sleep last toy) → direct_attack becomes legal"  
**Impact**: High - directly reduces CC efficiency and game performance

#### 2. Zone Context Confusion (Turn 4)  
**What happened**: AI attempted to play Knight from sleep zone  
**Root cause**: Request 1 confused zones when retrieving card IDs  
**Example**: Used Knight's ID from "YOUR SLEEP ZONE" section for play_card action  
**Impact**: Critical - generates illegal actions, causes execution failures

### The Prompts Were Actually Good

Both failures occurred **despite correct prompts**:
- Turn 2 prompt explicitly included state-change example matching the scenario
- Turn 4 prompt clearly separated hand from sleep zone

**This means the issue is LLM reasoning, not missing information.**

---

## Diagnostic Tool Gaps

### Critical Gaps Found

1. **Request 2 Prompts Not Logged**: Admin API shows empty `"prompt": ""` for Request 2. We can't see what was sent to strategic selector.

2. **Validation Results Not Visible**: Can't see which sequences passed/failed validation or why.

3. **Execution Details Missing**: When heuristic fails and LLM takes over, we don't see:
   - What `valid_actions` were available
   - What action was actually executed
   - Why the "illegal" action succeeded (mystery from Turn 4)

4. **V4 Request Separation**: AI logs show combined view, making it hard to trace Request 1 → validation → Request 2 → selection flow.

### Tool Improvements Needed

**Priority 1 - Logging Enhancements**:
```python
# Add separate log entries for V4:
- Request 1 (sequence generation) - prompt + response + validation results
- Request 2 (strategic selection) - prompt + response + selected sequence
- Execution (each action) - available actions + actual action + match status
```

**Priority 2 - Admin UI Enhancements**:
- V4 turn view showing dual-request flow
- Sequence validation report
- Execution trace with action matching

---

## Identified Patterns for Systematic Testing

### Pattern 1: Mid-Sequence State Changes
**Test scenario**: Opponent has 1 toy, AI has Surge + Knight + 4 CC  
**Expected**: Generate sequence with tussle → direct_attack  
**Current result**: ❌ Omits direct_attack

### Pattern 2: Zone-Based Card Availability
**Test scenario**: Hand = [Umbruh], Sleep = [Knight], Plan = play Knight  
**Expected**: Reject as illegal (Knight not in hand)  
**Current result**: ❌ Generates sequence with Knight from sleep zone

### Pattern 3: Full CC Utilization  
**Test scenario**: 5 CC available, best sequence uses only 3 CC  
**Expected**: Flag as suboptimal or generate better sequence  
**Current result**: ⚠️ Selects low-CC sequence, reasoning says "minimal CC" is good

---

## Recommended Next Steps

### Phase 1: Improve Diagnostics (Essential for Further Research)
1. ✅ **This session**: Document findings
2. **Next PR**: 
   - Log Request 2 prompts separately
   - Add sequence validation results to logs
   - Enhance execution logging with available actions
3. **Following PR**:
   - Build V4-specific admin viewer showing dual-request flow
   - Add metrics dashboard for failure mode tracking

### Phase 2: Prompt Architecture Fixes (Based on Patterns)
1. **Zone Confusion Fix**:
   - Add zone prefix to card names: `[HAND] Umbruh` vs `[SLEEP] Knight`
   - Explicitly state: "Only cards in HAND section can be played"
   - Consider schema enforcement

2. **State-Change Enhancement**:
   - Pre-compute state changes: "After this tussle, opponent will have 0 toys"
   - Make follow-up actions explicit: "Then direct_attack becomes legal"
   - Possibly split into two-phase generation

3. **Strategic Goal Clarification**:
   - Reframe "minimal CC" → "maximum CC utilization"
   - Add explicit warning: "Leaving 2+ CC unused is wrong"
   - Emphasize cards slept per turn over CC conservation

### Phase 3: Regression Testing (Validate Fixes)
1. Create test suite for each failure pattern
2. Run ablation tests on prompt variations
3. Compare models (flash-lite vs flash) for Request 1
4. Measure improvement through simulation metrics

---

## Open Questions for Further Investigation

1. **Turn 4 Mystery**: How did "play Knight from sleep" execute successfully? What actually happened?
2. **Model Selection**: Would gemini-2.5-flash (vs flash-lite) handle state changes better?
3. **Temperature Tuning**: Would Request 1 temp 0.4 (vs 0.2) improve reasoning without generating illegal moves?
4. **Example Impact**: What examples were shown in Turn 2 Request 2? Did they demonstrate state-change sequences?
5. **Validation Timing**: Are sequences validated after Request 1 or after Request 2 selection?

---

## Conclusion: A Clear Path Forward

The V4 architecture fundamentally works, but LLM execution has systematic failure modes. We now have:

✅ **Identified patterns**: State-change reasoning failure and zone confusion  
✅ **Traced root causes**: Request 1 generation issues, not prompt quality  
✅ **Found tool gaps**: Missing Request 2 logs, validation visibility, execution details  
✅ **Defined test scenarios**: Specific cases to validate improvements  
✅ **Established methodology**: Data-driven approach using production game analysis  

Next session should focus on:
1. Analyzing 2-3 more games to validate patterns
2. Implementing diagnostic improvements (Request 2 logging)
3. Creating regression tests for known failure modes
4. Testing first prompt fix (zone prefixes)

This establishes a systematic, measurable approach to AI fine-tuning based on production data rather than intuition.
