# AI v3.1 Prompt Optimization - Session Analysis

## Date: January 1, 2026

## Objective
Implement Gemini's "Protocol-style" recommendations to improve AI decision-making, addressing issues #267, #268, #271, #272, #273, #275, #276.

## Gemini's Original Recommendations

1. **Dynamic State Tagging** - Inject `[NO TUSSLE]` restrictions at card level
2. **ACTION REGISTRY** - Consolidate action types with costs in a table
3. **PRE-ACTION CHECKLIST** - Permission → Resource → Target checks
4. **HARD CONSTRAINTS** - Numbered list of violations
5. **ZERO-ACTION AUDIT** - Require justification if ending with CC >= 2

## What Was Working (Commit 8cb654e)

The committed Protocol restructure had:
- ACTION REGISTRY with clear table format
- PRE-ACTION CHECKLIST with 3 categories
- EXECUTION PROTOCOL with Priority Order (1-6)
- HARD CONSTRAINTS (9 numbered rules)
- ZERO-ACTION AUDIT requirement
- ~464 lines, structured and comprehensive

**Successful Turn 1 Example** (from earlier in session):
```
CC: 2 → 0  Target: Sleep 1 cards  Efficiency: 2.00 CC/card
1. ✅ play_card Surge (0 CC)
2. ✅ play_card Knight (1 CC)
3. ✅ direct_attack Knight (2 CC)
4. ✅ end_turn (0 CC)
```

## Changes Made After Commit (Uncommitted)

| Change | Intent | Result |
|--------|--------|--------|
| Paper Plane doc rewrite | Clarify direct attack targets HAND not toys | May have introduced confusion |
| Drop, Twist, Copy, Sun - added `target_ids` requirements | Fix Wake targeting issue | Good - needed |
| Removed ACTION REGISTRY columns | Simplify | Lost important info (attacker requirements) |
| Removed PRE-ACTION CHECKLIST | Simplify | Lost systematic validation |
| Replaced EXECUTION PROTOCOL with TURN PLANNING ALGORITHM | Simplify | Lost Priority Order |
| Removed HARD CONSTRAINTS section | Absorbed into other sections | Lost numbered rules |
| Removed ZERO-ACTION AUDIT | Replaced with STOP condition | Lost explicit justification requirement |
| Added "DIRECT ATTACK BLOCKER" section | Fix bypass confusion | Added but may conflict |
| Changed tussle math format | Show "Will I sleep them?" | Good simplification |
| Reduced from 464 to 436 lines | Efficiency | But lost structure |

## Problems Identified

### 1. Loss of Structure
The committed version had clear, numbered sections. The current version is more prose-like and harder to follow systematically.

### 2. Conflicting Instructions
- Multiple sections mention tussle vs direct attack rules
- "DIRECT ATTACK BLOCKER" section repeats attack loop content
- No single source of truth

### 3. Lost Systematic Validation
The PRE-ACTION CHECKLIST forced step-by-step validation:
1. PERMISSION CHECK
2. RESOURCE CHECK  
3. TARGET CHECK

This was replaced with a less structured algorithm.

### 4. Lost Priority Order
The original had explicit priority:
1. WIN CHECK
2. TUSSLE
3. DIRECT ATTACK
4. ABILITIES
5. DEFEND
6. END TURN

This guided decision-making sequentially.

### 5. CC Math Issues
The AI is outputting `cc_start: 0` when game state shows `CC: 2/7`. This suggests the AI isn't correctly reading the game state, which is a schema/extraction issue separate from prompt content.

## Recommendation: Revert and Selectively Re-apply

### Keep from Current Changes:
1. ✅ `target_ids` requirements for Wake, Drop, Twist, Copy, Sun
2. ✅ Paper Plane clarification (direct attack targets HAND)
3. ✅ Simplified tussle math ("Will I sleep them?")

### Restore from Commit 8cb654e:
1. ACTION REGISTRY with attacker requirements column
2. PRE-ACTION CHECKLIST structure
3. EXECUTION PROTOCOL with Priority Order
4. HARD CONSTRAINTS numbered list
5. ZERO-ACTION AUDIT section

### New Approach:
Instead of constantly editing PLANNING_INSTRUCTIONS, we should:
1. Revert to the working committed version
2. Apply ONLY the `target_ids` documentation fixes
3. Test thoroughly before making further changes
4. Make one change at a time with testing between

## Action Plan

1. **Revert** `planning_prompt_v2.py` to commit 8cb654e
2. **Re-apply** only the `target_ids` documentation for Wake, Drop, Twist, Copy, Sun
3. **Test** Turn 1 to verify Surge+Knight+direct_attack works
4. **Commit** if working
5. **Then** address any remaining issues one at a time

## Root Cause of Regressions

The session started well but degraded because:
1. Each fix was applied without re-testing basic scenarios
2. Changes accumulated without understanding interactions
3. Structure was lost in favor of adding more explanatory text
4. No baseline test suite to catch regressions immediately

## Lesson Learned

Prompt engineering requires:
- A stable baseline to compare against
- Minimal changes per iteration
- Testing the same scenarios after each change
- Preserving working structure rather than rewriting
