# AI v3.1 Prompt Optimization - Session Analysis

## Date: January 1, 2026

## Current Status: NEEDS CONSOLIDATION

**Prompt size**: 514 lines (growing)
**Tests**: 8 tests, all passing but validating wrong things
**Core issues remaining**:
1. ❌ Combat math wrong - AI thinks trades are mutual destruction (ignores attacker SPD bonus)
2. ❌ Efficiency calculation counts own cards (should only count OPPONENT's cards slept)
3. ❌ Prompt growing without consolidation - adding fixes on top of fixes
4. ⚠️ May have overwritten working Gemini recommendations

## Gemini's Original Recommendations (from AI_V3_FOLLOWUP_PLAN.md)

1. **Sequential CC State-Tracking** - `cc_after_action` field per action ✅ Implemented
2. **Persona: Aggressive Board Maximizer** - Goal: sleep opponent cards ✅ Implemented
3. **Exhaustive Action Loop** - Continue until CC<2 AND no targets ✅ Implemented
4. **Card Targeting Constraints** - Drop/Archer require in-play targets ✅ Implemented
5. **residual_cc_justification** - Explain leftover CC ✅ Implemented
6. **Few-Shot Examples** - Worked examples ✅ Have examples

## Changes Made This Session

### Commit 8f5e03b - CC Math Improvements
- Strengthened CC MATH section with step-by-step verification
- Added "STOP AND VERIFY" warning
- Created Turn 1 test suite (5 tests)

### Commit 2ff8d2e - Sleep Zone Constraint
- Added HARD CONSTRAINT #10: play_card from SLEEP ZONE is illegal
- Added Wake example showing proper card recovery
- Added ZONE CHECK section
- New test: TestSleepZoneTrap

### Uncommitted Changes (Current)
- Fixed opponent hand display: "0 cards - EMPTY, no hand cards to attack!" 
- Added BOARD REALITY CHECK step (verify opponent toys before planning)
- Expanded WIN CHECK priority with TRADING WINS explanation
- Added trade example in combat math
- New test: TestWinningTussle

## Known Bugs Still Present

### 1. Combat Math - Attacker Advantage Not Understood
AI said "Cards Slept: 2 (both Umbruh)" when in fact:
- Attacker gets +1 SPD bonus (5 vs 4)
- Attacker strikes first
- Defender sleeped before counter-attack
- **Only defender dies, attacker takes 0 damage**

The prompt says "Higher SPD (attacker +1 bonus) attacks first" but AI doesn't apply it.

### 2. Efficiency Counts Own Cards
AI reported efficiency as "2 CC / 2 cards" counting its own Umbruh.
Should be: "2 CC / 1 opponent card = 2.0 efficiency"

The prompt header says "Maximize CC efficiency (target: <=2.5 CC per opponent card slept)" but this isn't reinforced.

## Prompt Size Analysis

```
Current: 514 lines
Baseline (8cb654e): ~464 lines
Growth: +50 lines (10% increase)
```

Added sections this session:
- HARD CONSTRAINT #10 (3 lines)
- Wake example (8 lines)
- ZONE CHECK (4 lines)
- BOARD REALITY CHECK step (5 lines)
- WIN CHECK expansion (4 lines)
- Trade example (6 lines)
- Opponent toys count in post-action audit (1 line)

## Test Coverage

| Test | What It Validates | Blind Spots |
|------|-------------------|-------------|
| TestTurn1WithSurge | Surge CC bridge works | Doesn't check expected_cards_slept accuracy |
| TestTurn1DropTrap | Drop not played without targets | - |
| TestTurn1ArcherTrap | Archer ability not used without targets | - |
| TestSleepZoneTrap | Wake used before sleep zone cards | - |
| TestWinningTussle | Tussle used when opponent has toys | Doesn't validate combat math reasoning |
| TestTurn1CCMathValidation | CC math doesn't go negative | - |
| TestTurn1Regression | Combined regression | Same blind spots |

**Missing test coverage**:
- Combat math accuracy (attacker advantage)
- Efficiency calculation (opponent cards only)
- Mid-game exhaustive planning (#268)

## Recommendation

### Option A: Continue Iterating (Current Path)
- Fix combat math clarity in prompt
- Fix efficiency definition
- Run tests, commit
- Risk: Prompt keeps growing, may lose coherence

### Option B: Consolidate and Optimize
- Review entire prompt for redundancy
- Remove duplicate explanations
- Tighten language for Gemini 2.5 Flash Lite
- May break things temporarily but results in cleaner prompt

### Option C: User Testing First
- Commit current changes
- User tests real games
- Gather more failure cases
- Prioritize based on real-world impact

## Files Modified This Session

- `backend/src/game_engine/ai/prompts/planning_prompt_v2.py` - Main prompt
- `backend/src/game_engine/ai/prompts/formatters.py` - Opponent hand display
- `backend/tests/test_ai_turn1_planning.py` - Test suite (8 tests)
- `docs/dev-notes/ai-v3.1-session-analysis.md` - This file

## Commits Made

1. `8f5e03b` - CC math tracking and Turn 1 tests
2. `2ff8d2e` - Sleep Zone card constraint and test
3. (uncommitted) - Winning tussle, board reality check, hand display fix

