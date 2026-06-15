# Audit Remediation Plan — June 2026

**Created**: June 11, 2026
**Source**: Full-codebase audit (engine, docs, AI player) — June 11 session
**Status**: WP-0 ✅ · WP-1 ✅ (#327) · WP-2 ✅ (#326) · WP-3 ✅ (#328) · AI-config correction ✅ (#329) · **WP-4 ready (next, hands-on)**

Each work package (WP) is one PR-sized unit with explicit acceptance criteria and a
self-contained starter prompt. Starter prompts are written for a cold agent session —
they embed the audit findings so no re-discovery is needed.

**Workflow for every WP** (per `bot-workflow.instructions.md`):

```bash
gh auth switch -u regisca-bot
git checkout main && git pull
git checkout -b <branch>
# ... work, commit ...
git push -u origin <branch>
gh pr create --base main
# Review and merge as RegisCA
```

**Execution order**: WP-0 (local, 10 min) → WP-1 and WP-2 (parallel-safe) → WP-3 → WP-4.

---

## WP-0: Rebuild local venv (LOCAL TASK, not a PR) ✅ COMPLETE

The repo-root `.venv` had broken (its interpreter symlink pointed at a Python that
was removed by a package-manager upgrade). Rebuilt on Python 3.13 — the version
production pins via `render.yaml` → `PYTHON_VERSION`. Full backend suite passes
locally with a dummy `GOOGLE_API_KEY`.

> Gotcha for next time: a `uv`-created venv does **not** include `pip`. Install
> with `uv pip install`, not `python -m pip install` (the latter no-ops with
> "No module named pip"). A plain `python -m venv` ships pip and works the usual way.

---

## WP-1: Documentation truth pass + AI current-state doc ✅ COMPLETE (PR #327)

**Branch**: `docs/audit-truth-pass` · **Estimate**: one session · **Type**: docs only, no code changes

> **Correction (post-merge, PR docs/ai-config-correction):** the starter prompt
> below told the agent "single-request planning is the default / dual is
> experimental." That was wrong — it came from reading `.env.example` /
> `get_planner_mode()` without tracing `get_ai_player()`. **Production actually
> runs dual/V4 on Gemini, selected by `AI_VERSION=4`; `AI_PLANNER_MODE` is a no-op
> in the live path.** The merged docs were corrected accordingly. See
> `docs/development/ai/AI_CURRENT_STATE.md` and KNOWN_ISSUES Active Issue #1.

### Starter prompt

```
## Context
You are fixing documentation drift identified in a June 2026 codebase audit.
This is a docs-only PR — do not modify any .py or .ts files.
Read docs/plans/AUDIT_2026_06_REMEDIATION.md (WP-1 section) first.

Ground truth to verify against before writing:
- backend/data/cards.csv has 30 cards (count the rows).
- The AI default is AI_PLANNER_MODE=single (see backend/src/game_engine/ai/turn_planner.py
  get_planner_mode() and backend/.env.example). "dual" (V4) is experimental.
- Supported providers: gemini, groq, openrouter (backend/src/game_engine/ai/providers.py).
  Default models: gemini-flash-lite-latest (gemini), llama-3.3-70b-versatile (groq).
- Frontend is React 19, Vite 7, Tailwind 4 (frontend/package.json).
- The venv lives at the REPO ROOT (.venv), not in backend/.
- run_server.py's flag is --deck (not --deck-csv).

## Task A — fix these specific stale references (all verified broken in the audit)
1. docs/README.md:
   - Links to plans/INSTRUCTION_FILES_MIGRATION_PLAN.md and DOCS_RESTRUCTURING_PLAN.md
     → both moved to docs/development/archive/. Fix or drop.
   - Link to development/features/ADDING_NEW_CARDS.md → actual path is
     development/ADDING_NEW_CARDS.md.
   - The "Root Context Files" section lists AGENTS.md twice — deduplicate.
2. AGENTS.md (root): tech-stack table says React 18 and "Google Gemini 1.5 Flash" —
   update to React 19 and the provider abstraction (Gemini default
   gemini-flash-lite-latest; Groq/OpenRouter supported; AI_PROVIDER/AI_PLANNER_MODE
   env vars). Update the "AI System (V4)" section: dual-request is the experimental
   mode; single-request planning is the default. Keep file structure otherwise.
3. README.md:
   - "Google Gemini AI v3" badge and the "LLM-Powered AI Opponent (v3)" feature bullet
     → describe current state (single-request turn planning by default, experimental
     dual-request mode, multi-provider).
   - "27-card set" / "(27 cards)" in the project-structure tree → 30 cards.
   - Quickstart: venv commands create it in backend/ — change to repo root .venv,
     matching reality. Also fix the --deck-csv example → --deck.
   - Verify the "37 endpoints" / "34 components" counts or remove the numbers.
4. CONTRIBUTING.md: venv path says backend/venv → repo-root .venv, consistent with README.
5. docs/development/ARCHITECTURE.md:
   - Repair the broken markdown code fences (many blocks close with ```text, mangling
     rendering from the "Effect Lifecycle" section onward).
   - Card counts: says 27 in one place, 30/31 in another → 30 throughout.
   - "Known Issues & Technical Debt" section repeats the same two resolved items twice
     → deduplicate.
   - Directory tree shows ai/prompts.py → it is now the ai/prompts/ package.
