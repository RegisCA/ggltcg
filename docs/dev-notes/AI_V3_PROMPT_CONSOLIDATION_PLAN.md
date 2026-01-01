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

## GitHub Issues - HONEST STATUS

**NONE of these issues have been fixed or commented on in GitHub.**

| Issue | Title | GitHub Status | Actual Status | Comments |
|-------|-------|---------------|---------------|----------|
| #267 | CC budgeting - sequential state-tracking | OPEN | Prompt has cc_after field, NOT VERIFIED | 0 |
| #268 | Exhaustive planning loop | OPEN | **NOT FIXED** - AI still ends turns early | 0 |
| #271 | CC efficiency for Drop card | OPEN | **NOT FIXED** - Backend bug, not prompt | 0 |
| #272 | Drop action card not understood | OPEN | Prompt has warning, NOT VERIFIED | 0 |
| #273 | Archer action card not understood | OPEN | Prompt has warning, NOT VERIFIED | 0 |
| #275 | Copy card not understood | OPEN | **NOT ADDRESSED** | 0 |
| #276 | Knight card not understood | OPEN | **NOT ADDRESSED** | 0 |

### Issue Details (From GitHub)

**#267 - CC budgeting**: AI doesn't track that Surge adds CC mid-turn. Plans sequences without accounting for gained CC.

**#268 - Exhaustive Planning Loop**: AI ends turn with CC remaining when it could attack more. Example: 5 CC, plays Umbruh+Drop (3 CC), ends with 2 CC left instead of adding a tussle.

**#271 - CC efficiency for Drop**: BACKEND BUG - action card sleeps not counted in efficiency tracking. Not a prompt issue.

**#272 - Drop not understood**: AI plays Drop on Turn 1 when opponent has 0 toys. Reasoning: "Use Drop to sleep an opponent's toy if they played one" - but they haven't!

**#273 - Archer not understood**: AI uses Archer ability when opponent has 0 toys. Reasoning: "this action will target a card in their hand" - WRONG, Archer only targets IN PLAY.

**#275 - Copy not understood**: AI tries to copy opponent's toys. Reasoning: "create a copy of the opponent's strongest toy (Ballaber)" - WRONG, Copy only targets YOUR toys.

**#276 - Knight not understood**: AI wastes Archer shots reducing STA before Knight tussle. Knight auto-wins regardless of target STA!

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

#### Fix F: Copy Card Targeting (#275)
Add to CARD_SPECIAL_DOCS:
```python
"Copy": """**Copy** (ACTION, 0 CC): Create exact copy of one of YOUR toys in play.
⚠️ Can ONLY target YOUR toys - NOT opponent's!
❌ Copy on opponent's toy → ILLEGAL!
Cost to play = cost of the toy being copied.""",
```

#### Fix G: Knight Efficiency (#276)
Update CARD_SPECIAL_DOCS for Knight:
```python
"Knight": """**Knight** (1 CC, 4/4/3): On YOUR turn, Knight auto-wins ALL tussles.
  - Opponent toy ALWAYS sleeped, Knight takes 0 damage
  - ✅ No need to reduce target STA first - Knight wins regardless!
  - ⚠️ Only works on Knight's CONTROLLER's turn
  - If OPPONENT has Knight and it's YOUR turn: Knight fights normally""",
```

#### Fix H: Drop Targeting (#272)
Update CARD_SPECIAL_DOCS for Drop:
```python
"Drop": """**Drop** (ACTION, 2 CC): Sleep 1 target toy IN PLAY.
⚠️ REQUIRES TARGET IN PLAY: Opponent must have 1+ toys NOW!
❌ 0 opponent toys = Drop is USELESS (no valid target!)
❌ Turn 1 trap: As Player 1, opponent has 0 toys - DON'T play Drop!""",
```

#### Fix I: Archer Targeting (#273)
Update CARD_SPECIAL_DOCS for Archer to be clearer:
```python
"Archer": """**Archer** (0 CC, 0/0/5): CANNOT tussle or direct attack!
  - Ability: 1 CC → Remove 1 STA from target opponent toy **IN PLAY**
  - ⚠️ ONLY targets toys IN PLAY - cannot target hand!
  - ❌ 0 opponent toys = CANNOT USE ABILITY (no valid target!)
  - ❌ DO NOT plan Archer ability if opponent has 0 toys!""",
```

### Step 3: Backend Fix for #271
This is NOT a prompt issue. In `game_engine.py`, when action card effects sleep opponent cards, must call the tracking method.

### Step 4: Remove Redundancy
After applying fixes, search for and remove:
- Duplicate explanations of tussle vs direct_attack
- Repeated mentions of "opponent must have 0 toys"
- Any section that says the same thing twice

### Step 5: Test After EACH Fix
Run test suite after each individual fix:
```bash
pytest backend/tests/test_ai_turn1_planning.py -v
```

### Step 6: Comment on GitHub Issues
For EACH issue addressed, add a GitHub comment documenting:
1. What was changed in the prompt
2. What test verifies the fix
3. Test results

