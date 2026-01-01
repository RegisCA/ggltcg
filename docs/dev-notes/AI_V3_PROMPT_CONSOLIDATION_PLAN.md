# AI v3 Prompt Consolidation Plan

## Executive Summary

Two Opus 4.5 sessions have degraded a working AI prompt baseline. This document provides everything needed for a fresh session to restore and properly optimize the prompt.

**Stable Baseline**: Commit `8cb654e` - "refactor(ai): Implement Protocol-style prompt restructure"
**Current State**: Prompt has grown to 514 lines with patches, conflicting instructions, and bugs

---

## The Core Problem

The AI is using **Gemini 2.5 Flash Lite** - a fast, lightweight model. The prompt must be:
- Crystal clear with no ambiguity
- Structured for systematic decision-making
- Minimal - every word must earn its place
- Tested against specific failure cases

Instead, we've been adding explanatory text that creates confusion and contradictions.

---

## What Was Working at Baseline (8cb654e)

The baseline prompt (~464 lines) had Gemini's recommended structure:

### 1. ACTION REGISTRY (Table Format)
```
| Action | Cost | Attacker Requirement |
|--------|------|---------------------|
| tussle | 2 CC | TOY in play with STR > 0 |
| direct_attack | 2 CC | TOY in play, opponent has 0 toys |
```

### 2. PRE-ACTION CHECKLIST
```
1. PERMISSION CHECK - Is card in correct zone?
2. RESOURCE CHECK - Do I have enough CC?
3. TARGET CHECK - Is target in play?
```

### 3. EXECUTION PROTOCOL with Priority Order
```
1. WIN CHECK → Sleep opponent's last cards?
2. TUSSLE → Opponent has toys? Attack!
3. DIRECT ATTACK → Opponent has 0 toys? Attack hand!
4. ABILITIES → Archer ability (1 CC)
5. DEFEND → No toys? Play one.
6. END TURN → Nothing else possible.
```

### 4. HARD CONSTRAINTS (Numbered)
```
1. [NO TUSSLE] tag → Cannot attack
2. STR = 0 → Cannot attack
3. cc_after < 0 → ILLEGAL
... etc
```

### 5. ZERO-ACTION AUDIT
Requires justification if ending with CC >= 2.

---

## What Broke and Why

### Session 1 Issues
- Removed structure in favor of prose
- Lost ACTION REGISTRY columns
- Lost PRE-ACTION CHECKLIST
- Lost numbered HARD CONSTRAINTS

### Session 2 Issues (Current)
- Added patches without consolidation
- Prompt grew to 514 lines
- Added redundant explanations
- Combat math still wrong
- Efficiency definition wrong

### Specific Bugs Still Present

#### Bug 1: Combat Math - Attacker Advantage Ignored
**Symptom**: AI said "both Umbruh sleeped" in a trade
**Reality**: Attacker gets +1 SPD, strikes first, defender dies before counter-attacking
**Location in prompt**: TUSSLE COMBAT MATH section says "Higher SPD (attacker +1 bonus) attacks first" but AI doesn't apply it

**Fix needed**: Make the implication explicit:
```
Attacker gets +1 SPD bonus → Usually attacks FIRST → If attacker kills defender, NO COUNTER-ATTACK!
```

#### Bug 2: Efficiency Counts Own Cards
**Symptom**: AI reported "2 CC / 2 cards = 1.0" counting its own sleeped card
**Reality**: Efficiency = CC spent / OPPONENT cards sleeped
**Location in prompt**: Header says "per opponent card slept" but not reinforced

**Fix needed**: In efficiency calculation:
```
CC Efficiency = CC spent / OPPONENT cards slept (YOUR cards don't count!)
```

#### Bug 3: Direct Attack When Opponent Has Toys
**Symptom**: AI tried direct_attack when opponent clearly had Umbruh in play
**Cause**: AI hallucinated "opponent has no toys"
**Fix added this session**: BOARD REALITY CHECK step (verify opponent toy count)

#### Bug 4: Playing Cards from Sleep Zone
**Symptom**: AI tried to play Knight directly from Sleep Zone
**Cause**: Didn't understand Wake returns to HAND first
**Fix added this session**: HARD CONSTRAINT #10, ZONE CHECK section

---

## GitHub Issues Being Addressed