6. docs/development/ADDING_NEW_CARDS.md: Step 3 says "Add card to
   backend/src/game_engine/ai/prompts.py" — that file was deleted in Nov 2025.
   Replace with the actual AI-layer touchpoints for a new card:
   - backend/src/game_engine/ai/prompts/card_guidance.yaml (strategic guidance)
   - backend/src/game_engine/ai/prompts/examples/card_examples.py and loader.py
     (optional few-shot examples, dual mode only)
   - NOTE in the doc: several AI files currently hardcode card names
     (sequence_generator.py restriction hints, turn_planner.py/_CC_GAIN_ON_PLAY,
     validators/turn_plan_validator.py, quality_metrics.py) — cards with CC-gain or
     target-requirement effects need entries there until metadata is centralized.
7. backend/src/simulation/README.md: "Related Documentation" links to
   docs/development/SIMULATION.md, AI_V4_ARCHITECTURE.md, SIMULATION_IMPROVEMENTS.md —
   none exist. Point to docs/development/SIMULATION_SYSTEM.md,
   docs/development/ai/AI_V4_DESIGN.md, docs/development/archive/SIMULATION_IMPROVEMENTS.md.
8. backend/AGENTS.md: "Files" list under AI System includes
   prompts/turn_planner.py — actual path is ai/turn_planner.py. Also note single vs
   dual planner modes.
9. docs/development/KNOWN_ISSUES.md: stale empty shell dated January. Either populate
   with current actives (HLK CC-gain mapping bug — see WP-3; AI card metadata
   centralization pending) or delete the file and remove references to it.

## Task B — write docs/development/ai/AI_CURRENT_STATE.md (the key deliverable)
A single page that makes the AI subsystem inheritable. Contents:
- Current architecture: planner modes (single = default, one request, optimized for
  Groq token budgets, server-side plan pruning + CC regrounding; dual = V4
  experimental, sequence generation → TurnPlanValidator → strategic selection).
- Execution layer: heuristic plan-step matching, LLM fallback matcher, mid-turn
  replan (cap 2), V2 single-action fallback.
- Env var reference: AI_PROVIDER, AI_MODEL, AI_FALLBACK_MODEL, AI_PLANNER_MODE,
  GEMINI_MODEL, GEMINI_FALLBACK_MODEL, GOOGLE_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY.
- Version history table: V1 per-action (Nov 2025) → V2 structured output (Dec 2025)
  → V3 single-request turn planning (Dec 2025, prompts too large, illegal actions)
  → V4 dual-request (Jan 2026, balanced 160-game baseline) → provider era
  (May–Jun 2026, AI_PLANNER_MODE, Groq default-capable).
- How to evaluate changes: quality metrics (CC waste), tests/test_ai_standard_scenario.py,
  the simulation CLI (currently dormant).
- Add a one-line "Historical — superseded by AI_CURRENT_STATE.md" banner at the top of
  docs/development/ai/AI_V4_DESIGN.md, AI_V4_BASELINE.md, and
  docs/plans/AI_V4_REMEDIATION_PLAN.md.
- Link the new doc from docs/README.md and AGENTS.md.

## Constraints
- Docs only. Do not "fix" code to match docs — docs match code.
- Run the markdown linter if configured (.markdownlint-cli2.json exists).
- Verify every link you touch actually resolves (test -e each target path).

