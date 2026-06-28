# Test Suite Audit — Report

> 2026-06-28. Companion to `TEST_SUITE_AUDIT_START_PROMPT.md`. Baseline before
> this audit: 393 passed, 34 skipped, 50 warnings (30 `PytestReturnNotNoneWarning`
> + 20 pre-existing `datetime.utcnow()` deprecation warnings in `test_token_refresh.py`,
> unrelated to this audit).

## 1. `return`-instead-of-`assert` tests — FIXED

All 30 functions across the 6 named files converted from `return True`/`return False`
to `assert`. Final suite: **393 passed, 34 skipped, 20 warnings, 0
`PytestReturnNotNoneWarning`**. No production code changes — every issue found was
a test bug, not a game-engine bug.

**Confirmed toothless test:** `test_effects.py::test_effect_registry` (and
`test_effect_instantiation`) asserted against `EffectRegistry.get_all_cards_with_effects()`
/ the legacy name-based `EffectRegistry._effect_map` + `register_effect()` mechanism.
Independently confirmed `register_effect()` is never called anywhere in `src/`
(`effect_registry.py:1149` defines it, `:1231-1235` is just a stale comment showing
example usage) — every card now ships effects via `effect_definitions` in `cards.csv`,
parsed by `EffectFactory`. This test was printing `✗ Missing effects for: {15 cards}`
and **silently passing anyway** before the fix — exactly the failure mode the audit
was looking for. Rewrote both tests against the real data-driven path.