### Step 7: Close Issues Only When Verified
Only close an issue when:
- Test exists and passes
- GitHub comment documents the fix

---

## Test Gaps to Address

### Existing Tests (Keep)
1. `TestTurn1WithSurge` - Surge CC bridge (#267)
2. `TestTurn1DropTrap` - Drop targeting (#272)
3. `TestTurn1ArcherTrap` - Archer targeting (#273)
4. `TestSleepZoneTrap` - Wake requirement
5. `TestWinningTussle` - Tussle vs direct attack
6. `TestTurn1CCMathValidation` - CC math

### Tests to Create

#### For #275 - Copy Card
```python
class TestCopyTrap:
    def test_copy_only_targets_own_toys(self, turn_planner):
        """Verify Copy cannot target opponent's toys."""
        # Setup: AI has Copy, opponent has Ballaber in play, AI has Umbruh in play
        # Expected: If Copy used, targets AI's Umbruh, NOT opponent's Ballaber
```

#### For #276 - Knight Efficiency
```python
class TestKnightEfficiency:
    def test_no_wasted_archer_before_knight(self, turn_planner):
        """Verify AI doesn't waste Archer shots before Knight tussle."""
        # Setup: AI has Knight and Archer in play, opponent has Umbruh
        # Expected: AI tussles with Knight directly (auto-wins)
        # NOT: Archer ability + Knight tussle (wastes CC)
```

#### For #268 - Exhaustive Planning
```python
class TestExhaustivePlanning:
    def test_uses_all_available_cc(self, turn_planner):
        """Verify AI continues attacking until CC < 2."""
        # Setup: AI has 5 CC, Umbruh in play, opponent has Knight + Wizard
        # Expected: Multiple tussles until CC exhausted
        # NOT: Single action then end turn with CC remaining
```

#### For Combat Math
```python
class TestCombatMath:
    def test_attacker_wins_clean(self, turn_planner):
        """Verify AI predicts only 1 card sleeped in attacker-advantage tussle."""
        # Setup: AI Umbruh vs Opponent Umbruh (identical 4/4/4 stats)
        # Expected: expected_cards_slept = 1 (attacker wins, no counter)
        # NOT: expected_cards_slept = 2 (mutual destruction is WRONG)

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
- [ ] Prompt restored from baseline 8cb654e
- [ ] Fixes A-I applied ONE AT A TIME with tests between
- [ ] Prompt is ≤500 lines
- [ ] All existing tests pass
- [ ] Tests created for #275 (Copy), #276 (Knight), #268 (exhaustive)
- [ ] GitHub comments added to ALL 7 issues documenting fixes
- [ ] Issues closed ONLY when test passes and comment added
- [ ] 2-3 real games played without hallucinations

---

## Prompt for Fresh Session

Use this to start a new session:

```
I need help consolidating my AI prompt for a card game. Two previous sessions made things worse. I need a methodical approach.

**Context:**
- Game: GGLTCG (card battle game)
- AI Model: Gemini 2.5 Flash Lite (needs clear, structured prompts)
- Stable baseline: Git commit 8cb654e
- Current state: 514 lines with patches and bugs, NO issues actually fixed

**CRITICAL: Work methodically!**
1. Restore prompt from baseline commit 8cb654e FIRST
2. Apply fixes ONE AT A TIME
3. Run tests after EACH fix
4. Comment on GitHub issues when fixes verified
5. Do NOT claim fixed until test passes

**The 7 open GitHub issues (NONE are fixed):**
- #267: CC budgeting - AI doesn't track Surge adds CC mid-turn
- #268: Exhaustive loop - AI ends turn early when it could attack more  
- #271: Backend bug - action card sleeps not counted (NOT a prompt fix)
- #272: Drop played without valid targets
- #273: Archer ability used without valid targets
- #275: Copy targets opponent's toys (should only target own)
- #276: Knight - AI wastes actions before Knight auto-win tussle

**Additional bugs found this session:**
- Combat math: AI thinks trades kill both (ignores attacker SPD bonus)
- Efficiency: AI counts own sleeped cards (should only count opponent's)
- Hallucination: AI tried direct_attack when opponent had toys
- Zone error: AI tried to play card from Sleep Zone without Wake

**Key files:**
- Main prompt: backend/src/game_engine/ai/prompts/planning_prompt_v2.py
- Tests: backend/tests/test_ai_turn1_planning.py
- Full plan: docs/dev-notes/AI_V3_PROMPT_CONSOLIDATION_PLAN.md
- Gemini recommendations: docs/dev-notes/AI_V3_FOLLOWUP_PLAN.md (lines 190-300)

**MUST READ the consolidation plan document before starting.**
It contains exact text for each fix (A through I) and what test to run.

**Rules:**
- Do NOT add explanatory prose - use tables and bullet points
- Do NOT duplicate information - single source of truth  
- Make ONE change at a time with tests between
- Comment on GitHub issues when fixes verified
- Prompt must stay under 500 lines
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