## Verification
- A link-check pass over every file you edited (no references to nonexistent paths).
- Commit, push, open PR as regisca-bot per the workflow at the top of the plan doc.
```

### Acceptance criteria

| # | Criterion |
|---|-----------|
| 1.1 | Every link in edited docs resolves to an existing file |
| 1.2 | No doc claims React 18, Gemini 1.5, 27 cards, or backend-local venv |
| 1.3 | `AI_CURRENT_STATE.md` exists, linked from docs/README.md and AGENTS.md |
| 1.4 | V4 docs carry a historical banner |
| 1.5 | ADDING_NEW_CARDS Step 3 describes real AI-layer touchpoints |

---

## WP-2: Dead-code sweep + CI hygiene ✅ COMPLETE (PR #326)

**Branch**: `chore/audit-dead-code-sweep` · **Estimate**: short session · **Type**: deletions + one-liners, no behavior change

### As shipped (deviations from the starter prompt below)

- **Task 3 went further**: removed not only the dead Snuggles effect but also the
  legacy `UmbruhEffect` class — both were unregistered dead code (Umbruh resolves via
  the data-driven `gain_cc_when_sleeped:1`). That emptied `triggered_effects.py`, so
  the whole module and its `from . import triggered_effects` were dropped.
- **Task 4 was scoped down**: only the `turn3_analysis/` log dump and its one-off
  generator (`investigate_turn3_failure.py`) were removed. Broader `backend/scripts/`
  archiving was **deferred** — several one-off scripts are still referenced by
  AI-history docs (edited in WP-1's PR #327), so moving them now would orphan those
  links. Tracked in the "Deferred" section.
- Also added `.venv/` to `.gitignore` (the repo ignored `venv/` but not the
  now-documented repo-root `.venv/`).

### Starter prompt

```
## Context
Maintenance PR removing dead code identified in a June 2026 audit. Pure
deletion/cleanup — zero behavior changes. Read docs/plans/AUDIT_2026_06_REMEDIATION.md
(WP-2). Verify each claim with grep before deleting; the audit findings are listed
below but you must confirm imports/usages yourself.

## Tasks
1. Delete backend/src/game_engine/ai/prompts/planning_prompt_v2.py — audit found
   nothing imports it. Confirm: grep -rn "planning_prompt_v2" backend/src backend/tests.
2. Prune backend/src/game_engine/ai/prompts/planning_prompt.py (V1, 618 lines):
   only some helpers are still used (e.g. format_sleep_zone_for_planning, imported via
   prompts/__init__.py into turn_planner.py). Grep each symbol exported in
   prompts/__init__.py from planning_prompt (get_planning_prompt,
   format_hand_for_planning, format_in_play_for_planning, format_sleep_zone_for_planning,
   THREAT_PRIORITIES, CC_COST_REFERENCE) for usages outside the prompts package.
   Delete dead ones from both the module and __init__.py exports; keep live helpers.
3. Delete SnugglesWhenSleepedEffect (and any other Snuggles effect classes) from
   backend/src/game_engine/rules/effects/triggered_effects.py — Snuggles is not in
   backend/data/cards.csv. Remove its registration and the Snuggles mentions in
   base_effect.py docstrings/comments. Keep Umbruh untouched. Confirm no test
   references Snuggles effects (grep tests/).
4. backend/scripts/ holds ~24 one-off debugging scripts (debug_log_6259.py,
   investigate_turn3_failure.py, analyze_*.py, gate_user_slot3*.py, etc.) plus the
   committed turn3_analysis/ directory of raw January debug logs.
   git rm the turn3_analysis/ directory (history preserves it) and move clearly
   one-off scripts into backend/scripts/archive/ with a one-line README. Keep
   genuinely reusable tools (run_v4_simulation.py, run_standard_scenario.py,
   analyze_simulation_results.py, backfill/reset/verify scripts) at top level —
   use judgment, list your keep/archive split in the PR description.
5. .github/workflows/ci.yml: node-version '18' → '20' (Vite 7 requires Node 20.19+;
   18 passing today is luck, not support).
6. backend/src/game_engine/ai/prompts/strategic_selector.py: module docstring says
   "Temperature: 0.7" but get_strategic_selector_temperature() returns 0.4. Fix the
   docstring (code is the truth). Also remove the duplicated
   `logger = logging.getLogger(__name__)` (it appears twice near the imports).
