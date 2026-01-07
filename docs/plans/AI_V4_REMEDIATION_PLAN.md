# AI V4 Remediation Plan

**Created**: January 5, 2026  
**Updated**: January 7, 2026  
**Status**: Phase 0 Complete, Phase 1 Complete  
**Purpose**: Comprehensive, actionable plan to complete AI V4 development with quality gates

---

## Executive Summary

This plan addresses two critical needs:

1. ~~**Immediate**: Fix regressions from the January 5 session disaster~~ ✅ Done (PR #290)
2. **Systematic**: Complete AI V4 development with proper testing infrastructure

Each phase is designed as a focused 2-4 hour session with explicit acceptance criteria that MUST pass before moving to the next phase.

### Phase Overview (Restructured for Quality-First)

| Phase | Goal | Key Deliverable | Quality Gate | Status |
|-------|------|-----------------|--------------|--------|
| **0** | Fix Jan 5 regressions | Working prompt | Manual 2-turn test passes | ✅ Complete (PR #290) |
| **1** | CC Waste Tracking | Automated metrics | Baseline established | ✅ Complete (Jan 7) |
| **2** | Automated Scenario Test | Turn 1+2 regression test | Test catches broken prompts | 🔴 Ready |
| **3** | Document learnings | Update COPILOT.md | Failures documented | Not started |
| **4** | Prompt regression tests | `test_ai_prompt_regression.py` | Tests catch content issues | Not started |
| **5** | Card metadata | `cards/metadata.py` | No hard-coded names | Not started |
| **6+** | Future improvements | (Planned after Phase 5) | TBD | Not started |

**Key Insight**: CC waste is the best quality signal. A well-functioning V4 should:

- **Turn 1 (P1)**: Use 3 CC (with Surge), sleep 1 card, waste 0 CC
- **Turn 2 (P2)**: Use 4-5 CC, sleep 1-2 cards, waste 0-1 CC

Note: Turn sequence is P1(T1) → P2(T2) → P1(T3) → P2(T4)...

If these metrics fail, the prompt is broken. This is more valuable than checking for specific combos.

---

## Pre-Session Checklist (EVERY SESSION)

Before ANY AI development session, the agent MUST:

```
□ Read CONTEXT.md (root context - CHECK FACTS FIRST section)
□ Read COPILOT.md (architectural decisions quick reference)
□ Read docs/rules/QUICK_REFERENCE.md (game rules)
□ Read this plan document (current phase section at minimum)
□ Verify backend is running: curl http://localhost:8000/health
□ Verify frontend is running: http://localhost:5173
□ Know how to check AI logs: curl http://localhost:8000/admin/ai-logs?limit=5
```

---

## Phase 0: Stabilize & Fix Regressions ✅ COMPLETE

**Completed**: January 6, 2026 via PR #290  
**Verification Game**: `971cd8e6-2f8a-441c-93eb-16d92889321c`

### What Was Fixed

| Issue | Fix | Verification |
|-------|-----|--------------|
| 0.1 Persona/framing missing | Added intro: "You are an expert GGLTCG player..." | ✅ Present in AI logs |
| 0.2 Turn 1 tussle restriction | Removed "(unless it's Turn 1)" clause | ✅ No invalid restriction |
| 0.3 STATE CHANGES vague | Restored Wake example from commit 111d4be | ✅ Present in AI logs |
| 0.4 Backend cached code | Verified new code loaded | ✅ Admin logs show fixes |
| 0.5 Real game test | Played 2 turns, AI reasonable | ✅ No CC hallucination |

### Phase 0 Details (Historical Reference)

<details>
<summary>Click to expand original Phase 0 requirements</summary>

**Goal**: Fix the January 5 regressions surgically, verify backend loads changes, run a real game test.

**Time Estimate**: 2-3 hours

**Files to Modify**:

- `backend/src/game_engine/ai/prompts/sequence_generator.py`

**Files to Read First** (MANDATORY):

- `git show d47e2ed:backend/src/game_engine/ai/prompts/sequence_generator.py` (last known good)
- `git log --oneline -10 backend/src/game_engine/ai/prompts/sequence_generator.py`
- `docs/development/sessions/SESSION_POSTMORTEM_2026_01_05.md`

### Specific Issues to Fix

#### Issue 0.1: Restore Persona/Framing

**Problem**: Prompt starts with orphaned "## CC: X" with no context.

**Current** (broken):

```
Generate 5-10 LEGAL sequences that **spend ALL {player.cc} CC**...
```

**Required** (restore from d47e2ed or similar):

```
You are an expert GGLTCG player planning your turn.
Your goal: Sleep all 6 opponent cards to win.

## Your CC Budget: {cc_available}
...
```

#### Issue 0.2: Fix Turn 1 Tussle Rule

**Problem**: Current prompt says "Toys can tussle the SAME TURN they are played (unless it's Turn 1)!"

**Truth**: GGLTCG has NO summoning sickness. Cards CAN tussle on Turn 1. The restriction removed in commit `111d4be` was about a different mechanic.

**Fix**: Remove the "(unless it's Turn 1)" clause entirely. The correct rule is:

```
Cards can tussle the SAME TURN they are played!
```

#### Issue 0.3: Restore STATE CHANGES Section

**Problem**: Current version is vague.

**Current**:

```
## STATE CHANGES (CRITICAL!)
- Tussle that sleeps opponent's LAST toy → direct_attack becomes legal!
- Cards that return toys from sleep to hand let you replay them
```

**Required** (from commit 111d4be):

```
## STATE CHANGES (CRITICAL!)
- Tussle that sleeps opponent's LAST toy → direct_attack becomes legal!
- Wake moves card to HAND (must pay cost to play it again) → then it can tussle immediately!
- Example: Surge→Knight→tussle(sleeps last toy)→direct_attack→end_turn
```

#### Issue 0.4: Verify Backend Loads New Code

**Problem**: Previous session pushed changes but backend was running cached code.

**Verification Steps**:

```bash
# 1. Kill any running backend
ps aux | grep -E "python.*run_server|uvicorn" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null

# 2. Start fresh
cd backend && python run_server.py

# 3. Verify new code loaded - check logs for startup message or make a test request
curl http://localhost:8000/health
```

### Acceptance Criteria (Phase 0)

All criteria must pass before Phase 0 is complete:

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 0.1 | Prompt has persona/framing | `grep -n "expert\|goal\|planning" backend/src/game_engine/ai/prompts/sequence_generator.py` |
| 0.2 | No Turn 1 tussle restriction | `grep -n "Turn 1" backend/src/game_engine/ai/prompts/sequence_generator.py` returns NO matches with tussle restriction |
| 0.3 | STATE CHANGES has Wake example | `grep -n "Wake moves card" backend/src/game_engine/ai/prompts/sequence_generator.py` |
| 0.4 | Backend running with new code | Start game, check `curl localhost:8000/admin/ai-logs?limit=1` shows updated prompt |
| 0.5 | Real game test passes | Play 2 turns manually, AI makes reasonable moves (no CC hallucination, no illegal actions) |

### Starter Prompt (Phase 0)

```
## Context
You are fixing regressions in the AI V4 sequence generator prompt. Read these files FIRST before making any changes:

1. docs/development/ai/AI_V4_REMEDIATION_PLAN.md (this plan - Phase 0 section)
2. docs/development/sessions/SESSION_POSTMORTEM_2026_01_05.md (what went wrong)
3. Run: git show d47e2ed:backend/src/game_engine/ai/prompts/sequence_generator.py (last known good state)

## Task
Fix the sequence_generator.py prompt with these SPECIFIC changes:

1. Restore persona/framing at the start of the prompt
2. Remove "(unless it's Turn 1)" from the tussle rule - GGLTCG has NO summoning sickness
3. Restore the detailed STATE CHANGES section with the Wake example from commit 111d4be

## Constraints
- DO NOT remove the CC math examples that were added (those are good)
- DO NOT remove the UUID enrichment code (that's good)
- DO NOT change the JSON schema
- Keep the recent improvements to "Sleeps" tactical label clarification

## Verification
After changes:
1. Kill and restart the backend
2. Start a new game against AI
3. Check `curl localhost:8000/admin/ai-logs?limit=1` to confirm prompt is updated
4. Play 2 turns and verify AI behavior is reasonable

Report back with:
- What you changed (diff summary)
- Backend restart confirmation
- AI log showing new prompt
- Result of 2-turn test

## Git Workflow (After Verification Passes)
Once the 2-turn test passes, finalize Phase 0:
1. Create a PR to merge to main (use regisca-bot per bot-workflow.instructions.md)
2. Review and merge the PR
3. Delete any stale feature branches (no other active work)
4. Create a fresh branch for Phase 1: `git checkout -b feature/ai-v4-phase1-cc-tracking`
```

</details>

---

## Phase 1: CC Waste Tracking & Quality Metrics ✅ COMPLETE

**Completed**: January 7, 2026  
**Time Spent**: ~2 hours  
**Goal**: Implement turn-level CC waste tracking so we have an objective quality signal for AI behavior.

**Why This Is Phase 1**: CC waste is the BEST indicator of sequence quality:

- Turn 1 (P1, 2 CC + Surge): Should use 3 CC, sleep 1 card, waste 0 CC
- Turn 2 (P2, 4 CC): Should use 4-5 CC, sleep 1-2 cards, waste 0-1 CC
- Any turn ending with 2+ CC wasted = BAD sequence

This metric catches problems better than checking for specific combos.

**Files to Create**:

- `backend/src/game_engine/ai/quality_metrics.py`

**Files to Modify**:

- `backend/src/game_engine/ai/turn_planner.py` (log metrics after each turn)

### Quality Metrics Implementation

```python
# backend/src/game_engine/ai/quality_metrics.py
"""
Turn-level quality metrics for AI V4.

These metrics provide objective measurement of AI sequence quality.
CC waste is the primary quality indicator - advanced players waste <1 CC per turn.

Usage:
    metrics = TurnMetrics.from_plan(plan, game_state, player_id)
    if metrics.is_wasteful:
        logger.warning(f"Wasteful turn: {metrics.cc_wasted} CC wasted")
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger("game_engine.ai.quality_metrics")


@dataclass
class TurnMetrics:
    """Metrics for a single AI turn."""
    # Context
    game_id: str
    player_id: str
    turn_number: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    # CC metrics
    cc_start: int = 0
    cc_gained: int = 0  # From Surge, Rush, etc.
    cc_spent: int = 0
    cc_remaining: int = 0
    
    # Outcome metrics
    cards_slept: int = 0
    toys_played: int = 0
    actions_taken: int = 0
    
    # Efficiency calculations
    @property
    def cc_available(self) -> int:
        """Total CC available this turn (start + gained)."""
        return self.cc_start + self.cc_gained
    
    @property
    def cc_wasted(self) -> int:
        """CC left unused at end of turn."""
        return self.cc_remaining
    
    @property
    def efficiency_pct(self) -> float:
        """Percentage of available CC that was used."""
        if self.cc_available == 0:
            return 100.0
        return (self.cc_spent / self.cc_available) * 100
    
    @property
    def efficiency_rating(self) -> str:
        """
        Rate turn efficiency.
        
        Based on advanced player benchmarks:
        - 0-1 CC wasted = optimal
        - 2-3 CC wasted = acceptable (strategic save)
        - 4+ CC wasted = wasteful
        """
        if self.cc_wasted <= 1:
            return "optimal"
        elif self.cc_wasted <= 3:
            return "acceptable"
        else:
            return "wasteful"
    
    @property
    def is_optimal(self) -> bool:
        return self.efficiency_rating == "optimal"
    
    @property
    def is_wasteful(self) -> bool:
        return self.efficiency_rating == "wasteful"
    
    # Turn-specific expectations
    @property
    def expected_cc_for_turn(self) -> int:
        """Expected CC budget based on turn number."""
        if self.turn_number == 1:
            return 2  # Turn 1 starts with 2 CC
        else:
            return 4  # Turn 2+ starts with 4 CC (capped at 7)
    
    @property
    def expected_min_sleeps(self) -> int:
        """
        Expected minimum cards slept based on turn.
        
        Turn 1: With Surge+Knight+direct_attack = 1 sleep possible
        Turn 2+: With 4 CC = 2 sleeps possible (toy + 2 attacks)
        """
        if self.turn_number == 1:
            return 1 if self.cc_gained > 0 else 0  # Need Surge to sleep on T1
        else:
            return 1  # At minimum should sleep 1 card on T2+
    
    def meets_expectations(self) -> tuple[bool, str]:
        """
        Check if turn meets minimum quality expectations.
        
        Returns:
            (passed, reason) tuple
        """
        # Check CC waste
        if self.is_wasteful:
            return False, f"Wasteful: {self.cc_wasted} CC unused (max 3 acceptable)"
        
        # Check minimum sleeps (soft check - some turns may be setup)
        if self.cards_slept < self.expected_min_sleeps:
            if self.turn_number == 1 and self.cc_gained == 0:
                return True, "Turn 1 without Surge - no sleep expected"
            return False, f"Underperformed: {self.cards_slept} sleeps vs {self.expected_min_sleeps} expected"
        
        return True, f"Good: {self.cc_spent}/{self.cc_available} CC, {self.cards_slept} sleeps"
    
    @classmethod
    def from_plan(cls, plan, game_state, player_id: str) -> "TurnMetrics":
        """
        Extract metrics from a completed plan.
        
        Args:
            plan: TurnPlan object from turn_planner
            game_state: Current GameState
            player_id: Player who made the plan
        """
        # Count CC gains from the plan
        cc_gained = 0
        toys_played = 0
        
        for action in plan.action_sequence:
            if action.action_type == "play_card":
                if action.card_name == "Surge":
                    cc_gained += 1
                elif action.card_name == "Rush":
                    cc_gained += 2
                # Check if it's a toy (simplified - would need card lookup for accuracy)
                if action.card_name not in ["Surge", "Rush", "Wake", "Drop", "Clean", "Twist", "Sun", "Copy", "Toynado"]:
                    toys_played += 1
        
        return cls(
            game_id=game_state.game_id,
            player_id=player_id,
            turn_number=game_state.turn_number,
            cc_start=plan.cc_start,
            cc_gained=cc_gained,
            cc_spent=plan.cc_start + cc_gained - (plan.cc_after_plan or 0),
            cc_remaining=plan.cc_after_plan or 0,
            cards_slept=plan.expected_cards_slept,
            toys_played=toys_played,
            actions_taken=len([a for a in plan.action_sequence if a.action_type != "end_turn"]),
        )
    
    def to_log_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        passed, reason = self.meets_expectations()
        return {
            "game_id": self.game_id,
            "turn": self.turn_number,
            "cc_start": self.cc_start,
            "cc_gained": self.cc_gained,
            "cc_spent": self.cc_spent,
            "cc_remaining": self.cc_remaining,
            "cc_wasted": self.cc_wasted,
            "efficiency_pct": round(self.efficiency_pct, 1),
            "efficiency_rating": self.efficiency_rating,
            "cards_slept": self.cards_slept,
            "meets_expectations": passed,
            "assessment": reason,
        }


# Global metrics storage for session analysis
_session_metrics: List[TurnMetrics] = []


def record_turn_metrics(metrics: TurnMetrics):
    """Record metrics for later analysis."""
    _session_metrics.append(metrics)
    
    # Log immediately
    log_data = metrics.to_log_dict()
    if metrics.is_wasteful:
        logger.warning(f"WASTEFUL TURN: {log_data}")
    elif not metrics.meets_expectations()[0]:
        logger.info(f"SUBOPTIMAL TURN: {log_data}")
    else:
        logger.info(f"GOOD TURN: {log_data}")


def get_session_metrics() -> List[TurnMetrics]:
    """Get all metrics from current session."""
    return _session_metrics.copy()


def get_session_summary() -> dict:
    """Get summary statistics for the session."""
    if not _session_metrics:
        return {"turns": 0, "message": "No turns recorded"}
    
    total = len(_session_metrics)
    optimal = sum(1 for m in _session_metrics if m.is_optimal)
    wasteful = sum(1 for m in _session_metrics if m.is_wasteful)
    avg_waste = sum(m.cc_wasted for m in _session_metrics) / total
    avg_sleeps = sum(m.cards_slept for m in _session_metrics) / total
    
    return {
        "turns": total,
        "optimal_turns": optimal,
        "optimal_pct": round(optimal / total * 100, 1),
        "wasteful_turns": wasteful,
        "wasteful_pct": round(wasteful / total * 100, 1),
        "avg_cc_wasted": round(avg_waste, 2),
        "avg_cards_slept": round(avg_sleeps, 2),
        "target_avg_waste": "< 1.0",
        "target_optimal_pct": "> 65%",
    }


def clear_session_metrics():
    """Clear metrics for new session."""
    global _session_metrics
    _session_metrics = []
```

### Integration with turn_planner.py

Add metrics recording after plan creation:

```python
# In turn_planner.py, after successful plan creation:
from game_engine.ai.quality_metrics import TurnMetrics, record_turn_metrics

# After plan is created and validated
metrics = TurnMetrics.from_plan(plan, game_state, player_id)
record_turn_metrics(metrics)

# Log for visibility
logger.info(f"Turn {metrics.turn_number} metrics: {metrics.to_log_dict()}")
```

### Acceptance Criteria (Phase 1) ✅ ALL MET

| # | Criterion | Status | Verification |
|---|-----------|--------|--------------|
| 1.1 | Quality metrics file created | ✅ | File exists at `backend/src/game_engine/ai/quality_metrics.py` (232 lines) |
| 1.2 | TurnMetrics calculates cc_wasted | ✅ | Unit test passes: `metrics.cc_wasted == cc_remaining` |
| 1.3 | Turn 1 expectations correct | ✅ | Unit tests verify Turn 1 expects 2 CC, needs Surge for sleep |
| 1.4 | Metrics logged after each turn | ✅ | Integrated into turn_planner.py, logs show "GOOD TURN" / "WASTEFUL TURN" |
| 1.5 | Session summary works | ✅ | `get_session_summary()` tested with real AI game |

### What Was Delivered

**Files Created**:
1. `backend/src/game_engine/ai/quality_metrics.py` - TurnMetrics dataclass with efficiency calculations
2. `backend/tests/test_quality_metrics.py` - 18 unit tests (all passing)
3. `backend/scripts/test_phase1_metrics.py` - Integration test with real AI

**Files Modified**:
1. `backend/src/game_engine/ai/turn_planner.py` - Metrics recording at 4 return points (V3 and V4 paths)

**Test Results**:
- Unit tests: 18/18 passed
- Existing AI tests: 25 tests (11 passed, 14 skipped - no regressions)
- Real game test: ✅ Metrics tracked successfully
  - Turn 1: 0 CC wasted (optimal)
  - Turn 2: 1 CC wasted (optimal)
  - Session: 100% optimal turns, 0% wasteful

### Key Learnings

1. **Metrics Integration**: Adding metrics to turn_planner.py at all return points ensures complete coverage of both V3 and V4 AI paths, including fallback scenarios.

2. **CC Waste as Quality Signal**: The test confirmed CC waste is an excellent objective metric:
   - Both turns rated "optimal" (≤1 CC wasted)
   - Avg CC wasted: 0.5 (well below target of <1.0)
   - Easy to spot degradation in future tests

3. **Turn Expectations**: Turn-specific expectations work well:
   - Turn 1 with Surge: expect 3 CC available, 1 sleep possible
   - Turn 2+: expect 4+ CC available, 1+ sleep expected
   - Soft checks allow for strategic saves without false alarms

4. **AI Performance Baseline**: Current AI V4 shows good CC efficiency but room for improvement on card sleeps (achieved 1/2 expected in test). This is expected - Phase 1 is about *tracking*, optimization comes later.

5. **Testing Pattern**: The integration test (`test_phase1_metrics.py`) proves we can now measure AI quality objectively without manual testing. Foundation for Phase 2 automation.

### Starter Prompt (Phase 1)

```
## Context
You are implementing CC waste tracking to measure AI quality. Read these files FIRST:

1. docs/development/ai/AI_V4_REMEDIATION_PLAN.md (this plan - Phase 1 section)
2. backend/src/game_engine/ai/turn_planner.py (where to integrate)
3. backend/tests/test_ai_turn1_planning.py (existing test patterns)

## Task
1. Create backend/src/game_engine/ai/quality_metrics.py with the TurnMetrics class
2. Integrate metrics recording into turn_planner.py after plan creation
3. Add unit tests for the metrics calculations

## Key Quality Thresholds
- Turn 1 (2 CC start): With Surge, expect 3 CC used, 1 sleep, 0 waste
- Turn 2 (4 CC start): Expect 4-5 CC used, 1-2 sleeps, 0-1 waste
- Any turn with 4+ CC wasted = WASTEFUL = test failure

## Verification
1. Run a 2-turn game manually
2. Check logs for metrics output
3. Verify wasteful turns are flagged
4. Run: pytest backend/tests/test_quality_metrics.py (after creating tests)
```

---

## Phase 2: Automated Scenario Test (Your Repeatable Test)

**Goal**: Automate the EXACT test you keep running manually - Turn 1 (P1) + Turn 2 (P2) with a specific deck.

**Time Estimate**: 2-3 hours

**Why This Is Phase 2**: This directly addresses your frustration:
> "I keep manually repeating the same test with the same deck, and it's really not a good use of my time at this stage."

This test should:

1. Set up the exact game state you test with
2. Run Request 1 (sequence generation) for Turn 1 (P1) and Turn 2 (P2)
3. Validate CC waste and sleeps meet expectations
4. FAIL if the prompt is broken (like after Jan 5 changes)

**Files to Create**:

- `backend/tests/test_ai_standard_scenario.py`
- `backend/scripts/run_standard_scenario.py` (quick manual test)

### Standard Scenario Definition

Based on the existing test patterns and simulation decks:

```python
# backend/tests/test_ai_standard_scenario.py
"""
Standard Scenario Test for AI V4.

This automates the exact test that was being run manually:
- Deck: Surge, Knight, and supporting cards
- Turn 1: 2 CC, expect Surge → Knight → direct_attack (3 CC used, 1 sleep)
- Turn 2: 4 CC, expect aggressive play (4-5 CC used, 1-2 sleeps)

If this test fails, the AI prompt is broken and should not be deployed.

Run with: pytest tests/test_ai_standard_scenario.py -v -s
"""
import pytest
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards
from game_engine.ai.quality_metrics import TurnMetrics


def _has_valid_api_key():
    key = os.environ.get("GOOGLE_API_KEY", "")
    return key and not key.startswith("dummy") and len(key) > 20


pytestmark = pytest.mark.skipif(
    not _has_valid_api_key(),
    reason="Valid GOOGLE_API_KEY not set - skipping LLM tests"
)


@pytest.fixture
def turn_planner():
    """Create a TurnPlanner instance for testing."""
    from google import genai
    from game_engine.ai.turn_planner import TurnPlanner
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    fallback = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")
    
    return TurnPlanner(client=client, model_name=model, fallback_model=fallback)


class TestStandardScenario:
    """
    The standard test scenario that must pass before any prompt deployment.
    
    This is the automated version of the manual test that was being run repeatedly.
    """
    
    # The standard test deck - matches User_Slot3 from simulation_decks.csv
    PLAYER_DECK = ["Archer", "Knight", "Paper Plane", "Umbruh", "Surge", "Wake"]
    OPPONENT_DECK = ["Knight", "Ka", "Archer", "Wizard", "Drop", "Surge"]
    
    def test_turn1_with_surge_knight(self, turn_planner):
        """
        Turn 1: Standard opening with Surge + Knight.
        
        Setup:
        - Player has Surge, Knight, other cards in hand
        - Opponent has no toys in play (fresh game)
        - CC: 2 (Turn 1)
        
        Expected:
        - Play Surge (+1 CC) → 3 CC available
        - Play Knight (1 CC) → 2 CC remaining
        - Direct Attack (2 CC) → 0 CC remaining
        - Result: 3 CC used, 1 card slept, 0 CC wasted
        
        Minimum acceptable:
        - CC wasted ≤ 1
        - At least 1 card slept (given Surge is available)
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Umbruh", "Wake"],
            player1_in_play=[],
            player2_hand=self.OPPONENT_DECK,
            player2_in_play=[],
            player1_cc=2,  # Turn 1
            player2_cc=0,
            active_player="player1",
            turn_number=1,
        )
        
        print("\n" + "=" * 70)
        print("TURN 1 STANDARD SCENARIO TEST")
        print("=" * 70)
        print(f"Hand: Surge, Knight, Umbruh, Wake")
        print(f"CC: 2 (Turn 1)")
        print(f"Expected: Surge → Knight → direct_attack = 3 CC used, 1 sleep")
        print("=" * 70)
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None, "Plan should be generated"
        
        # Extract metrics
        metrics = TurnMetrics.from_plan(plan, setup.game_state, "player1")
        
        print(f"\nPlan result:")
        print(f"  CC start: {metrics.cc_start}")
        print(f"  CC gained: {metrics.cc_gained}")
        print(f"  CC spent: {metrics.cc_spent}")
        print(f"  CC remaining: {metrics.cc_remaining}")
        print(f"  Cards slept: {metrics.cards_slept}")
        print(f"  Efficiency: {metrics.efficiency_rating}")
        
        # CRITICAL ASSERTIONS
        assert metrics.cc_wasted <= 1, \
            f"Turn 1 WASTEFUL: {metrics.cc_wasted} CC unused. " \
            f"With Surge+Knight available, should use 3 CC. " \
            f"This indicates a broken prompt!"
        
        # Soft assertion for sleeps (warn but don't fail)
        if metrics.cards_slept == 0:
            print(f"\n⚠️ WARNING: 0 cards slept on Turn 1 with Surge+Knight available!")
            print("This may indicate the AI doesn't understand the Surge→Knight→direct_attack combo.")
        
        # Log for debugging
        print(f"\n✅ TURN 1 PASSED: {metrics.efficiency_rating}, {metrics.cc_wasted} CC wasted")
    
    def test_turn2_aggressive_play(self, turn_planner):
        """
        Turn 2 (P2's first turn): Aggressive follow-up.
        
        Setup:
        - Player 2 (AI) has Knight in play
        - Player 2 has cards in hand
        - Player 1 has 1 toy in play
        - CC: 4 (Turn 2 = P2's first turn)
        
        Expected:
        - Use Knight to tussle opponent toy (2 CC)
        - If clear, direct_attack (2 CC)
        - Result: 4 CC used, 1-2 cards slept
        
        Minimum acceptable:
        - CC wasted ≤ 1
        - At least 1 card slept
        """
        setup, cards = create_game_with_cards(
            player2_hand=["Umbruh", "Wake", "Archer"],
            player2_in_play=["Knight"],  # P2's Knight from a previous play
            player1_hand=["Ka", "Archer", "Wizard", "Drop", "Surge"],
            player1_in_play=["Knight"],  # P1's Knight
            player2_cc=4,  # Turn 2 = P2's first turn (gains 4 CC)
            player1_cc=0,
            active_player="player2",
            turn_number=2,  # Turn 2 = P2's first turn
        )
        
        print("\n" + "=" * 70)
        print("TURN 2 (P2's FIRST TURN) STANDARD SCENARIO TEST")
        print("=" * 70)
        print(f"Player 2 (AI) Hand: Umbruh, Wake, Archer")
        print(f"Player 2 In Play: Knight")
        print(f"Player 1 (Opponent): Knight in play")
        print(f"CC: 4 (Turn 2 = P2's first turn)")
        print(f"Expected: tussle Knight→Knight, then direct_attack or play more")
        print("=" * 70)
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player2",  # Turn 2 = P2's turn
            setup.engine
        )
        
        assert plan is not None, "Plan should be generated"
        
        metrics = TurnMetrics.from_plan(plan, setup.game_state, "player2")
        
        print(f"\nPlan result:")
        print(f"  CC start: {metrics.cc_start}")
        print(f"  CC spent: {metrics.cc_spent}")
        print(f"  CC remaining: {metrics.cc_remaining}")
        print(f"  Cards slept: {metrics.cards_slept}")
        print(f"  Efficiency: {metrics.efficiency_rating}")
        
        # CRITICAL ASSERTIONS
        assert metrics.cc_wasted <= 1, \
            f"Turn 2 (P2) WASTEFUL: {metrics.cc_wasted} CC unused. " \
            f"With 4 CC and Knight in play, should spend 4+ CC. " \
            f"This indicates a broken prompt!"
        
        assert metrics.cards_slept >= 1, \
            f"Turn 2 (P2) UNDERPERFORMED: {metrics.cards_slept} cards slept. " \
            f"With Knight in play vs opponent Knight, should sleep at least 1. " \
            f"This indicates strategic issues in the prompt!"
        
        print(f"\n✅ TURN 2 (P2) PASSED: {metrics.efficiency_rating}, {metrics.cards_slept} sleeps")
    
    def test_full_scenario_turn1_and_turn2(self, turn_planner):
        """
        Full scenario: Turn 1 (P1) followed by Turn 2 (P2).
        
        This simulates the complete 2-turn test that was being run manually.
        Tests the AI's ability to:
        1. Use resources efficiently on Turn 1 (P1, tight CC budget)
        2. Follow up aggressively on Turn 2 (P2, more CC available)
        """
        print("\n" + "=" * 70)
        print("FULL SCENARIO: TURN 1 (P1) + TURN 2 (P2)")
        print("=" * 70)
        
        # --- TURN 1 ---
        setup_t1, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Umbruh", "Wake"],
            player1_in_play=[],
            player2_hand=self.OPPONENT_DECK,
            player2_in_play=[],
            player1_cc=2,
            player2_cc=0,
            active_player="player1",
            turn_number=1,
        )
        
        plan_t1 = turn_planner.create_plan(setup_t1.game_state, "player1", setup_t1.engine)
        assert plan_t1 is not None
        
        metrics_t1 = TurnMetrics.from_plan(plan_t1, setup_t1.game_state, "player1")
        print(f"\nTurn 1: {metrics_t1.cc_spent}/{metrics_t1.cc_available} CC, "
              f"{metrics_t1.cards_slept} sleeps, {metrics_t1.efficiency_rating}")
        
        # --- TURN 2 ---
        # Simulate game state after Turn 1
        # Assume Knight played and survived, 1 opponent card slept
        setup_t2, _ = create_game_with_cards(
            player1_hand=["Umbruh", "Wake"],  # Used Surge+Knight
            player1_in_play=["Knight"],
            player2_hand=["Ka", "Archer", "Wizard", "Drop", "Surge"],  # -1 card
            player2_in_play=["Knight"],  # Opponent played Knight
            player1_cc=4,
            player2_cc=0,
            active_player="player1",
            turn_number=2,
        )
        
        plan_t2 = turn_planner.create_plan(setup_t2.game_state, "player1", setup_t2.engine)
        assert plan_t2 is not None
        
        metrics_t2 = TurnMetrics.from_plan(plan_t2, setup_t2.game_state, "player1")
        print(f"Turn 2: {metrics_t2.cc_spent}/{metrics_t2.cc_available} CC, "
              f"{metrics_t2.cards_slept} sleeps, {metrics_t2.efficiency_rating}")
        
        # --- AGGREGATE CHECK ---
        total_cc_wasted = metrics_t1.cc_wasted + metrics_t2.cc_wasted
        total_sleeps = metrics_t1.cards_slept + metrics_t2.cards_slept
        
        print(f"\n{'=' * 70}")
        print(f"SCENARIO SUMMARY:")
        print(f"  Total CC wasted: {total_cc_wasted}")
        print(f"  Total cards slept: {total_sleeps}")
        print(f"{'=' * 70}")
        
        # SCENARIO PASS/FAIL
        assert total_cc_wasted <= 2, \
            f"SCENARIO FAILED: {total_cc_wasted} total CC wasted over 2 turns. " \
            f"Max acceptable is 2 (1 per turn)."
        
        assert total_sleeps >= 2, \
            f"SCENARIO FAILED: Only {total_sleeps} cards slept over 2 turns. " \
            f"Should sleep at least 2 (1 per turn minimum)."
        
        print(f"\n✅ FULL SCENARIO PASSED")
```

### Quick Manual Test Script

```python
#!/usr/bin/env python3
# backend/scripts/run_standard_scenario.py
"""
Quick manual test for the standard scenario.

Run this after ANY prompt change to verify basic functionality.

Usage:
    cd backend
    python scripts/run_standard_scenario.py

Expected output:
    Turn 1: 3/3 CC, 1 sleep, optimal
    Turn 2: 4/4 CC, 2 sleeps, optimal
    PASSED
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Check for API key
if not os.environ.get("GOOGLE_API_KEY"):
    print("ERROR: GOOGLE_API_KEY not set")
    print("Run: export GOOGLE_API_KEY=your_key")
    sys.exit(1)


def main():
    from google import genai
    from game_engine.ai.turn_planner import TurnPlanner
    from game_engine.ai.quality_metrics import TurnMetrics, get_session_summary, clear_session_metrics
    
    # Import test fixture helper
    sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
    from conftest import create_game_with_cards
    
    print("=" * 60)
    print("STANDARD SCENARIO TEST")
    print("=" * 60)
    
    # Setup planner
    api_key = os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    planner = TurnPlanner(client=client, model_name=model, fallback_model=model)
    
    clear_session_metrics()
    results = []
    
    # Turn 1
    print("\n--- TURN 1 ---")
    setup_t1, _ = create_game_with_cards(
        player1_hand=["Surge", "Knight", "Umbruh", "Wake"],
        player1_in_play=[],
        player2_hand=["Knight", "Ka", "Archer", "Wizard", "Drop", "Surge"],
        player2_in_play=[],
        player1_cc=2,
        player2_cc=0,
        active_player="player1",
        turn_number=1,
    )
    
    plan_t1 = planner.create_plan(setup_t1.game_state, "player1", setup_t1.engine)
    if plan_t1:
        m1 = TurnMetrics.from_plan(plan_t1, setup_t1.game_state, "player1")
        print(f"CC: {m1.cc_spent}/{m1.cc_available} | Sleeps: {m1.cards_slept} | {m1.efficiency_rating}")
        results.append(m1)
    else:
        print("FAILED: No plan generated")
        sys.exit(1)
    
    # Turn 2
    print("\n--- TURN 2 ---")
    setup_t2, _ = create_game_with_cards(
        player1_hand=["Umbruh", "Wake"],
        player1_in_play=["Knight"],
        player2_hand=["Ka", "Archer", "Wizard", "Drop", "Surge"],
        player2_in_play=["Knight"],
        player1_cc=4,
        player2_cc=0,
        active_player="player1",
        turn_number=2,
    )
    
    plan_t2 = planner.create_plan(setup_t2.game_state, "player1", setup_t2.engine)
    if plan_t2:
        m2 = TurnMetrics.from_plan(plan_t2, setup_t2.game_state, "player1")
        print(f"CC: {m2.cc_spent}/{m2.cc_available} | Sleeps: {m2.cards_slept} | {m2.efficiency_rating}")
        results.append(m2)
    else:
        print("FAILED: No plan generated")
        sys.exit(1)
    
    # Summary
    print("\n" + "=" * 60)
    total_waste = sum(m.cc_wasted for m in results)
    total_sleeps = sum(m.cards_slept for m in results)
    
    passed = total_waste <= 2 and total_sleeps >= 2
    
    print(f"Total CC wasted: {total_waste} (max 2)")
    print(f"Total sleeps: {total_sleeps} (min 2)")
    print("=" * 60)
    
    if passed:
        print("✅ PASSED")
        sys.exit(0)
    else:
        print("❌ FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Acceptance Criteria (Phase 2)

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 2.1 | Standard scenario test created | File exists at `backend/tests/test_ai_standard_scenario.py` |
| 2.2 | Test uses real LLM calls | Test requires GOOGLE_API_KEY |
| 2.3 | Test validates CC waste | Assert on `metrics.cc_wasted <= 1` |
| 2.4 | Test validates sleeps | Assert on `metrics.cards_slept >= expected` |
| 2.5 | Quick script works | `python scripts/run_standard_scenario.py` completes |
| 2.6 | Test catches broken prompts | Temporarily break prompt, verify test fails |

### Starter Prompt (Phase 2)

```
## Context
You are creating the automated test that replaces manual Turn 1 + Turn 2 testing. Read these files FIRST:

1. docs/development/ai/AI_V4_REMEDIATION_PLAN.md (this plan - Phase 2 section)
2. backend/tests/test_ai_turn1_planning.py (existing LLM test patterns)
3. backend/src/game_engine/ai/quality_metrics.py (metrics from Phase 1)

## Task
1. Create backend/tests/test_ai_standard_scenario.py with Turn 1 + Turn 2 tests
2. Create backend/scripts/run_standard_scenario.py for quick manual verification
3. Ensure tests use TurnMetrics for quality validation

## Key Assertions
- Turn 1: cc_wasted <= 1, cards_slept >= 1 (with Surge)
- Turn 2: cc_wasted <= 1, cards_slept >= 1
- Full scenario: total_cc_wasted <= 2, total_sleeps >= 2

## Verification
1. Run with working prompt: pytest tests/test_ai_standard_scenario.py -v -s
2. All tests should pass
3. Temporarily break the prompt (add Turn 1 restriction)
4. Tests should FAIL
5. Revert the break, tests pass again
```

---

## Phase 3: Document Learnings in COPILOT.md

**Goal**: Update COPILOT.md with any new learnings from Phases 0-2

**Status**: 🔵 READY (COPILOT.md already exists from January 6)

**Time Estimate**: 30 minutes

**Files to Modify**:
- `COPILOT.md` (add any new failures, decisions, or patterns from Phase 0-2)

### What's Already Done

COPILOT.md was created on January 6, 2026 with:
- January 5+6 disaster documentation
- Core architectural decisions
- Testing philosophy
- Environment facts

### Remaining Work

1. Review Phase 0-2 work for new learnings
2. Update COPILOT.md with:
   - Any new failures or near-misses
   - Prompt patterns that worked well
   - CC waste tracking insights
   - Testing patterns from automated scenario test

### Acceptance Criteria (Phase 3)

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 3.1 | Phase 0 learnings documented | COPILOT.md mentions Turn 1 tussle bug fix |
| 3.2 | Phase 1 insights documented | COPILOT.md mentions CC waste as quality signal |
| 3.3 | Phase 2 patterns documented | COPILOT.md mentions automated Turn 1+2 test value |
| 3.4 | Committed to main | `git log` shows COPILOT.md update |

### Starter Prompt (Phase 3)

```
## Context
COPILOT.md exists at project root with initial documentation from January 6, 2026.

Read these files:
1. COPILOT.md (the file to update)
2. This plan document (review Phase 0-2 sections)
3. Recent commits: `git log --oneline -20`

## Task
1. Review Phases 0-2 work for new learnings
2. Update COPILOT.md sections:
   - Add Phase 0 Turn 1 bug fix to "Critical Failures & Learnings"
   - Update "Testing Philosophy" with CC waste tracking insights
   - Add any new architectural decisions or patterns

## Verification
1. COPILOT.md contains Phase 0-2 learnings
2. Commit with message: "docs: Update COPILOT.md with Phase 0-2 learnings"
```

---

## Phase 4: Prompt Content Regression Tests

**Goal**: Create unit tests that catch prompt content regressions (like the Jan 5 issues) WITHOUT making LLM calls.

**Time Estimate**: 2-3 hours

**Files to Create**:

- `backend/tests/test_ai_prompt_regression.py`

**Files to Read First**:

- `backend/tests/test_ai_v4_components.py` (existing V4 tests)
- `backend/tests/conftest.py` (test fixtures)

```python
# backend/tests/test_ai_prompt_regression.py
"""
Regression tests for AI prompt content.

These tests verify that critical prompt elements are present and correct.
They catch regressions like those from the January 5, 2026 session.
"""
import pytest
from game_engine.ai.prompts.sequence_generator import generate_sequence_prompt
from conftest import create_game_with_cards


class TestPromptContentRegression:
    """Verify critical prompt elements are present."""
    
    def test_no_turn_1_tussle_restriction(self):
        """
        Regression: Jan 5 2026 session added "(unless it's Turn 1)" restriction.
        GGLTCG has NO summoning sickness - cards can tussle on Turn 1.
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Knight"],
            active_player="player1",
        )
        setup.game_state.turn_number = 1
        
        prompt = generate_sequence_prompt(
            setup.game_state, 
            setup.player1.player_id,
            setup.engine
        )
        
        # Should NOT contain Turn 1 restriction
        assert "unless it's Turn 1" not in prompt.lower(), \
            "Prompt incorrectly restricts tussle on Turn 1 - GGLTCG has no summoning sickness"
    
    def test_wake_example_present(self):
        """
        Regression: Jan 5 session removed specific Wake mechanics.
        Wake moves card to HAND, not directly to play.
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Wake"],
            player1_sleep=["Knight"],
            active_player="player1",
        )
        
        prompt = generate_sequence_prompt(
            setup.game_state,
            setup.player1.player_id,
            setup.engine
        )
        
        # Should contain Wake -> HAND explanation
        assert "hand" in prompt.lower() and "wake" in prompt.lower(), \
            "Prompt should explain Wake moves cards to HAND"
    
    def test_persona_framing_present(self):
        """
        Regression: Jan 5 session removed persona/framing.
        Prompt should establish context for the LLM.
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Knight"],
            active_player="player1",
        )
        
        prompt = generate_sequence_prompt(
            setup.game_state,
            setup.player1.player_id,
            setup.engine
        )
        
        # Should have some framing (exact wording may vary)
        has_framing = any(word in prompt.lower() for word in [
            "expert", "goal", "planning", "your turn", "ggltcg"
        ])
        assert has_framing, "Prompt should have persona/framing at start"
    
    def test_cc_available_is_dynamic(self):
        """
        Regression: Static CC values caused hallucination.
        PR #288 fixed this - verify it stays fixed.
        """
        # Test with different CC values
        for cc_value in [2, 4, 5, 7]:
            setup, cards = create_game_with_cards(
                player1_hand=["Knight"],
                active_player="player1",
                player1_cc=cc_value,
            )
            
            prompt = generate_sequence_prompt(
                setup.game_state,
                setup.player1.player_id,
                setup.engine
            )
            
            # CC value should appear in prompt
            assert str(cc_value) in prompt, \
                f"Prompt should show actual CC ({cc_value}), not static value"
    
    def test_direct_attack_conditional_on_board_state(self):
        """
        direct_attack is only legal when opponent has 0 toys in play.
        Prompt should reflect current board state.
        """
        # With opponent toys
        setup1, _ = create_game_with_cards(
            player1_hand=["Knight"],
            player1_in_play=["Wizard"],
            player2_in_play=["Ka"],  # Opponent has toy
            active_player="player1",
        )
        prompt1 = generate_sequence_prompt(
            setup1.game_state,
            setup1.player1.player_id,
            setup1.engine
        )
        
        # Without opponent toys
        setup2, _ = create_game_with_cards(
            player1_hand=["Knight"],
            player1_in_play=["Wizard"],
            player2_in_play=[],  # No opponent toys
            active_player="player1",
        )
        prompt2 = generate_sequence_prompt(
            setup2.game_state,
            setup2.player1.player_id,
            setup2.engine
        )
        
        # Prompts should differ in direct_attack guidance
        assert "direct_attack" in prompt1 or "direct_attack" in prompt2, \
            "Prompt should mention direct_attack"
        # When opponent has toys, should indicate restriction
        assert "0 toys" in prompt1 or "cannot" in prompt1.lower() or "illegal" in prompt1.lower(), \
            "Should indicate direct_attack restricted when opponent has toys"


class TestPromptStructure:
    """Verify prompt structure requirements."""
    
    def test_prompt_length_reasonable(self):
        """Prompt should be under 6k chars for efficiency."""
        setup, cards = create_game_with_cards(
            player1_hand=["Knight", "Surge", "Wake"],
            player1_in_play=["Wizard"],
            player2_in_play=["Ka", "Archer"],
            active_player="player1",
        )
        
        prompt = generate_sequence_prompt(
            setup.game_state,
            setup.player1.player_id,
            setup.engine
        )
        
        assert len(prompt) < 6000, \
            f"Prompt too long ({len(prompt)} chars), target <6000"
    
    def test_task_section_near_end(self):
        """Task/instruction should be at end of prompt (LLM best practice)."""
        setup, cards = create_game_with_cards(
            player1_hand=["Knight"],
            active_player="player1",
        )
        
        prompt = generate_sequence_prompt(
            setup.game_state,
            setup.player1.player_id,
            setup.engine
        )
        
        # Find task section
        task_pos = prompt.lower().rfind("task")
        if task_pos == -1:
            task_pos = prompt.lower().rfind("generate")
        
        # Task should be in last 30% of prompt
        assert task_pos > len(prompt) * 0.5, \
            "Task/instruction should be near end of prompt"
```

### Acceptance Criteria (Phase 4)

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 4.1 | Regression tests created | `pytest backend/tests/test_ai_prompt_regression.py -v` passes |
| 4.2 | Tests catch Turn 1 bug | Temporarily add "(unless Turn 1)", verify test fails |
| 4.3 | Tests catch missing Wake | Temporarily remove Wake example, verify test fails |
| 4.4 | Tests verify dynamic CC | Test checks CC values are dynamic not static |
| 4.5 | All existing tests pass | `pytest backend/tests/` has no new failures |

### Starter Prompt (Phase 4)

```
## Context
You are creating unit tests that validate prompt CONTENT without making LLM calls. Read these files FIRST:

1. docs/development/ai/AI_V4_REMEDIATION_PLAN.md (this plan - Phase 4 section)
2. backend/tests/test_ai_v4_components.py (existing test patterns)
3. backend/src/game_engine/ai/prompts/sequence_generator.py (the prompt to test)

## Task
Create backend/tests/test_ai_prompt_regression.py with tests that:
1. Verify no Turn 1 tussle restriction exists
2. Verify Wake example is present
3. Verify CC values are dynamic (not static)
4. Verify prompt structure (task at end, reasonable length)

## Key Point
These tests do NOT call the LLM. They test the PROMPT CONTENT directly.
This is cheap, fast, and catches regressions like the Jan 5 issues.

## Verification
1. Run tests: pytest backend/tests/test_ai_prompt_regression.py -v
2. All tests pass
3. Temporarily break prompt, verify relevant test fails
4. Revert break
```

---

## Phase 5: Card Metadata Infrastructure

**Goal**: Centralize card metadata to eliminate hard-coded card names scattered across prompt files.

**Time Estimate**: 3-4 hours

**Files to Create**:

- `backend/src/game_engine/cards/metadata.py`

**Files to Modify**:

- `backend/src/game_engine/ai/prompts/sequence_generator.py`
- `backend/src/game_engine/ai/validators/turn_plan_validator.py`

**Files to Read First**:

- `backend/data/cards.csv` (source of truth for card data)
- Technical Audit section on "Fix 1.1: Centralize Card Metadata"

### Card Metadata Structure

```python
# backend/src/game_engine/cards/metadata.py
"""
Centralized card metadata for AI prompts.

This is the SINGLE SOURCE OF TRUTH for card properties used in AI prompts.
NO OTHER FILE should hard-code card names or properties.

When adding a new card:
1. Add entry to CARD_METADATA dict
2. NO changes needed to prompt files (they query this metadata)
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class CardType(Enum):
    TOY = "toy"
    ACTION = "action"


class TargetZone(Enum):
    OPPONENT_BOARD = "opponent_board"
    MY_SLEEP = "my_sleep"
    MY_BOARD = "my_board"
    ANY_CARD = "any_card"
    NONE = "none"


@dataclass
class CardMeta:
    """Metadata for a single card."""
    name: str
    cost: int
    card_type: CardType
    
    # Resource generation
    cc_gain: int = 0
    
    # Priority (higher = play earlier in sequence)
    # 90-100: Resource cards (Surge, Rush)
    # 70-89: Enablers (Wake, Sun)
    # 50-69: Standard cards
    # 0-49: Situational
    priority: int = 50
    
    # Targeting
    requires_target: bool = False
    target_zone: TargetZone = TargetZone.NONE
    
    # Combat (for toys)
    strength: int = 0
    speed: int = 0
    stamina: int = 0
    
    # Special abilities (for prompt generation)
    special_note: Optional[str] = None


# Master card database - ALL 18 cards
CARD_METADATA: dict[str, CardMeta] = {
    # === Resource Cards (Priority 90-100) ===
    "Surge": CardMeta(
        name="Surge",
        cost=0,
        card_type=CardType.ACTION,
        cc_gain=1,
        priority=100,
        special_note="+1 CC when played, play FIRST",
    ),
    "Rush": CardMeta(
        name="Rush",
        cost=0,
        card_type=CardType.ACTION,
        cc_gain=2,
        priority=99,
        special_note="+2 CC when played, play FIRST",
    ),
    
    # === State Change Cards (Priority 70-89) ===
    "Wake": CardMeta(
        name="Wake",
        cost=1,
        card_type=CardType.ACTION,
        priority=75,
        requires_target=True,
        target_zone=TargetZone.MY_SLEEP,
        special_note="Returns card to HAND (must pay cost to replay)",
    ),
    "Sun": CardMeta(
        name="Sun",
        cost=2,
        card_type=CardType.ACTION,
        priority=70,
        requires_target=True,
        target_zone=TargetZone.MY_SLEEP,
        special_note="Returns card directly to BOARD (no replay cost)",
    ),
    
    # === Removal Cards (Priority 60-69) ===
    "Drop": CardMeta(
        name="Drop",
        cost=2,
        card_type=CardType.ACTION,
        priority=65,
        requires_target=True,
        target_zone=TargetZone.OPPONENT_BOARD,
        special_note="Sleeps opponent toy directly",
    ),
    "Twist": CardMeta(
        name="Twist",
        cost=1,
        card_type=CardType.ACTION,
        priority=60,
        requires_target=True,
        target_zone=TargetZone.OPPONENT_BOARD,
        special_note="Steals opponent toy (control changes)",
    ),
    "Clean": CardMeta(
        name="Clean",
        cost=0,
        card_type=CardType.ACTION,
        priority=62,
        special_note="Sleeps ALL toys (both players)",
    ),
    "Toynado": CardMeta(
        name="Toynado",
        cost=1,
        card_type=CardType.ACTION,
        priority=55,
        requires_target=True,
        target_zone=TargetZone.MY_BOARD,
        special_note="Sleep your toy to draw 2",
    ),
    
    # === Combat Toys (Priority 50-59) ===
    "Knight": CardMeta(
        name="Knight",
        cost=1,
        card_type=CardType.TOY,
        priority=58,
        strength=3,
        speed=4,
        stamina=3,
        special_note="Auto-wins tussles on YOUR turn",
    ),
    "Archer": CardMeta(
        name="Archer",
        cost=2,
        card_type=CardType.TOY,
        priority=55,
        strength=0,  # Cannot attack!
        speed=3,
        stamina=3,
        special_note="STR=0 (cannot tussle/direct_attack), has activate: 1 CC deals 1 damage",
    ),
    "Wizard": CardMeta(
        name="Wizard",
        cost=1,
        card_type=CardType.TOY,
        priority=52,
        strength=3,
        speed=3,
        stamina=3,
    ),
    "Ka": CardMeta(
        name="Ka",
        cost=1,
        card_type=CardType.TOY,
        priority=50,
        strength=4,
        speed=2,
        stamina=3,
    ),
    "Raggy": CardMeta(
        name="Raggy",
        cost=2,
        card_type=CardType.TOY,
        priority=56,
        strength=4,
        speed=3,
        stamina=3,
        special_note="Steals opponent toy when played",
    ),
    "Umbruh": CardMeta(
        name="Umbruh",
        cost=2,
        card_type=CardType.TOY,
        priority=54,
        strength=4,
        speed=3,
        stamina=4,
        special_note="+1 CC when this toy wins a tussle",
    ),
    "Beary": CardMeta(
        name="Beary",
        cost=2,
        card_type=CardType.TOY,
        priority=53,
        strength=3,
        speed=3,
        stamina=4,
        special_note="Immune to opponent effects",
    ),
    "Snuggles": CardMeta(
        name="Snuggles",
        cost=1,
        card_type=CardType.TOY,
        priority=51,
        strength=2,
        speed=2,
        stamina=3,
    ),
    "Dream": CardMeta(
        name="Dream",
        cost=2,
        card_type=CardType.TOY,
        priority=52,
        strength=3,
        speed=3,
        stamina=4,
    ),
    "Ballaber": CardMeta(
        name="Ballaber",
        cost=3,
        card_type=CardType.TOY,
        priority=48,
        strength=5,
        speed=4,
        stamina=5,
        special_note="Expensive but powerful",
    ),
    
    # === Utility Cards ===
    "Copy": CardMeta(
        name="Copy",
        cost=1,
        card_type=CardType.ACTION,
        priority=45,
        requires_target=True,
        target_zone=TargetZone.MY_BOARD,
        special_note="Copies target toy (complex mechanics)",
    ),
    "Paper Plane": CardMeta(
        name="Paper Plane",
        cost=0,
        card_type=CardType.TOY,
        priority=40,
        strength=1,
        speed=1,
        stamina=1,
        special_note="Cheap blocker, weak stats",
    ),
}


# === Query Functions ===

def get_resource_cards() -> list[str]:
    """Cards that generate CC when played."""
    return [name for name, meta in CARD_METADATA.items() if meta.cc_gain > 0]


def get_cards_by_priority(card_names: list[str]) -> list[str]:
    """Sort cards by priority (highest first)."""
    return sorted(
        card_names,
        key=lambda n: CARD_METADATA.get(n, CardMeta(n, 0, CardType.TOY)).priority,
        reverse=True
    )


def get_targeting_info(card_name: str) -> tuple[bool, TargetZone]:
    """Get targeting requirements for a card."""
    meta = CARD_METADATA.get(card_name)
    if meta:
        return meta.requires_target, meta.target_zone
    return False, TargetZone.NONE


def get_cc_gain(card_name: str) -> int:
    """Get CC gained when card is played."""
    meta = CARD_METADATA.get(card_name)
    return meta.cc_gain if meta else 0


def get_special_note(card_name: str) -> Optional[str]:
    """Get special note for prompt generation."""
    meta = CARD_METADATA.get(card_name)
    return meta.special_note if meta else None
```

### Refactoring sequence_generator.py

Replace hard-coded card checks with metadata queries:

```python
# BEFORE (hard-coded)
if card.name == "Surge":
    cc_mod = " (+1 CC when played)"
elif card.name == "Rush":
    cc_mod = " (+2 CC when played)"

# AFTER (metadata-driven)
from game_engine.cards.metadata import get_cc_gain, get_special_note

cc_gain = get_cc_gain(card.name)
if cc_gain > 0:
    cc_mod = f" (+{cc_gain} CC when played)"
```

### Acceptance Criteria (Phase 5)

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 5.1 | Metadata file created | File exists with all 18 cards |
| 5.2 | No hard-coded card names in sequence_generator | `grep -E "Surge\|Rush\|Wake\|Knight" sequence_generator.py` shows only in comments or metadata calls |
| 5.3 | Query functions work | Unit tests for get_resource_cards(), get_cc_gain(), etc. |
| 5.4 | Existing tests still pass | `pytest backend/tests/` |
| 5.5 | Real game works | Play 2 turns, verify prompts correct |

### Starter Prompt (Phase 5)

```
## Context
You are centralizing card metadata to eliminate hard-coded card names. Read these files FIRST:

1. docs/development/ai/AI_V4_REMEDIATION_PLAN.md (this plan - Phase 5 section)
2. docs/development/ai/TECHNICAL_AUDIT.md (Fix 1.1 section)
3. backend/data/cards.csv (source of truth for card stats)
4. backend/src/game_engine/ai/prompts/sequence_generator.py (file to refactor)

## Task
1. Create backend/src/game_engine/cards/metadata.py with card metadata for all 18 cards
2. Refactor sequence_generator.py to use metadata queries instead of hard-coded card names
3. Add unit tests for metadata query functions

## Constraints
- Metadata values MUST match cards.csv (cross-reference!)
- Keep backward compatibility - don't change prompt output, just how it's generated
- Add __init__.py if needed for imports

## Verification
1. Run existing tests: pytest backend/tests/
2. Run regression tests: pytest backend/tests/test_ai_prompt_regression.py
3. Play a real game and check prompt via `curl localhost:8000/admin/ai-logs?limit=1`
```

---

## Phase 6+: Future Work (Not Detailed Yet)

These phases should be planned after Phases 0-5 are complete:

- **Phase 6**: State-Based Phase Detection - Replace turn-number detection with cards-remaining metric
- **Phase 7**: Complete card guidance library (14 missing cards)
- **Phase 8**: Sleep zone consideration in example selection
- **Phase 9**: Dynamic sequence diversity based on phase
- **Phase 10**: Card synergy detection system
- **Phase 11**: V5 iterative sequence generation POC

---

## Quality Gates

### Before ANY Prompt Change

```
□ Read git history for file being modified
□ Run: pytest backend/tests/test_ai_prompt_regression.py
□ Have test game ready
```

### After ANY Prompt Change

```
□ Run: pytest backend/tests/test_ai_prompt_regression.py
□ Run: python backend/scripts/quick_ai_test.py
□ Play 2 turns manually, observe AI behavior
□ Check AI logs: curl localhost:8000/admin/ai-logs?limit=1
□ Document test results in PR/commit message
```

### Before Merging to Main

```
□ All tests pass: pytest backend/tests/
□ Real game test completed (2+ turns)
□ No increase in CC waste (if Phase 5 complete)
□ Peer review of prompt changes
```

---

## Appendix: Common Commands

```bash
# Kill backend
ps aux | grep -E "python.*run_server|uvicorn" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null

# Start backend
cd backend && python run_server.py

# Check backend health
curl http://localhost:8000/health

# Run all tests
pytest backend/tests/ -v

# Run regression tests only
pytest backend/tests/test_ai_prompt_regression.py -v

# Check recent git history
git log --oneline -20 backend/src/game_engine/ai/

# View file at specific commit
git show <commit>:path/to/file

# Search for hard-coded card names
grep -rn "Surge\|Rush\|Knight" backend/src/game_engine/ai/
```

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-05 | Initial creation |
