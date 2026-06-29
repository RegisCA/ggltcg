# Known Issues & Workarounds

**Last Updated**: June 28, 2026

This document tracks unresolved issues, their workarounds, and recommended fixes for future sessions.

---

## 🔴 Active Issues

### 1. `test_ai_enum_scenario.py` — stale migration-parity gate, not a real correctness check

- **Where**: `backend/tests/test_ai_enum_scenario.py` —
  `test_turn1_surge_knight_enum` and `test_turn2_aggressive_enum`.
- **What it actually is**: introduced in PR #331 (WP-4 Phase 4.2) to gate the
  new deterministic-enumerator (`enum`) planner mode against the old
  dual-LLM (`dual`/V4) planner mode's *measured baseline* on two scenarios.
  Original docstring: "Gate: ... CC waste ≤ **the dual baseline** (≤1)", and
  both assertions originally read
  `f"enum wasted {X} CC (dual baseline ≤1)"`. The `dual` mode and its own
  test file (`test_ai_standard_scenario.py`) were deleted in PR #342 when the
  AI was pruned to a single architecture. The `≤1` threshold survived, and
  later passes (PR #341's cc→charge rename, then #342/#343's doc cleanup)
  reworded the docstring to "Gate: ... Charge waste ≤1" — dropping the "vs
  dual" qualifier and making a migration-parity number look like a
  self-contained correctness bar. There is no longer a `dual` baseline to be
  ≤ of.
- **Why it doesn't actually test anything useful now**: `charge_wasted`
  doesn't measure play quality. Enumerating `test_turn2_aggressive_enum`'s
  exact scenario shows a 0-waste sequence exists (play Archer, play Umbruh,
  activate Archer's stamina-removal ability against no remaining valid
  target, then tussle) but it is not obviously *better* play than the 2-waste
  line the AI actually picked (tussle only, hold the rest of the hand) —
  Archer's ability has nothing useful to target once the opponent's only toy
  is broken, and playing Umbruh just exposes a second toy for no immediate
  benefit. The metric rewards "spent the number" over "made a good
  decision." `test_turn1_surge_knight_enum` currently passes, but for the
  same non-reason — it happens to coincide with the obviously-correct
  Surge→Knight→direct_attack line in that simpler scenario, not because the
  metric is principled.
- **Compounding problem**: gated behind a live, non-deterministic Gemini call
  (skipped without a real API key), so `test_turn2_aggressive_enum` will flip
  pass/fail run-to-run independent of any code change — reproduced as
  failing identically on `main` before PR #344's unrelated changes, via a
  throwaway worktree.
- **Caught and rationalized twice**: PR #343's test-suite audit found this
  exact failure and filed it as "a live AI strategic-quality gap... left as a
  backlog item," and it was rationalized the same way again during PR #344's
  review — both times treating the failure as actionable AI-quality
  feedback instead of recognizing the test's premise (compare against a
  deleted `dual` baseline) no longer holds. Caught on the third pass only
  because the user pushed back and the original PR #331 docstring was pulled
  via `git show`.
- **Status**: Open — recommend deleting both tests in
  `test_ai_enum_scenario.py` (or rewriting them against a real, current
  notion of correctness, not a deleted mode's baseline) rather than
  continuing to treat their failures as actionable.

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