7. Do NOT touch card_library.py — it is still imported by formatters.py (V2 fallback
   path). Out of scope.

## Verification
- cd backend && GOOGLE_API_KEY=dummy python -m pytest tests/ -q  (full suite green)
- grep confirms no dangling imports of anything deleted
- PR as regisca-bot per the workflow at the top of the plan doc; PR description lists
  every deleted symbol/file
```

### Acceptance criteria

| # | Criterion |
|---|-----------|
| 2.1 | Full backend suite green |
| 2.2 | No remaining imports of deleted modules/symbols (grep-verified) |
| 2.3 | turn3_analysis/ removed from tracking; one-off scripts archived |
| 2.4 | CI on Node 20, both jobs green on the PR |

---

## WP-3: Fix HLK CC-gain mapping bug ✅ COMPLETE

**Branch**: `fix/hlk-cc-gain-mapping` · **Estimate**: < 1 hour · **Type**: small behavior fix + regression test

### As shipped (deviations from the starter prompt below)

Scope expanded to the full cluster of phantom/wrong card knowledge found in
`turn_plan_validator.py` (same bug class as HLK):

- Removed phantom `"HLK"` from both `CC_GAIN_ON_PLAY` tables + fixed the two
  direct-attack messages (the core task).
- Removed the dead `CC_GAIN_TRIGGERS` dict (defined, never referenced) and the
  unreachable "Red Solo Cup" branches (not a real card) — pure dead-code removal.
- **Behavior change (one)**: removed the reachable-but-wrong credit that gave
  Umbruh +1 CC on *tussle*. Umbruh gains CC when *sleeped*, not on tussle, so the
  validator was over-crediting CC and could accept overspent plans. Removing it is
  strictly more correct. Sleep-based CC gain is intentionally not modeled (it
  happens off the active turn). No test depended on the old credit; full suite green.
- Regression test `tests/test_cc_gain_tables.py` pins both tables to real cards with
  a play-triggered `gain_cc:` effect, keeps the two tables in sync, and asserts they
  cover every such card. Proven to fail if "HLK" (or any phantom) returns.

### Starter prompt

```
## Context
Audit-confirmed bug: the AI planner's CC-gain tables contain an entry for a card
that does not exist, modeling an effect the real card does not have.

Facts (verify each):
- backend/data/cards.csv has "Hind Leg Kicker" — a TOY (3/3/1) with effect
  on_card_played_gain_cc:1 (gain 1 CC when you play a SUBSEQUENT card while it is
  in play). There is no card named "HLK".
- backend/src/game_engine/ai/turn_planner.py:_CC_GAIN_ON_PLAY = {"Surge": 1, "Rush": 2, "HLK": 1}
- backend/src/game_engine/ai/validators/turn_plan_validator.py has a matching
  CC_GAIN_ON_PLAY entry for "HLK" and error messages calling HLK an "Action card"
  ("Action cards (Rush, Surge, HLK) do not enter play...").

The "HLK" entries never match (name mismatch) and are semantically wrong twice over
(wrong trigger, wrong card type).

## Task — minimal fix
1. Remove "HLK" from both CC_GAIN_ON_PLAY tables.
2. Fix the validator messages: "(Rush, Surge, HLK)" → "(Rush, Surge)".
3. Do NOT attempt to model Hind Leg Kicker's on_card_played trigger in the validator —
   that is deliberate scope-out (belongs to the future CSV-metadata centralization).
4. Add a regression test (backend/tests/) asserting that every key in both
   CC_GAIN_ON_PLAY tables is the exact name of a card in cards.csv whose effects
   contain a gain_cc effect. This pins the tables to the CSV until centralization.

