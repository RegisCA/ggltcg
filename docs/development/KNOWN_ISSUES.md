# Known Issues & Workarounds

**Last Updated**: June 29, 2026 (all Active Issues resolved — PRs #349-#351)

This document tracks unresolved issues, their workarounds, and recommended fixes for future sessions.

---

## 🔴 Active Issues

_None currently — see Resolved below._

---

## 🟡 Monitoring Issues

---

## ✅ Resolved

### `ARCHITECTURE.md` / `EFFECT_SYSTEM_ARCHITECTURE.md` — described a pre-CSV effect system that no longer exists

- **Fixed**: June 29, 2026.
- **What it was**: both docs described effects as registered at startup by
  name via `EffectRegistry.register()`/`register_effect()` (e.g.
  `EffectRegistry.register_effect("Knight", KnightEffect)`), with a class
  hierarchy listing card-specific classes like `WizardCostEffect`,
  `SnugglesWhenPlayedEffect`, `UmbruhEffect`, `WakeEffect`, `SunEffect`,
  `RushEffect`, `CleanEffect`, `ArcherEffect` — none of which exist anywhere
  in the current codebase. `EFFECT_SYSTEM_ARCHITECTURE.md` also still framed
  this as a live "Dual System Problem... TECHNICAL DEBT," and both its
  inline effect-type list (missing 7 of the current ~25 types) and
  `EffectRegistry.get_effects()`'s documented "Priority 2: legacy registry"
  fallback were stale beyond just the name-based-registration section
  `KNOWN_ISSUES.md` originally pointed at.
- **Fix**: rewrote the effect type hierarchy diagram and lifecycle section in
  `ARCHITECTURE.md`, and the effect-types list, `EffectRegistry` snippet, and
  "Dual System Problem" section (renamed "Effect Resolution Path") in
  `EFFECT_SYSTEM_ARCHITECTURE.md`, against the actual single CSV-driven
  `EffectFactory.parse_effects()` architecture (`effect_registry.py`,
  `base_effect.py`, `continuous_effects.py`, `action_effects.py`). Both docs
  now point to `ADDING_NEW_CARDS.md` as the canonical, current effect-type
  list instead of carrying their own copies.

### Route-level (HTTP) test coverage gap

- **Fixed**: June 29, 2026.
- **What it was**: `/ai-turn` (509 LOC, 4-way action dispatch + LLM
  fallback), `/tussle` (cost/defender/victory branching), `GET /{game_id}`
  (hand-visibility-by-`player_id`, security-relevant), and `/play-card`
  (status-code mapping) all had real handler logic exercised only at the
  engine/validator layer, never through the actual route. `POST
  /activate-ability` had the same gap until a real `spend_cc`→`spend_charge`
  rename bug shipped to prod for two weeks uncaught — see
  `test_activate_ability_route_spends_charge` in `test_archer_issue_201.py`,
  the template this fix follows.
- **Note**: this doc previously described the gap as fully open. PR #343
  (June 28) had already closed the first layer — one `TestClient`-based
  happy-path test per route, in `backend/tests/test_route_coverage_audit.py`
  — but neither this doc nor `TEST_SUITE_AUDIT_REPORT.md §2`'s own status
  line were updated to reflect that, so the remaining gap looked larger than
  it was.
- **Fix**: added 5 tests covering the specific branches #343 left
  untested: `/ai-turn`'s `tussle` and `activate_ability` dispatch branches
  and its AI-selected-nothing fallback (falls back to `engine.end_turn()`),
  and `/tussle`'s direct-attack (`defender_id` omitted) and victory-response
  branches. `GET /{game_id}` and `/play-card`'s main risk areas
  (hand-visibility, 400 mapping) were already covered by #343 — no further
  work needed there.

### `test_ai_enum_scenario.py` — stale migration-parity gate, not a real correctness check

- **Fixed**: June 29, 2026.
- **What it was**: introduced in PR #331 (WP-4 Phase 4.2) to gate the new
  deterministic-enumerator (`enum`) planner mode against the old dual-LLM
  (`dual`/V4) planner mode's *measured baseline* on two scenarios. The `dual`
  mode was deleted in PR #342 when the AI was pruned to a single
  architecture, but the `≤1` Charge-waste threshold survived and later
  passes reworded the docstring to drop the "vs dual" qualifier, making a
  migration-parity number look like a self-contained correctness bar.
  `charge_wasted` doesn't measure play quality (see prior analysis below),
  and `test_turn2_aggressive_enum` was also gated behind a live,
  non-deterministic Gemini call, so it could flip pass/fail run-to-run
  independent of any code change.
- **Fix**: deleted `backend/tests/test_ai_enum_scenario.py` outright — no
  salvageable assertion. Confirmed nothing else in the test suite imports
  the file or its test names; its local fixtures weren't shared elsewhere.

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
- **Note**: the broader hardcoded-card-name problem this pointed to was fixed
  by "AI card-metadata centralization pending" above (`card_metadata.py`).

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