| Issue | Title | Status |
|-------|-------|--------|
| #267 | CC budgeting - sequential state-tracking | ✅ Fixed (cc_after field) |
| #268 | Exhaustive planning loop | ⚠️ Partial (priority order exists) |
| #271 | CC efficiency for Drop card | ❌ Not fixed |
| #272 | Drop action card not understood | ✅ Fixed (target constraints) |
| #273 | Archer action card not understood | ✅ Fixed (target constraints) |

---

## Gemini's Original Recommendations (DO NOT IGNORE)

From `AI_V3_FOLLOWUP_PLAN.md` lines 190-220:

### 1. Persona
```
## PERSONA: Aggressive Board Maximizer
Your goal is to SLEEP AS MANY OPPONENT CARDS AS POSSIBLE each turn.
```

### 2. Exhaustive Loop Requirement
```
Generate actions until BOTH conditions are met:
1. CC < 2 (cannot afford any more actions)
2. No valid targets remain
```

### 3. Verification Checklist
```
□ Did I end with ≥2 CC remaining? → Why couldn't I attack?
□ Are there opponent toys I could tussle? → Why didn't I?
□ Did I maximize cards slept this turn?
```

### 4. residual_cc_justification Field
Added to schema - requires explanation of leftover CC.

---

## Files to Modify

