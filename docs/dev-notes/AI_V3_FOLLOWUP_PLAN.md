# AI v3 Follow-up Issues Implementation Plan

This document outlines the implementation plan for issues #252, #259, and #260, which build upon the AI v3 turn planning architecture.

> **Note**: Issue #258 (v2 vs v3 simulations) is deferred to a separate session focused on simulations.

## Issues Overview

| Issue | Title | Labels | Status |
|-------|-------|--------|--------|
| [#252](https://github.com/RegisCA/ggltcg/issues/252) | Add CC efficiency tracking to game logging | backend, enhancement | ✅ Complete |
| [#259](https://github.com/RegisCA/ggltcg/issues/259) | Admin - Playbacks enhancement/consolidation | frontend, simulations, refactor | Not Started |
| [#260](https://github.com/RegisCA/ggltcg/issues/260) | Update play by play and AI logs for Gemiknight v3 | AI, backend, enhancement | Not Started |

## Implementation Dependencies

```
#252 (CC Tracking) ───┐
                      ├──> #259 (Playback Consolidation)
#260 (AI Logs v3) ────┘
```

**Recommended order**: #252 → #260 → #259

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

## Issue #260: Update Play by Play and AI Logs for Gemiknight v3

### Current State

- AI logs store: `prompt`, `response`, `action_number`, `reasoning`
- v3 generates a `TurnPlan` with: `threat_analysis`, `strategy`, `action_sequence`, `cc_efficiency`
- Play-by-play shows individual actions but not the overall plan
- No indication when v3 falls back to v2 for action selection

### Implementation Plan

#### 1. Extend AI Log Schema for v3 Plans

**File**: `backend/src/api/db_models.py`

Add new fields to `AILogModel`:

```python
# Existing fields
prompt = Column(Text, nullable=True)
response = Column(Text, nullable=True)
action_number = Column(Integer, nullable=True)
reasoning = Column(Text, nullable=True)

# New v3 fields
ai_version = Column(Integer, default=2)  # 2 or 3
turn_plan = Column(JSON, nullable=True)  # Full TurnPlan JSON for v3
plan_execution_status = Column(String, nullable=True)  # "complete", "partial", "fallback"
fallback_reason = Column(Text, nullable=True)  # Why fallback occurred
planned_action_index = Column(Integer, nullable=True)  # Which action in the plan (0-based)
```

#### 2. Log Turn Plan Creation

**File**: `backend/src/game_engine/ai/llm_player.py`

When v3 creates a plan, log it:

```python
def _log_v3_plan(self, game_id: str, turn: int, player_id: str, plan: TurnPlan):
    """Log the turn plan for v3 games."""
    # Include:
    # - Full plan JSON
    # - Threat analysis summary
    # - Strategy description
    # - Expected CC efficiency
    # - Action sequence with card names
```

#### 3. Track Plan Execution Status

**File**: `backend/src/game_engine/ai/llm_player.py`

Track when plan execution deviates:

```python
# In select_action():
def _record_execution_status(
    self,
    plan: TurnPlan,
    planned_action_index: int,
    selected_action: ValidAction,
    was_fallback: bool,
    fallback_reason: Optional[str] = None
):
    """Record whether action matched plan or required fallback."""
```

#### 4. Update Victory Screen Play-by-Play

**File**: `frontend/src/components/VictoryScreen.tsx` (or relevant component)

Changes needed:

1. **Show plan at turn start**: Before individual actions, show "Plan: [strategy]"
2. **Remove generic "end of turn"** messages unless meaningful
3. **Add v3/v2 indicator** in footer showing which version drove each turn

Example format:

```
Turn 3 (Gemiknight v3):
📋 Plan: Remove Knight threat via Archer, then direct attack x2
  Expected: 4 CC spent, 2 cards slept (2.0 CC/card)

  ✓ Play Archer [0 CC]
  ✓ Activate Archer → Knight [1 CC]
  ✓ Direct Attack [2 CC]
  ✓ End Turn
  
  Result: 3 CC spent, 1 card slept (3.0 CC/card) ⚠️ Deviation
```

#### 5. Redesign Admin AI Logs View for v3

**File**: `frontend/src/components/AdminDataViewer.tsx`

Create expanded AI log view for v3:

```tsx
interface AILogV3Detail {
  // Existing
  id: number;
  game_id: string;
  turn_number: number;
  player_id: string;
  model_name: string;
  
  // v3 specific
  ai_version: number;
  turn_plan?: {
    threat_analysis: string;
    strategy: string;
    action_sequence: Array<{
      action_type: string;
      card_name: string;
      target_name?: string;
      cc_cost: number;
      reasoning: string;
    }>;
    cc_start: number;
    cc_end_expected: number;
    expected_cards_slept: number;
    cc_efficiency: string;
  };
  plan_execution_status?: 'complete' | 'partial' | 'fallback';
  fallback_reason?: string;
  actions_taken: number;  // How many of planned actions executed
}
```

Display components:

1. **Plan Summary Card**: Threat analysis, strategy, expected efficiency
2. **Action Sequence Table**: Planned vs actual, with status indicators
3. **Execution Metrics**: Planned CC vs actual CC, planned cards slept vs actual
4. **Fallback Alerts**: Highlighted when plan couldn't be followed

#### 6. Add "View AI Log" Links in Playback

Connect playback turns to their corresponding AI logs:

- Each turn in playback should link to the AI log for that turn
- Filter AI logs by game_id + turn_number

### Testing

- Unit test: v3 plan logging with all fields populated
- Integration test: AI log API returns v3 fields correctly
- Manual test: Victory screen displays plan correctly
- Manual test: Admin AI logs show v3 plan details

---

## Issue #259: Admin Playbacks Enhancement/Consolidation

### Current State

Two separate views exist:

1. **Game Playbacks** (`/admin/game-playbacks`):
   - Clean, well-spaced layout
   - Shows starting decks, play-by-play
   - Missing: CC tracking, duration, turn count prominently

2. **Simulation Game Details** (inline in simulation tab):
   - Compact turn-by-turn table with CC per turn
   - Shows CC gained/spent per player per turn
   - Missing: Game duration, overall game highlights

### Implementation Plan

#### 1. Define Unified Playback Component

Create a reusable component that combines best features:

**File**: `frontend/src/components/GamePlaybackDetail.tsx` (new)

```tsx
interface GamePlaybackDetailProps {
  // Core game info
  gameId: string;
  player1: { id: string; name: string; deck: string[] };
  player2: { id: string; name: string; deck: string[] };
  winner?: { id: string; name: string };
  firstPlayerId: string;
  
  // Game metrics
  turnCount: number;
  durationSeconds: number;
  completedAt?: string;
  
  // CC Tracking (per turn)
  ccTracking: TurnCC[];
  
  // Play by play
  playByPlay: PlayByPlayEntry[];
  
  // Optional links
  aiLogLinkBase?: string;  // Base URL to link to AI logs per turn
  
  // Display options
  variant: 'full' | 'compact';  // full for playbacks, compact for simulations
}
```

#### 2. Consolidate CC Tracking Display

Take the turn-by-turn CC table from simulation view and enhance:

```tsx
<CCTrackingTable
  ccTracking={ccTracking}
  player1Name={player1.name}
  player2Name={player2.name}
  showTotals={true}
  showEfficiency={true}  // CC per card slept
/>
```

#### 3. Add Game Highlights Header

Combine metrics into a clear header:

```tsx
<GameHighlights
  turnCount={turnCount}
  duration={durationSeconds}
  winner={winner}
  player1CCEfficiency={player1.ccPerCardSlept}
  player2CCEfficiency={player2.ccPerCardSlept}
/>
```

#### 4. Integrate AI Log Links

Add links to AI logs for each turn:

```tsx
// In play-by-play table
<tr>
  <td>{entry.turn}</td>
  <td>{entry.player}</td>
  <td>{entry.action_type}</td>
  <td>{entry.description}</td>
  <td>
    {aiLogLinkBase && (
      <a href={`${aiLogLinkBase}?turn=${entry.turn}&player=${entry.player}`}>
        View AI Log
      </a>
    )}
  </td>
</tr>
```

#### 5. Update Playbacks Tab to Use New Component

**File**: `frontend/src/components/AdminDataViewer.tsx`

Replace current playback detail view with `GamePlaybackDetail`:

```tsx
{selectedPlayback && (
  <GamePlaybackDetail
    gameId={selectedPlayback.game_id}
    player1={...}
    player2={...}
    ccTracking={selectedPlayback.cc_tracking || []}
    playByPlay={selectedPlayback.play_by_play}
    variant="full"
    aiLogLinkBase={`#ai-logs?game=${selectedPlayback.game_id}`}
  />
)}
```

#### 6. Update Simulation Games to Use New Component

Replace inline simulation game detail with `GamePlaybackDetail`:

```tsx
{selectedGameDetail && (
  <GamePlaybackDetail
    gameId={`sim-${runId}-${selectedGameDetail.game_number}`}
    player1={...}
    player2={...}
    ccTracking={selectedGameDetail.cc_tracking}
    playByPlay={selectedGameDetail.action_log.map(toPlayByPlayEntry)}
    variant="compact"
  />
)}
```

#### 7. Backend: Consolidate CC Calculations

Per issue comment, calculate CC totals once in backend:

**File**: `backend/src/api/routers/admin.py`

Add computed fields to playback response:

```python
@dataclass
class PlaybackResponse:
    # ... existing fields ...
    
    # Computed CC stats
    player1_total_cc_spent: int
    player1_total_cc_gained: int
    player2_total_cc_spent: int
    player2_total_cc_gained: int
    
    # Efficiency (if cards_slept tracked)
    player1_cc_efficiency: Optional[float]
    player2_cc_efficiency: Optional[float]
```

### Testing

- Visual test: Playback view matches mockup/expectations
- Visual test: Simulation game detail uses same component
- Unit test: CC totals calculated correctly
- Integration test: AI log links work correctly

---

## Summary of Files to Modify/Create

### Backend

| File | Changes |
|------|---------|
| `game_engine/models/game_state.py` | Add `TurnCCRecord`, `cc_history` field |
| `game_engine/game_engine.py` | Add CC tracking during game execution |
| `game_engine/ai/llm_player.py` | v3 plan logging, execution status tracking |
| `api/db_models.py` | Extend `AILogModel`, `GamePlaybackModel` |
| `api/routers/game.py` | Add CC efficiency to game completion |
| `api/routers/admin.py` | Add computed CC stats to playback response |
| `api/services/stats_service.py` | Add CC efficiency aggregation |

### Frontend

| File | Changes |
|------|---------|
| `components/GamePlaybackDetail.tsx` | **NEW**: Unified playback component |
| `components/CCTrackingTable.tsx` | **NEW**: Reusable CC display |
| `components/GameHighlights.tsx` | **NEW**: Game metrics header |
| `components/AdminDataViewer.tsx` | Integrate new components |
| `components/VictoryScreen.tsx` | Show v3 plans, add version indicator |

### Database Migrations

1. Add `cc_tracking` to `game_playbacks` table
2. Add v3 fields to `ai_logs` table

---

## Estimated Effort

| Issue | Estimated Hours | Risk |
|-------|----------------|------|
| #252 (CC Tracking) | 8-12h | Low - straightforward data plumbing |
| #260 (AI Logs v3) | 12-16h | Medium - requires UI design decisions |
| #259 (Playback Consolidation) | 10-14h | Medium - refactoring existing UI |

**Total**: 30-42 hours

## Next Steps

1. Review and refine this plan
2. Create sub-issues or checkboxes for tracking
3. Start with #252 (foundation for others)
4. Parallel work possible on #260 backend while #252 frontend integrates

