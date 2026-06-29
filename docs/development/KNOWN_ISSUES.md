# Known Issues & Workarounds

**Last Updated**: June 28, 2026

This document tracks unresolved issues, their workarounds, and recommended fixes for future sessions.

---

## 🔴 Active Issues

(none)

---

## 🟡 Monitoring Issues

---

## ✅ Resolved

### `TurnPlanValidator` — advisory-only relic of the pre-enum architecture

- **Fixed**: June 28, 2026 (AI dead-code cleanup pass).
- **What it was**: `TurnPlanValidator` (and its package, `ai/validators/`) ran
  against every enumerated sequence each turn, but its result only fed a log
  line and an admin-UI debug field — it never dropped a sequence or changed
  the returned plan, since enumerated sequences are engine-legal by
  construction. It also carried its own hardcoded, incomplete card knowledge
  (e.g. assumed tussles always cost 2, wrong for Raggy's 0-cost tussles).
- **Fix**: deleted `ai/validators/` entirely, the call sites in
  `turn_planner.py`, the `sequence_disagreements`/`sequences_after_validation`
  admin-UI fields, and the now-unbuildable `backend/scripts/run_v4_simulation.py`
  (broken by the same architecture pruning, PR #342).

### AI card-metadata centralization pending

- **Fixed**: June 28, 2026 (AI dead-code cleanup pass).
- **What it was**: the Charge-gain-on-play table (Surge +1, Rush +2, Cake +5)
  was hand-copied into four places — `turn_planner.py` `_CHARGE_GAIN_ON_PLAY`,
  `enumerator.py` (inline dict, already missing Cake — proof the copies
  drift), `prompts/strategic_selector.py` (inline conditionals), and
  `quality_metrics.py` (inline conditionals plus a separate hardcoded
  action-card-name list). Adding or renaming a Charge-gain card required
  editing several AI files by hand; easy to miss one.
- **Fix**: added `game_engine/ai/card_metadata.py`, which derives
  `CHARGE_GAIN_ON_PLAY` and `ACTION_CARD_NAMES` from `cards.csv` at import
  time. `turn_planner.py`'s copy of the table was deleted outright (it only
  fed the now-removed `TurnPlanValidator` advisory check — see below); the
  other three sites now import the shared constants. Pinned by
  `tests/test_card_metadata.py`.

### `AI_VERSION` vs `AI_PLANNER_MODE` — unfinished migration (confusing footgun)

- **Fixed**: June 15, 2026 (WP-4 Phase 4.2, branch `feat/deterministic-enumerator`).
- **What it was**: two env vars appeared to select the planner mode, but only
  **`AI_VERSION`** did in the running app. `get_ai_player()` derived the mode from
  `AI_VERSION` and passed it explicitly, so `get_planner_mode()` — the only reader
  of `AI_PLANNER_MODE` — was never reached, making `AI_PLANNER_MODE` a no-op in the
  deployed app.
- **Fix**: `get_ai_player()` now resolves the mode via `get_planner_mode()`, making
  **`AI_PLANNER_MODE` authoritative** (`single` / `dual` / `enum`). Back-compat is
  preserved — `AI_VERSION=4` with no `AI_PLANNER_MODE` still resolves to `dual`
  (`get_planner_mode()` falls back to `AI_VERSION`). Pinned by
  `tests/test_planner_mode_selection.py`, including the `AI_VERSION=4 → dual`
  back-compat case so deployed prod behavior does not shift.
- **Superseded**: June 28, 2026 — the entire planner-mode/provider concept this
  issue was about (`single`/`dual`/`enum`, `AI_VERSION`, `AI_PLANNER_MODE`,
  `AI_PROVIDER`) was removed in the AI player pruning pass. There is now a
  single architecture (enum + Gemini), so this footgun can no longer recur.
  `tests/test_planner_mode_selection.py` was deleted along with it.

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
- **Note**: the broader hardcoded-card-name problem remains — see Active Issue #1
  (AI card-metadata centralization).

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

