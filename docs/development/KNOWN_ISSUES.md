# Known Issues & Workarounds

**Last Updated**: June 15, 2026

This document tracks unresolved issues, their workarounds, and recommended fixes for future sessions.

---

## 🔴 Active Issues

### 1. `AI_VERSION` vs `AI_PLANNER_MODE` — unfinished migration (confusing footgun)

- **Where**: `backend/src/game_engine/ai/llm_player.py` (`get_ai_player()`) and
  `turn_planner.py` (`get_planner_mode()`).
- **Problem**: two env vars appear to select the planner mode, but only
  **`AI_VERSION`** does in the running app. `get_ai_player()` derives the mode from
  `AI_VERSION` (`4` → dual/V4, else → single) and passes it explicitly, so
  `get_planner_mode()` — the only reader of `AI_PLANNER_MODE` — is never reached.
  **`AI_PLANNER_MODE` is therefore a no-op in the deployed app** (prod has it set to
  `single` while actually running V4/dual via `AI_VERSION=4`).
- **Impact**: high confusion; easy to "switch modes" by editing `AI_PLANNER_MODE`
  and have nothing change. `AI_MODEL` is similarly ignored when `AI_PROVIDER=gemini`.
- **Fix**: pick one authoritative variable (recommend `AI_PLANNER_MODE`), make
  `get_ai_player()` honor it, and retire/alias the other. Until then, set
  `AI_VERSION`. See `docs/development/ai/AI_CURRENT_STATE.md`.

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

## ✅ Resolved

### `HLK` CC-gain mapping bug + phantom card cluster (planner/validator)

- **Fixed**: June 15, 2026 (WP-3, branch `fix/hlk-cc-gain-mapping`).
- **What it was**: both `_CC_GAIN_ON_PLAY` (turn_planner) and `CC_GAIN_ON_PLAY`
  (turn_plan_validator) had a phantom `"HLK"` key matching no real card. The same
  validator also carried a dead `CC_GAIN_TRIGGERS` dict, unreachable "Red Solo Cup"
  branches (not a real card), and a reachable-but-wrong credit giving Umbruh +1 CC
  on *tussle* (Umbruh gains CC when *sleeped*, not on tussle).
- **Fix**: removed all phantom/wrong entries; corrected two direct-attack error
  messages; added `tests/test_cc_gain_tables.py` pinning both tables to real cards
  whose CSV effect is a play-triggered `gain_cc:` (and keeping the two tables in sync).
- **Note**: the broader hardcoded-card-name problem remains — see Active Issue #1.

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

