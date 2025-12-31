# Issue #260: Update Play by Play and AI Logs for Gemiknight v3

## Implementation Status (2025-12-30)

### Backend Work ✅ COMPLETE

**PR #266** merged - adds v3 AI logging infrastructure.

| Task | Status | Details |
|------|--------|---------|
| 1. Extend AILogModel for v3 | ✅ Done | Added 5 columns: `ai_version`, `turn_plan`, `plan_execution_status`, `fallback_reason`, `planned_action_index` |
| 2. Log Turn Plan Creation | ✅ Done | `routes_actions.py` extracts `v3_plan` from `decision_info` |
| 3. Track Plan Execution Status | ✅ Done | Parses "[v3 Plan]" vs "[v3 Fallback]" prefixes |
| 4. Update AI Log API Response | ✅ Done | Admin API returns all v3 fields |

**Migration**: `011_add_v3_fields_to_ai_decision_logs.py` deployed to production.

---

## v3_plan Data Structure

The backend returns this structure in AI logs when v3 is active:

```json
{
  "strategy": "Remove Knight threat via Archer, then direct attack",
  "total_actions": 4,
  "current_action": 2,
  "cc_start": 5,
  "cc_after_plan": 1,
  "expected_cards_slept": 2,
  "cc_efficiency": 2.0
}
```

---

## Frontend Work: Admin AI Logs ✅ COMPLETE

### Priority: Admin AI Logs Redesign (Tasks 8-11)

**File**: `frontend/src/components/AdminDataViewer.tsx`

**Issue #260 Requirement**:
> "Admin, AI logs: this needs to be redesigned for v3. We need to understand the plan that was created, based on what prompt, and then how the plan was executed. This should highlight any time we're not able to execute the plan."

| Task | Status | Details |
|------|--------|---------|
| 8. Update AILog TypeScript Interface | ✅ Done | Added `ai_version`, `turn_plan`, `plan_execution_status`, `fallback_reason`, `planned_action_index` |
| 9. v3 Plan Summary Card | ✅ Done | Purple-bordered card showing strategy, progress, CC metrics, efficiency |
| 10. Fallback Alert | ✅ Done | Yellow warning box with fallback reason when plan couldn't execute |
| 11. Visual Version Indicators | ✅ Done | Version badge (purple v3, gray v2), status badges (green "Plan OK", yellow "Fallback") |

#### Implementation Details

**Version Badge** (Task 11):
- Purple badge for v3, gray for v2
- Shown in log header next to model name

**Plan Summary Card** (Task 9):
- Strategy text prominently displayed
- Progress: "Action X of Y"
- CC metrics: start → end, efficiency (CC/card slept)
- Cards to sleep count

**Fallback Alert** (Task 10):
- Yellow/orange warning styling
- Shows fallback reason text
- "Fallback" badge in header

---

### Deferred: Victory Screen Updates (Tasks 5-7)

**Issue #260 Requirements**:
> "We need to more clearly present the plan and then the actions taken"
> "Streamline / remove the 'end of turn', unless it's something other than a generic statement"
> "Indicate at each turn whether the actions were entirely driven by v3 or whether the app had to fall back to v2"

**Blocked**: Play-by-play entries do not currently include AI version or plan info.

**Options to unblock**:
1. **Backend change**: Add `ai_plan_summary` field to first play-by-play entry per AI turn
2. **Frontend change**: Fetch AI logs client-side and merge by turn number (extra API call)

**Recommendation**: Complete Admin AI Logs (Tasks 8-11) first, then make a backend decision for Victory Screen data.

---

## Implementation Order

1. **Task 8**: ✅ Update TypeScript interface for AILog
2. **Task 11**: ✅ Add version badge to log header
3. **Task 9**: ✅ Add v3 Plan Summary Card to expanded view
4. **Task 10**: ✅ Add fallback warning display
5. **Tasks 5-7**: Victory Screen (requires backend decision first)

---

## Testing Checklist

- [x] Unit test: v3 plan logging with all fields populated
- [x] Integration test: AI log API returns v3 fields correctly
- [ ] Manual test: Admin AI logs show v3 plan details
- [ ] Manual test: Victory screen displays plan (blocked on data decision)

---

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/components/AdminDataViewer.tsx` | Update AILog interface, add v3 display components |
| `frontend/src/components/VictoryScreen.tsx` | (Deferred) Add plan display, version indicators |
| `backend/src/api/routes_actions.py` | (If needed) Add plan info to play-by-play |