## Verification
- New test fails on current main logic if "HLK" is re-added, passes after fix.
- Full suite green: cd backend && GOOGLE_API_KEY=dummy python -m pytest tests/ -q
- PR as regisca-bot per the workflow at the top of the plan doc.
```

### Acceptance criteria

| # | Criterion |
|---|-----------|
| 3.1 | No "HLK" string remains in src/ (grep) |
| 3.2 | Regression test ties CC-gain tables to cards.csv |
| 3.3 | Full suite green |

---

## WP-4: Deterministic sequence enumerator (EXPERIMENT — hands-on)

**Branch**: `feat/deterministic-enumerator` · **Estimate**: 2–3 sessions, phased · **Type**: new planner mode, experimental
**Dependencies**: WP-1..3 ✅ merged. Do this hands-on (lots of live AI testing).

### Context for a fresh session (read first — corrected June 2026)

- **Authoritative AI doc**: `docs/development/ai/AI_CURRENT_STATE.md`. Read it before
  touching the planner — the env-var story is genuinely confusing.
- **What prod actually runs**: **V4 / dual-request on Gemini** (`gemini-flash-lite-latest`),
  selected by **`AI_VERSION=4`**. NOT single. `AI_PLANNER_MODE` is a **no-op in the live
  path** (KNOWN_ISSUES Active Issue #1) — `get_ai_player()` derives the mode from
  `AI_VERSION` and bypasses `get_planner_mode()`. This directly affects integration
  (see Design → Integration below).
- **The path you are replacing** is V4's **Request 1** (LLM sequence generation), in
  `turn_planner.py::_create_plan_v4`. The current flow:
  `sequence_generator.generate_sequence_prompt` → LLM → `parse_sequences_response`
  → `TurnPlanValidator` (via `_sequence_to_temp_plan`) → `add_tactical_labels`
  → `strategic_selector.generate_strategic_prompt` → LLM (Request 2)
  → `parse_selector_response` → `convert_sequence_to_turn_plan`.
  The enumerator replaces **only the first LLM call**; Request 2 (selection) stays.
- **Environment**: repo-root `.venv` (Python 3.13, built with `uv`; install with
  `uv pip install`, not `python -m pip`). Run tests:
  `cd backend && GOOGLE_API_KEY=dummy ../.venv/bin/python -m pytest tests/ -q`
  (baseline: 382 passed, 39 skipped). The 39 skips are live-LLM tests needing a real
  `GOOGLE_API_KEY` — you'll want a real key for hands-on WP-4 testing.

### Hypothesis

Legal-sequence generation is a computation, not a judgment call. Replacing V4's
Request 1 with engine-side enumeration should: eliminate the illegal-action failure
class entirely (including the two documented V4 failure modes — mid-sequence
state-change reasoning and zone confusion), **cut Gemini usage from 2 calls/turn to 1**
(strategic selection only), and produce exact CC math by construction. The comparison
baseline is **dual/V4 (current prod)**, not single.

### Design sketch

- New module: `backend/src/game_engine/ai/enumerator.py`.
- Depth-limited DFS over the action space from the current state, using a **cloned,
  full-fidelity GameState** and real `GameEngine` transitions — so "tussle sleeps last
  toy → direct_attack becomes legal" falls out for free.
  - **Clone gotcha**: use `serialize_game_state` / `deserialize_game_state`
    (`api/serialization.py`) or `GameState.from_dict(gs.to_dict())` **without** a
    `requesting_player_id` — `to_dict(requesting_player_id=...)` *redacts the opponent's
    hand*, and the enumerator needs the complete state. Phase 4.0 must assert the clone
    is full-fidelity (opponent hand present, not hidden).
- **Output the structured sequence dict directly** — do NOT emit the LLM's lossy string
  format ("play X | CC: 3/4 | Sleeps: 1") that `parse_sequences_response` regex-parses.
  Match the dict shape that `add_tactical_labels` + `convert_sequence_to_turn_plan`
  consume: a list of `{action_type, card_id, card_name, target_ids, cc_cost}` actions
  plus `total_cc_spent` and `cards_slept`. Real `card_id`s and exact per-step CC are a
  strict improvement over the parsed-string path (no UUID-enrichment guesswork).
- Budget guards: CC budget prunes naturally; cap sequence length (~8 actions); cap
  Archer activations per sequence (≤ target's stamina); dedupe order-equivalent
  sequences (frozenset of action signatures); cap total returned (~12), ranked by a
  trivial score (cards slept desc, CC wasted asc) before selection.
- Direct attack's random hand-card choice: enumerate as a single action with
  expected-value annotation; do not branch on outcomes.
- **Integration (note the env-var reality)**: the new mode must be reachable from the
  *live* path, which keys off `AI_VERSION` — so `AI_PLANNER_MODE=enum` alone will NOT
  work. **Recommended: fold in the KNOWN_ISSUES #1 fix first** — make `AI_PLANNER_MODE`
  authoritative in `get_ai_player()` (so `single`/`dual`/`enum` all select correctly),
  then add `enum` as a third mode. This kills the footgun and gives a clean selector in
  one move. (Fallback if you want to avoid the migration: add an `AI_PLANNER` override
  consulted first by `get_ai_player()`.) Reuse `add_tactical_labels()` +
  `generate_strategic_prompt()` for selection — don't fork. Keep `TurnPlanValidator` in
  the loop initially as a **cross-check that should never fire**; log loudly if it does
  (that means the enumerator produced something the validator thinks is illegal — a bug
  in one of them).

### Phases

| Phase | Deliverable | Gate |
|-------|-------------|------|
| 4.0 | Full-fidelity state-clone utility + perf check | Unit test: clone round-trips opponent hand (not redacted); clone+apply a few actions ≤ a few ms |
| 4.1 | Enumerator + unit tests on standard scenarios (Turn 1 Surge+Knight hand MUST include the Surge→Knight→direct_attack line) | **Validator agreement: 0 enumerated sequences rejected** across test scenarios; enumeration time measured and bounded |
| 4.2 | `enum` mode wired through `get_ai_player()` + selector, with the `AI_PLANNER_MODE`-authoritative fix folded in | `tests/test_ai_standard_scenario.py` passes in enum mode with CC waste ≤ dual; KNOWN_ISSUES #1 resolved |
| 4.3 | Sim comparison: **enum vs dual** (prod), ≥40 games | Win rate ≥ dual; illegal actions = 0; **1 Gemini call/turn confirmed** (vs dual's 2) |

### Risks

- Combinatorial blowup with multi-target cards (Sun, Clean) and repeated activations —
  mitigated by caps above; measure enumeration time in Phase 4.1.
- Copy/Twist branching on targets multiplies sequences — cap targets considered per
  card to the top-N by simple score if needed.
- If `GameEngine` has hidden global state that survives cloning (module-level singletons,
  the effect registry mutating cards), Phase 4.0 surfaces it — fix there before proceeding.
- **Env-var coupling**: Phase 4.2 deliberately touches planner selection (the migration
  fix). Keep that change small and well-tested — it affects how *all* modes are selected,
  including prod's dual. Add a test asserting `AI_VERSION=4` still resolves to dual after
  the change (back-compat), so deployed prod behavior doesn't shift unexpectedly.

### Optional follow-up (not WP-4 scope, but natural next step)

Once sequences are enumerated deterministically, a **code-only scorer** (greedy or 2-ply
over the enumerated set) could replace Request 2 entirely → **0 LLM calls/turn**, giving
a free "easy AI" difficulty and a fixed benchmark to measure the LLM versions against.
This is audit recommendation #2 (heuristic baseline). Decide after 4.3.

---

## Deferred (tracked, not scheduled)

- **Centralize AI card metadata from CSV** (kills hardcoded names in 10 ai/ files) —
  shrinks dramatically if WP-4 succeeds, since most hardcoded knowledge exists to help
  the LLM do math it would no longer do. Decide after WP-4 Phase 4.3.
- **Split AdminDataViewer.tsx** (2,440 lines) — admin-only, works, lowest urgency.
- **Finish AI_VERSION → AI_PLANNER_MODE migration** — now **folded into WP-4 Phase 4.2**
  (the enumerator needs a clean mode selector). Tracked in detail as KNOWN_ISSUES
  Active Issue #1. If WP-4 is deferred, this is still worth doing standalone.
- **Sleeped-CC-gain owner vs controller**: the live data-driven `GainCCWhenSleepedEffect`
  (`continuous_effects.py`) grants CC to `get_card_owner`, not `get_card_controller`.
  Surfaced when removing the dead `UmbruhEffect` in WP-2 (Copilot review). It's a real
  rules question — if a stolen (Twisted) card is sleeped, does the thief or the original
  owner gain the CC? — but changing it is a behavior change, so it's out of scope for the
  sweep. Decide deliberately with a test before touching.
- **.gitignore AGENTS.md contradiction** ✅ resolved in WP-2: AGENTS.md dropped from the
  ignore list (the 3 tracked AGENTS.md files stay tracked); CLAUDE.md remains ignored.
