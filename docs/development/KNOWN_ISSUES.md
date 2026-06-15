# Known Issues & Workarounds

**Last Updated**: June 15, 2026

This document tracks unresolved issues, their workarounds, and recommended fixes for future sessions.

---

## 🔴 Active Issues

### 1. `HLK` CC-gain mapping bug (planner)

- **Where**: `backend/src/game_engine/ai/turn_planner.py` — `_CC_GAIN_ON_PLAY`
  contains an `"HLK"` key that does not correspond to any real card name, so
  it never matches. CC-gain regrounding for the intended card is silently lost.
- **Impact**: Low — the planner under-credits CC gain in one case; no crash.
- **Status**: Being fixed separately.

### 2. AI card-metadata centralization pending

- **Where**: card names are hardcoded across ~10 files under
  `backend/src/game_engine/ai/` (e.g. `turn_planner.py` `_CC_GAIN_ON_PLAY`,
  `prompts/sequence_generator.py` restriction hints,
  `validators/turn_plan_validator.py`, `quality_metrics.py`).
- **Impact**: Adding or renaming a card with a CC-gain or target-requirement
  effect requires editing several AI files by hand (see
  `docs/development/ADDING_NEW_CARDS.md`, Step 3). Easy to miss one.
- **Status**: Open — needs a single source of card metadata for the AI layer.

---

## 🟡 Monitoring Issues


---

## How to Use This Document

**When you encounter a bug**:
1. Check if it's already listed here
2. If not, add it to "Active Issues" with problem description and workaround
3. Link to relevant code/files
4. Estimate severity and effort to fix

**When you fix something**:
1. Move from "Active" to "Resolved" 
2. Add fix description and date
3. Link to PR/commit if applicable

**Before starting a session**:
1. Review "Active Issues" to see what needs attention
2. Pick quick wins (Low effort, High impact)
3. Update status as you work

---