**Test-setup bugs found (not game-engine bugs):**
- `test_ka_effect` / `test_demideca_effect` in `test_data_driven_effects.py` never
  set `card.zone = Zone.IN_PLAY` on the boosting/boosted cards. `StatBoostEffect.modify_stat`
  (`continuous_effects.py:212`) correctly requires `Zone.IN_PLAY` before applying a
  buff (an intentional Issue #123 guard against off-board cards buffing). With the
  default zone, the boost was silently a no-op — the bare `return False` covered this
  up. Fixed by setting the zone explicitly, matching the pattern already used in
  `test_phase2_effects.py`. Production code was correct; the test wasn't exercising it.
- `test_effect_data_parsing` asserted Wizard's `effect_definitions == ""` ("uses
  legacy registry") — stale; Wizard is now data-driven (`set_tussle_cost:1`), already
  confirmed elsewhere by `test_phase2_effects.py::test_wizard_effect_parsing`. Updated.

**Verdict:** this lead is closed. Diff is `backend/tests/{test_data_driven_effects,
test_effects,test_game_engine,test_phase1_effects,test_phase2_effects,test_phase3_effects}.py`.

## 1b. Charge-budget assertions in live-LLM tests — TIGHTENED

Follow-up to §1, prompted by a direct challenge: the live-LLM-gated charge
tests (`test_turn_planner.py`, `test_ai_turn1_planning.py`) carried a stale
premise — comments like *"charge_start is LLM-generated metadata... we
accept any non-negative value"* and *"Uses KNOWN card costs rather than
trusting AI's reported charge_cost, since LLMs sometimes report incorrect
values"*. Verified against the actual current code
(`turn_planner.py:253-261`, `enumerator.py:240-250`): charge numbers are
100% engine-derived today — each candidate sequence is built by literally
running the action through `GameEngine` and reading back the resulting
Charge. The LLM only picks a sequence index; it never generates a Charge
number. So a charge-math mismatch is a real bug, not LLM noise.

Found and fixed: `test_ai_turn1_planning.py` defined `validate_charge_math`
**twice** — once (lines 28-106) with a hand-maintained `CARD_COSTS` table
that could drift from `cards.csv` and downgraded equality mismatches to
print-only warnings, and again (line 643) with a simpler version that only
checked for negative Charge. Since Python resolves module-level names at
call time, every caller silently used the *second* definition — the first,
more elaborate one was dead code, never executed.

Fix: consolidated into one canonical `validate_charge_math()` in
`tests/ai_test_support.py` (shared by both files), using
`TurnPlanner._CHARGE_GAIN_ON_PLAY` instead of a duplicated cost table, and
asserting exact `charge_after` equality (not just non-negativity) as a real
error. Removed ~15 print-only "expected: X" diagnostics across
`test_turn_planner.py` that computed an expected value and never asserted
it; added `assert not validate_charge_math(plan)` to every test that
generates a plan. Verified against real Gemini (not just the dummy-key
skip path): all 30 affected tests pass live. One unrelated, pre-existing,
reproducible failure surfaced incidentally in `test_ai_enum_scenario.py`
(`test_turn2_aggressive_enum`, untouched by this fix) — the AI wastes 2
Charge instead of ≤1 on that scenario. That's a live AI strategic-quality
gap, not a test bug; left as a backlog item below since it's outside this
audit's scope.

## 2. Route-level (HTTP) coverage gap — 4 regression tests added

Template precedent: `test_activate_ability_route_spends_charge` in
`test_archer_issue_201.py:402-475` (TestClient + `get_game_service()._cache[...]`
injection + `use_database = False`).

| Endpoint | HTTP test? | Handler complexity | Untested risk |
|---|---|---|---|
| `POST /activate-ability` | **Yes** | Non-trivial | (covered, PR #342) |
| `POST /ai-turn` | No | **High (509 LOC)** | 4-way action dispatch, LLM fallback, stats logging |
| `POST /tussle` | No | Non-trivial (104 LOC) | cost calc, defender lookup, 2 victory branches, DB save |
| `GET /{game_id}` | No | Non-trivial (55 LOC) | hand-visibility-by-player_id, stat/cost buff calc |
| `POST /play-card` | No | Non-trivial (87 LOC) | victory branching, status-code mapping, DB save |
| `GET /{game_id}/debug` | No | Non-trivial (147 LOC) | effect parsing helpers |
| `POST /end-turn` | No | Thin | side effects, DB save |
| `GET /valid-actions`, `GET /cards`, `POST /`, `POST /random-deck`, `POST /quick-play`, `DELETE /{game_id}`, `GET /{game_id}/logs`, `POST /narrative` | No | Thin | pass-through, low risk |

**Priority order for new TestClient regression tests** (same reasoning as the
`spend_cc` bug: real handler logic + zero HTTP coverage):

1. `POST /ai-turn` — largest handler, dispatches all 4 action types with its own
   error handling and stats logging; a dispatch-routing bug here is exactly the
   shape of bug that engine-level tests can't see.
2. `POST /tussle` — cost/defender/victory branching at the route layer.
3. `GET /{game_id}` — hand-visibility-by-`player_id` is security-relevant (wrong
   player seeing hidden hand data would be a real bug, not just a test gap).
4. `POST /play-card` — status-code mapping (`ValueError`→400, `Exception`→500) is
   route-layer-only and currently asserted nowhere.

**Not done yet** — writing these 4 tests is a discrete chunk of new work
(~30-60 min each, following the established pattern). Backlog, see below.

## 3. Validator advisory noise — confirmed, stays in backlog

`game_engine/ai/validators/turn_plan_validator.py`. All 4 known gaps confirmed real
by grep: Stomp's `break_target` and Monster's `damage_all_opponent_cards` are
completely unmodeled; Jumpscare's `return_target_to_hand` is only caught when the
card is named "Twist" (Jumpscare has the same effect, different card, not matched);
Twist-crediting doesn't track which side owns the returned card, so it can't tell
AI-targets-own-toy from AI-targets-opponent-toy. Zero test coverage on any of this
(no `test_*validator*` files exist; only indirect mentions in
`test_enum_planner_integration.py`). Confirmed harmless (advisory-only, never blocks
a selection) — no production-code risk. Per project context, leave in backlog.

## 4. Open-ended spot check

- **Stale AI-architecture references**: none found. Clean grep for "planner mode",
  multi-provider, provider-fallback language across `backend/tests/` — PR #342's
  cleanup was thorough.
- **Constant-confirmation tests mislabeled as logic tests**: minor, cosmetic only.
  `test_batch1_vanilla_toys.py::test_car_stats` and similar are CSV-parser regression
  tests dressed as toy-mechanics tests — fine to leave, not misleading enough to
  cause confusion, but flagging for awareness.
- **Mock-shape drift**: none found. No tests currently mock `GeminiProvider` /
  `LLMPlayer` at the unit level — live-LLM tests are gated behind the API-key skip
  instead of mocked, so there's no stale-mock-interface risk to begin with.
- **Skip conditions (34 total)**: 32 are gated on a real `GOOGLE_API_KEY` and
  validate genuine semantic correctness of live Gemini responses (action ordering,
  charge math, targeting) — confirmed not rewritable without losing real coverage.
  The remaining 2 (`test_db_integration.py`, `test_lobby.py`) are intentional
  integration-test skips (need a real DB / running server). All 34 are justified.

## Backlog (prioritized, nothing here fixed today)

1. **Add the 4 route-level regression tests** identified in §2 (`/ai-turn`,
   `/tussle`, `GET /{game_id}`, `/play-card`) — highest-value remaining item,
   directly modeled on the `/activate-ability` precedent that caught a real bug.
2. **Validator gaps** (§3) — Stomp/Monster/Jumpscare/Twist-ownership — low urgency,
   advisory-only, fix opportunistically or as a confidence-building exercise.
3. **Cosmetic test mislabeling** (§4) — rename/docstring-only, no urgency.

## Confirmed-fine (no further audit needed unless code changes)

- AI architecture is single enum+Gemini throughout the test suite, no stale
  multi-provider remnants.
- No Gemini/LLM mock-interface drift.
- All 34 skip conditions are justified as-is.
