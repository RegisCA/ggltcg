# Test Suite Audit — Session Start Prompt

> Paste this into a new session to start the audit. Written 2026-06-28 after
> the AI player pruning work (PR #342) and a CI failure investigation
> surfaced two concrete, unrelated coverage gaps in the same sitting —
> the suite (393 tests as of this writing) is large enough that "it's
> green" no longer means "it's trustworthy" by inspection alone.

## Prompt

Audit the backend test suite (`backend/tests/`, ~393 tests) for coverage
quality, not just count. We don't need more tests reflexively — we need to
know which of the existing ones can actually fail, and where the real gaps
are. Three confirmed starting leads, then open-ended audit:

### 1. `return`-instead-of-`assert` tests (confirmed, not a hypothesis)

Run `cd backend && GOOGLE_API_KEY=dummy-test-key python -m pytest tests/ -q`
and grep the warnings for `PytestReturnNotNoneWarning`. As of 2026-06-28
there are **30 test functions across 6 files** doing `return True`/
`return False` instead of `assert ...`:

- `test_data_driven_effects.py` (3): `test_demideca_effect`,
  `test_effect_data_parsing`, `test_ka_effect`
- `test_effects.py` (3): `test_effect_instantiation`, `test_effect_registry`,
  `test_effect_types`
- `test_game_engine.py` (6): `test_continuous_effects`,
  `test_cost_modification`, `test_play_card`, `test_turn_management`,
  `test_tussle_basic`, `test_victory_condition`
- `test_phase1_effects.py` (7): `test_clean_breaks_all_cards`,
  `test_clean_effect_parsing`, `test_rush_charge_gain`,
  `test_rush_effect_parsing`, `test_rush_first_turn_restriction`,
  `test_sun_effect_parsing`, `test_wake_effect_parsing`
- `test_phase2_effects.py` (6): `test_dream_cost_cannot_go_negative`,
  `test_dream_cost_reduction_no_broken`, `test_dream_cost_reduction_with_broken`,
  `test_dream_effect_parsing`, `test_wizard_effect_parsing`,
  `test_wizard_sets_tussle_cost`
- `test_phase3_effects.py` (5): `test_clean_breaks_umbruh_and_triggers`,
  `test_parse_gain_charge_when_broken_effect`,
  `test_parse_set_self_tussle_cost_effect`,
  `test_raggy_tussle_cost_and_turn_restriction`,
  `test_umbruh_gains_charge_when_broken`

For each: read the function body. Pytest currently only fails a test on an
uncaught exception or a failed `assert` — a bare `return False` at the end
is **silently ignored** for pass/fail purposes today (it'll become a hard
error in a future pytest, which is the only reason these show up at all).
That means **if the logic inside ever computes `False` without raising,
right now nothing fails** — these tests may have been silently toothless for
some unknown period. For each one: figure out what condition the `return`
was gating, confirm whether converting it to `assert <condition>, <message>`
changes any current pass/fail outcome (it shouldn't, if the code is
currently correct — but the whole point is to verify, not assume), and fix
the assertion style. If converting one *does* surface a real failure, that's
a genuine latent bug this audit was meant to find — fix the underlying code,
not the test.

### 2. Route-level (HTTP) coverage gap (confirmed, already partially fixed)

PR #342 found that `routes_actions.py`'s `/activate-ability` endpoint called
a renamed-away method (`spend_cc` instead of `spend_charge`) for two weeks
post-#341 with zero test coverage catching it, because every existing test
for that effect (`test_archer_issue_201.py`) exercises the engine/validator
layer directly and never goes through the actual FastAPI route. One
regression test was added (`test_activate_ability_route_spends_charge`,
using the `TestClient` + `get_game_service()._cache[...]` injection pattern
— see that test for the template, including the `use_database = False`
gotcha needed to avoid depending on a real `POST /games` DB row).

Audit: which other `routes_actions.py` / `routes_games.py` endpoints
(`/play-card`, `/tussle`, `/direct-attack`, `/end-turn`, `/ai-turn`, etc.)
have **zero** HTTP-level test coverage, relying entirely on engine-level
tests that never touch the route handler's own logic (param validation,
error-status mapping, the post-action DB-save call, etc.)? Build the list,
then decide which routes are worth adding a `TestClient` regression test for
— prioritize routes with non-trivial logic in the handler itself (not just a
thin pass-through to the engine), since that's exactly where the `spend_cc`
bug lived.

### 3. Validator "advisory" noise (lower priority, optional)

`TurnPlanValidator` (in `game_engine/ai/validators/turn_plan_validator.py`)
is advisory-only for the enum planner and deliberately incomplete — it
doesn't model every toy-removal/control-change effect (confirmed gaps as of
2026-06-28: Stomp's `break_target`, Jumpscare's return-to-hand, Monster's
`damage_all_opponent_cards`, and crediting the AI's own side when a card is
taken via Twist). This produces false-positive "disagreements" in the admin
AI Logs tab that are harmless (never block a selection) but add noise. Not
urgent — only worth closing if it's actively making the admin UI hard to
read, or as a confidence-building exercise. See PR #342's session notes for
the two example disagreement strings that prompted this.

### 4. Open-ended: does this test still test something that can fail?

Beyond the three leads above, spot-check broadly. Questions to ask of any
given test file:

- **Is the behavior under test now deterministic by construction?** The
  AI player was pruned to a single enum architecture in PR #342 — any
  remaining test asserting on LLM-non-determinism handling, planner-mode
  selection, or provider fallback logic that no longer exists should already
  be gone (it was, as part of #342), but double-check nothing slipped
  through with a different name.
- **Does this test exercise real logic, or just confirm a constant?** E.g. a
  test that asserts `CARD.cost == 2` by reading the same CSV the code under
  test reads is testing the CSV parser, not game logic — useful, but mislabel
  it if it claims to test something else.
- **Mocking depth**: where mocks are used (Gemini client, stats service,
  etc.), confirm the mock's shape still matches the real interface post-#342
  (e.g. `GeminiProvider`/`LLMPlayer` signatures changed — anything mocking
  the old shape would pass for the wrong reason).
- **Skip conditions**: 34 tests currently skip without a real
  `GOOGLE_API_KEY`. Are all 34 actually live-LLM-dependent, or could some
  be rewritten to not need a real key (faster CI, more coverage on every PR)?

Produce a written report: confirmed bugs (with fixes), confirmed-fine areas
(so we don't re-audit them next time), and a prioritized backlog for
anything not worth fixing today. Don't fix everything in one sitting unless
explicitly asked — this is meant to produce a map first.