### Primary: `backend/src/game_engine/ai/prompts/planning_prompt_v2.py`
- Current: 514 lines
- Target: ~450 lines (consolidate, don't grow)
- Action: Start from baseline 8cb654e, selectively add ONLY what's needed

### Secondary: `backend/src/game_engine/ai/prompts/formatters.py`
- Fixed this session: Opponent hand display for 0 cards
- Keep this change

### Tests: `backend/tests/test_ai_turn1_planning.py`
- Current: 8 tests
- All pass but some validate wrong things
- Need to add combat math accuracy test

---

## Consolidation Steps

### Step 1: Restore Baseline
```bash
git checkout 8cb654e -- backend/src/game_engine/ai/prompts/planning_prompt_v2.py
```

### Step 2: Re-apply ONLY These Fixes

#### Fix A: HARD CONSTRAINT #10 (Sleep Zone)
Add to HARD CONSTRAINTS section:
```
10. **play_card from SLEEP ZONE** → ILLEGAL! Use Wake first to return card to hand.
```

#### Fix B: Combat Math Clarity
Replace existing combat math with:
```
## TUSSLE COMBAT MATH

Damage = Attacker's STR
Target sleeped when: STA - Damage <= 0

**SPD RESOLUTION** (CRITICAL!):
1. Compare SPD: Attacker gets +1 bonus
2. Higher SPD attacks FIRST
3. If first attack kills target → NO COUNTER-ATTACK!
4. SPD tie → simultaneous damage (both may die)

**Example - Attacker Wins Clean**:
Your Umbruh (4/4/4) attacks Opponent's Umbruh (4/4/4)
- Your SPD: 4+1 = 5 (attacker bonus)
- Opponent SPD: 4
- You attack first: 4 STR vs 4 STA → Opponent SLEEPED
- Opponent cannot counter-attack (already sleeped!)
- Result: 1 opponent card sleeped, your Umbruh takes 0 damage
```

#### Fix C: Efficiency Definition
In header, change:
```
Maximize CC efficiency (target: <=2.5 CC per opponent card slept)
```
To:
```
CC EFFICIENCY = CC spent ÷ OPPONENT cards sleeped (your own cards don't count!)
Target: ≤2.5 CC per opponent card slept
```

#### Fix D: BOARD REALITY CHECK
Add to EXECUTION PROTOCOL after STEP 1:
```
**STEP 2: VERIFY OPPONENT BOARD**
Count opponent toys IN PLAY from "Opponent's Toys (THREATS)" section:
- 1+ toys → MUST use tussle (direct_attack is illegal!)
- 0 toys → direct_attack is legal (no target_ids needed)
```

#### Fix E: Zone Check (already in prompt, keep it)
```
**ZONE CHECK for card_id**:
- play_card: card_id MUST be from Hand section
- tussle/direct_attack/activate_ability: card_id MUST be from Your Toys (In Play)
```

### Step 3: Remove Redundancy
After applying fixes, search for and remove:
- Duplicate explanations of tussle vs direct_attack
- Repeated mentions of "opponent must have 0 toys"
- Any section that says the same thing twice

### Step 4: Test
Run full test suite:
```bash
pytest backend/tests/test_ai_turn1_planning.py -v
```

All 8 tests should pass. Then run 2-3 real games to verify.

---

## Test Gaps to Address

### Missing Test: Combat Math Accuracy
```python
def test_combat_math_attacker_wins_clean(self, turn_planner):
    """Verify AI understands attacker advantage means no counter-attack."""
    # Setup: Your Umbruh vs Opponent Umbruh (identical stats)
    # Expected: AI says 1 card sleeped (not 2!)
    # Expected: AI understands attacker takes 0 damage
```

### Missing Test: Efficiency Only Counts Opponent
```python
def test_efficiency_only_counts_opponent_cards(self, turn_planner):
    """Verify efficiency calculation excludes own cards."""
    # Setup: Trade scenario where both cards die
    # Expected: efficiency = CC / 1 (not CC / 2)
```

---

## What NOT to Do

1. ❌ Don't add explanatory prose - use tables and bullet points
2. ❌ Don't duplicate information - single source of truth
3. ❌ Don't add examples for every edge case - keep examples minimal
4. ❌ Don't grow the prompt beyond 500 lines
5. ❌ Don't make changes without running the test suite

---

## Success Criteria

After consolidation:
- [ ] Prompt is ≤450 lines
- [ ] All 8 existing tests pass
- [ ] New combat math test passes
- [ ] New efficiency test passes
- [ ] 3 real games played without hallucinations
- [ ] AI correctly identifies winning tussle opportunities
- [ ] AI never tries direct_attack when opponent has toys

---

## Prompt for Fresh Session

Use this to start a new session:

```
I need help consolidating my AI prompt for a card game. The prompt has grown messy over two debugging sessions and needs to be cleaned up.

**Context:**
- Game: GGLTCG (card battle game)
- AI Model: Gemini 2.5 Flash Lite (fast, lightweight - needs clear, structured prompts)
- Stable baseline: Git commit 8cb654e
- Current state: 514 lines with patches and bugs

**What I need:**
1. Restore prompt from baseline commit 8cb654e
2. Apply ONLY these specific fixes (documented in docs/dev-notes/AI_V3_PROMPT_CONSOLIDATION_PLAN.md):
   - Fix A: HARD CONSTRAINT #10 (Sleep Zone cards need Wake)
   - Fix B: Combat math clarity (attacker SPD bonus = no counter-attack)
   - Fix C: Efficiency only counts opponent cards
   - Fix D: BOARD REALITY CHECK step
   - Fix E: Zone check (already exists, keep it)
3. Remove any redundant/duplicate explanations
4. Ensure prompt stays under 450 lines
5. Run test suite to verify nothing broke

**Key files:**
- Main prompt: backend/src/game_engine/ai/prompts/planning_prompt_v2.py
- Tests: backend/tests/test_ai_turn1_planning.py
- Plan doc: docs/dev-notes/AI_V3_PROMPT_CONSOLIDATION_PLAN.md
- Gemini recommendations: docs/dev-notes/AI_V3_FOLLOWUP_PLAN.md (lines 190-300)

**Critical rules:**
- Do NOT add explanatory prose - use tables and bullet points
- Do NOT duplicate information
- Make ONE change at a time and run tests between changes
- The prompt must be optimized for Gemini 2.5 Flash Lite

Please read the consolidation plan document first, then proceed step by step.
```

---

## Appendix: Key Commits

| Commit | Description | Status |
|--------|-------------|--------|
| `8cb654e` | Protocol-style restructure (BASELINE) | ✅ Stable |
| `8f5e03b` | CC math tracking and Turn 1 tests | ⚠️ Good tests, some prompt changes |
| `2ff8d2e` | Sleep Zone constraint and test | ⚠️ Good constraint, prompt growing |
| (uncommitted) | Board reality check, winning tussle | ⚠️ Good ideas, needs consolidation |

---

## Appendix: The 8 Current Tests

1. `TestTurn1WithSurge::test_turn1_surge_knight_direct_attack` - Surge CC bridge
2. `TestTurn1DropTrap::test_drop_without_targets_not_played` - Drop targeting
3. `TestTurn1ArcherTrap::test_archer_ability_without_targets` - Archer targeting
4. `TestSleepZoneTrap::test_cannot_play_card_from_sleep_zone` - Wake requirement
5. `TestWinningTussle::test_must_tussle_to_win_not_direct_attack` - Tussle vs direct
6. `TestTurn1CCMathValidation::test_cc_math_consistency` - CC math
7. `TestTurn1Regression::test_turn1_regression_suite` - Combined regression
8. (Note: TestTurn1WithSurge has a second test for affordability)
