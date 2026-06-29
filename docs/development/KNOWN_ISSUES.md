# Known Issues & Workarounds

**Last Updated**: June 29, 2026 (mechanical dead-code scan)

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

### 2. Route-level (HTTP) test coverage gap

- **Where**: full detail, priority order, and per-route handler-complexity
  notes are in `docs/plans/TEST_SUITE_AUDIT_REPORT.md` §2 — this entry is a
  pointer so it's visible from this doc too, not a duplicate.
- **What it is**: `/ai-turn` (509 LOC, 4-way action dispatch + LLM fallback),
  `/tussle` (cost/defender/victory branching), `GET /{game_id}`
  (hand-visibility-by-`player_id`, security-relevant), and `/play-card`
  (status-code mapping) all have real handler logic and zero HTTP-level test
  coverage — only engine/validator-level tests exercise the logic they call.
  `POST /activate-ability` had the same gap until a real `spend_cc`→`spend_charge`
  rename bug shipped to prod for two weeks uncaught (see
  `feedback_rename_refactor_route_coverage_gap` in session memory); it now has
  a `TestClient`-based regression test (`test_activate_ability_route_spends_charge`
  in `test_archer_issue_201.py`) that's the template to copy for these four.
- **Note**: §3 of that same report ("validator advisory noise... leave in
  backlog") is now moot as of PR #344 — `TurnPlanValidator` no longer exists.
- **Status**: Open — not yet started, no committed timeline.

---

## 🟡 Monitoring Issues

---

## ✅ Resolved

### Mechanical dead-code scan — legacy `EffectRegistry` dispatch path + assorted orphans

- **Fixed**: June 29, 2026.
- **What it was**: ran `vulture` (backend) and `knip` (frontend) for the first time
  against this repo, then hand-verified every hit (both tools are dominated by
  framework false positives — FastAPI routes, SQLAlchemy event listeners, Click
  commands, multi-entry Vite blind spots — so raw output isn't actionable on its
  own). The biggest find: `EffectRegistry`'s entire legacy name-based dispatch
  path (`_effect_map`, `register_effect`, `has_effects`, `clear_registry`,
  `get_all_cards_with_effects`, plus 5 effect classes — `KaEffect`,
  `WizardEffect`, `DemidecaEffect`, `RaggyEffect`, `DreamCostEffect`) predates the
  current CSV-driven `EffectFactory` system. `register_effect` was never called
  (only a commented-out example remained), so the registry's "Priority 2"
  fallback branch never fired for any card — `tests/test_effects.py` already had
  a docstring saying as much. Also found: a whole second implementation of the
  `/maintenance/cleanup` logic in `StatsService` (`cleanup_old_ai_logs` /
  `cleanup_old_playback` / `cleanup_old_simulations`) that was never wired to the
  actual route (which does the same thing via inline SQL) — only its own unit
  test called it. And a frontend component, `PlayerZone.tsx`, that's been
  unreferenced since `GameBoard.tsx` was decomposed into smaller zone
  components, yet kept receiving drive-by edits from global refactors
  (terminology rename, Tailwind-token passes) that touched every file in
  `components/` without checking liveness first.
- **Fix**: removed the legacy registry path and its 5 dead effect classes, two
  orphaned `TriggerTiming` enum members (`WHEN_OPPONENT_TUSSLES`, `END_OF_TURN`
  — stale "# Beary" comment, no dispatch branch ever checked them), the
  entirely-unused `effects_constants.py` module (and the two tautological tests
  that only asserted its constants equal themselves), the duplicate
  `StatsService` cleanup methods, several one-off dead methods across the API/AI
  layers, stale `--v1/--v2` CLI examples in two simulation docs left over from
  the AI-pruning pass (#342), and 4 orphaned frontend files (`PlayerZone.tsx`,
  `CardHoverPreview.tsx`, `TurnTransition.tsx`, `App.css`) plus several unused
  exported types/functions. Net: 31 files, +19/−1351 lines. All 389 backend
  tests pass; frontend `tsc -b && vite build` succeeds.

### AI test suite — purged tautological/toothless tests

- **Fixed**: June 28, 2026, following on from the `TurnPlanValidator`/
  Charge-gain cleanup below and the `test_ai_enum_scenario.py` finding above.
- **What it was**: a broad pass across all 12 AI-related test files (~70
  tests) found ~24 that could never fail regardless of AI quality, confirmed
  against the actual `ActionValidator`/effect code, not just inference:
  - `test_ai_wake_hallucination.py` — only exercised `TurnPlanner.create_plan`
    (Phase 1 selection), whose schema (`selected_index`/`reasoning`/
    `lethal_check`) has no target field at all; the LLM cannot specify a
    target there anymore. Superseded by `TestHallucinatedTargetGuard` in
    `test_ai_multi_target.py`, which tests the one place (Phase 2 execution
    fallback) where target hallucination is still structurally possible.
  - `test_turn_planner.py` (whole file, "AI v3 Turn Planner") — nearly every
    test's only real assertion was `validate_charge_math`, guaranteed by
    construction since Charge numbers are 100% engine-derived. Several were
    also toothless independent of that: `test_wizard_high_threat`,
    `test_direct_attack_opportunity`, `test_hind_leg_kicker_play_first`,
    `test_surge_enables_extra_direct_attacks`, `test_vvaj_before_tussle`,
    `test_dream_cost_reduction_combo` computed an interesting value and
    printed an "OPTIMAL"/"ERROR" label without ever asserting on it.
  - `test_ai_turn1_planning.py` — `test_turn1_drop_without_targets` /
    `test_turn1_archer_without_targets` (an action with no legal target is
    never added to `valid_actions`, `action_validator.py:228`/`:413-415`),
    `test_cannot_play_card_from_break_zone` (`play_card` only ever enumerates
    hand cards), `test_copy_only_targets_own_toys` (`CopyEffect.get_valid_targets`
    only returns the player's own in-play cards), `test_suicide_attack_prevention`
    and half of `test_must_tussle_to_win_not_direct_attack` (the enumerator's
    `filter_for_ai=True` already drops guaranteed-loss tussles and
    `direct_attack` is only ever offered when the opponent has zero toys in
    play — `action_validator.py:328`,`:350-351`), plus the duplicate
    `test_turn1_regression_suite` and tautological
    `test_charge_math_consistency`.
  - `test_ai_multi_target.py` — `test_llm_player_parses_target_ids_array` and
    `test_llm_player_handles_legacy_target_id` called no production code at
    all, just reimplemented parsing logic inline and asserted it against
    itself; `test_optimal_play_is_wake_then_sun` asserted local constants
    equal themselves, with its own docstring admitting "this is a
    documentation test."
- **Fix**: deleted `test_ai_wake_hallucination.py` and `test_turn_planner.py`
  outright; trimmed `test_ai_turn1_planning.py` down to the three tests whose
  failure mode is still legally reachable (`TestWinningTussle`,
  `TestKnightEfficiency`, `TestCombatMath::test_attacker_wins_clean`) and
  `test_ai_multi_target.py` down to the tests that exercise real, live code
  paths. Caught by going looking for this pattern deliberately after
  `test_ai_enum_scenario.py` (above) turned out to be one instance of it
  rather than a one-off.

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

