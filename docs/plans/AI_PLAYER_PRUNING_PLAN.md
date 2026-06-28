# AI Player Audit & Pruning Plan

> **Purpose:** prune the GGLTCG AI player down to the single architecture that
> actually runs in production (deterministic **enum** sequence generation +
> LLM **strategic selection** on Gemini), and remove every legacy mode, provider,
> prompt artifact, env var, admin-UI field, and doc that no longer reflects reality.
>
> **Status:** plan only — no code changed yet. Intended to be executed in VS Code
> with Claude Code (Sonnet).
>
> **Branch:** `claude/ai-player-audit-pruning-7hv4mo`

---

## 0. Locked-in decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Operating mode | **enum only.** Remove v2 (per-action), v3 (single-request), and dual/v4 (LLM sequence generation). |
| 2 | Provider | **Gemini only.** Remove the groq + openrouter (OpenAI-compatible) provider. Keep model-level fallback. |
| 3 | Primary model | `gemini-flash-lite-latest` |
| 4 | Fallback model | `gemini-2.5-flash-lite` (pinned, distinct from the `-latest` alias) |
| 5 | Example library | **Delete.** The static `card_examples`/`combo_examples`/`phase_examples` library is hardcoded to ~10 old cards and is collapsed to one-liners before it reaches the model. |
| 6 | Guidance rule | **If guidance is defined, send it in full.** No `_summarize_example`, no lossy "compact" passes. The dynamic board legend + `card_guidance.yaml` are the real, scalable context. |
| 7 | Threat priorities | `generate_threat_priorities` currently surfaces only CRITICAL/HIGH — **broaden** so MEDIUM threats are also surfaced (don't hide defined guidance). |
| 8 | Simulation harness | Align `backend/src/simulation/*` + its tests to the enum path; drop the `ai_version` 2/3/4 plumbing. |

### Guiding principle
The **only** runtime path after this work:

```
routes_actions.ai_turn
  → get_ai_player()                       # always the enum player, Gemini
  → LLMPlayer.select_action()             # (formerly LLMPlayerV3)
      → TurnPlanner.create_plan()         # enum branch only
          → enumerator.enumerate_sequences()        # deterministic, engine-legal
          → strategic_selector.generate_strategic_prompt()  # 1 Gemini call
          → convert_sequence_to_turn_plan()
      → _execute_planned_action()         # heuristic match, LLM only when ambiguous
```

Everything not on that path is luggage and should go.

---

## 1. Backend: collapse to the enum-only player

### 1a. `game_engine/ai/llm_player.py`
- The base `LLMPlayer` class currently holds **two** roles: (a) the dead V2
  per-action selector (`select_action`, `_call_json_api`, `get_ai_turn_prompt`,
  `SYSTEM_PROMPT`, `AI_DECISION_JSON_SCHEMA`), and (b) shared execution plumbing
  that the enum player still needs (`get_action_details`,
  `_filter_to_valid_targets`, `get_endpoint_name`, target/alt-cost bookkeeping).
- **Action:** collapse `LLMPlayer` + `LLMPlayerV3` into **one** class named
  `LLMPlayer`. Keep the execution plumbing; delete the V2 selector entirely.
  - Remove: V2 `select_action`, `_call_json_api`, the `get_ai_turn_prompt` import,
    `SYSTEM_PROMPT`/`AI_DECISION_JSON_SCHEMA` imports.
  - Keep + promote from `LLMPlayerV3`: `select_action` (planning), `_create_turn_plan`,
    `_execute_planned_action`, `_is_action_available`, `_call_execution_api`,
    `_advance_plan`, `record_execution_result`, `_handle_plan_failure`,
    `_maybe_replan`, `reset_plan`, `get_last_decision_info`.
  - The plan-exhausted fallback in `select_action` that calls
    `super().select_action(...)` (the V2 path) is now **dead** — the enumerator
    always returns at least the "pass" line, so a plan always exists. Replace that
    branch with a direct `end_turn` selection (find the `end_turn` action and
    return it). Confirm with a quick test that enum never returns `None`.
- **`get_ai_player()`**: drop `version` / `planner_mode` params, the
  `AI_VERSION` / `AI_PLANNER_MODE` reads, the `use_planner` branch, and the
  per-mode cache key. It becomes: build one cached `LLMPlayer` (Gemini, enum).
- **Remove:** `get_default_ai_version`, `get_ai_player_v3`, `LLMPlayerV3` alias.
- **`get_last_decision_info` keys:** rename for clarity (this is the
  backend→DB→frontend contract — change all three together, see §4):
  - `v3_plan` → `plan`
  - `ai_version` (int) → drop, or set a constant `planner: "enum"`
  - `v4_request1_*` → **drop** (enum has no LLM "request 1"; it's the deterministic enumerator)
  - `v4_request2_prompt` / `v4_request2_response` → `selection_prompt` / `selection_response`
  - `v4_request2_system_instruction` → `selection_system_instruction`
  - `v4_metrics` → `selection_metrics` (or drop if not surfaced)
  - `v4_turn_debug` → `enum_debug`

### 1b. `game_engine/ai/turn_planner.py`
- **`create_plan`:** delete the single-request body (the `format_*_for_planning_v3`
  block, the retry/validation-feedback loop, lines ~232–398) and the
  `planner_mode in ("dual", "enum")` branching. Keep only the enum flow.
- **`_create_plan_v4`:** rename to `create_plan` (or `_build_enum_plan`). Remove the
  `use_enumerator=False` (dual LLM) branch entirely — keep the
  `enumerate_sequences()` path + the strategic-selection request. Always
  `trust_action_costs=True` and skip `_reground_charge_chain` (enum costs are
  engine-exact).
- **Remove:** `get_planner_mode`, `ai_version_to_planner_mode`, `PLANNER_MODES`,
  the `_v4_metrics` class dict + `get_v4_metrics`/`reset_v4_metrics` (or slim to a
  small enum-only counter set), `_reground_charge_chain`,
  `_CHARGE_GAIN_ON_PLAY`/`_CANONICAL_ACTION_COSTS` (verify no other caller),
  groq-specific output-budget branches in `_get_*_output_budget` (Gemini only).
- **Rename** all `_v4_*` instance fields to match the new `get_last_decision_info`
  keys (`_selection_prompt`, `_selection_response`, `_enum_debug`, …).
- The `TurnPlanner.__init__` still needs `provider_client`, `model_name`,
  `fallback_model` — keep, but drop `ai_version` / `planner_mode` params.

### 1c. `routes_actions.py` (AI turn handler, ~line 485–620)
- Remove the `is_v3` / `filter_for_ai` toggle — enum always wants
  `filter_for_ai=True` (the enumerator already filters via
  `get_valid_actions(filter_for_ai=True)`; keep the live path consistent).
- Simplify the log-write block: drop the `v3_plan`/`ai_version=2-or-3` inference;
  read the renamed keys; `plan_execution_status` detection still works off the
  `[v3 Plan]`/`[v3 Fallback]` reasoning prefixes — **rename those prefixes** too
  (e.g. `[plan]` / `[fallback]`) and update the parser to match.

### 1d. Files that become fully dead → **delete** (verify each with grep first)
- `prompts/system_prompt.py` — `SYSTEM_PROMPT` + `ACTION_SELECTION_PROMPT` are V2-only.
  ⚠️ Confirm `narrative.py` / `get_llm_response` don't import it.
- `prompts/planning_prompt.py` — `format_break_zone_for_planning` only used by the
  single path.
- `prompts/planning_prompt_v3.py` — `get_planning_prompt_v3`,
  `format_hand/in_play/break_zone_for_planning_v3` only used by the single path.

### 1e. Files that need **partial** pruning
- `prompts/sequence_generator.py` (657 lines): the enum path only uses
  `add_tactical_labels` + `format_sequence_for_display`. Everything else
  (`generate_sequence_prompt`, `SEQUENCE_GENERATOR_SCHEMA`,
  `get_sequence_generator_temperature`, `parse_sequences_response`) is dual-only.
  **Action:** move the 2 surviving functions into `strategic_selector.py` (or a small
  `sequence_format.py`) and delete `sequence_generator.py`.
- `prompts/formatters.py`: keep `format_valid_actions_for_ai` (used by execution).
  Delete `get_ai_turn_prompt` (V2) and `format_game_state_for_ai` (single path only —
  verify). Drop the `ACTION_SELECTION_PROMPT` import.
- `prompts/schemas.py`: keep `TurnPlan` + `PlannedAction` pydantic models. Delete
  `AIDecision` + `AI_DECISION_JSON_SCHEMA` (V2) and `TURN_PLAN_JSON_SCHEMA`
  (single path only — verify nothing else references it).
- `prompts/execution_prompt.py`: keep `get_execution_prompt`,
  `find_matching_action_index`, `EXECUTION_JSON_SCHEMA`. Verify `get_replan_prompt`
  and `extract_target_from_action` are unused → delete if so.
- `prompts/__init__.py`: update re-exports to match all deletions above.

### 1f. Verify-then-decide (couldn't confirm in research)
- `prompts/effect_loader.py`, `prompts/effect_metadata.py` — grep for usage; keep
  only if the live enum/guidance path imports them.
- `quality_metrics.py` (`TurnMetrics`, `record_turn_metrics`) — used by turn_planner;
  keep, but trim any v3/v4-labeled fields.
- `validators/turn_plan_validator.py` — still used by enum as an **advisory**
  cross-check; keep. Trim comments that describe the dual path.

---

## 2. Provider simplification → Gemini only

### `game_engine/ai/providers.py`
- Delete `OpenAICompatibleProvider` (groq/openrouter), `_BASE_URLS`, the
  `SUPPORTED_PROVIDERS` tuple's non-gemini entries, and groq/openrouter default
  models/key-env mappings.
- `resolve_provider_config`: collapse to Gemini. Resolve key from
  `GOOGLE_API_KEY`; model from `GEMINI_MODEL` (default `gemini-flash-lite-latest`);
  fallback from `GEMINI_FALLBACK_MODEL` (default `gemini-2.5-flash-lite`). Drop the
  generic `AI_PROVIDER` / `AI_API_KEY` / `AI_MODEL` / `AI_FALLBACK_MODEL` /
  `AI_BASE_URL` reads.
- `build_provider` / `get_default_provider_name` / `get_default_model` /
  `get_api_key_env_var`: simplify or remove; callers in `turn_planner.py` and
  `llm_player.py` should construct the Gemini provider directly.
- Keep the Gemini retry + **model fallback** logic (`_is_retryable`,
  `_is_location_precondition`, the `allow_fallback` recursion) — this is the
  fallback the user explicitly wants kept.
- Update `get_display_name` map: keep `gemini-flash-lite-latest` and
  `gemini-2.5-flash-lite`; prune entries for models no longer used (optional).

---

## 3. Prompt context: delete fake examples, send real guidance in full

### 3a. Delete the static example library
- Delete the whole `prompts/examples/` directory: `loader.py`,
  `card_examples.py`, `combo_examples.py`, `phase_examples.py`, `__init__.py`.
- `strategic_selector.py`: remove the `from .examples.loader import …` import, the
  `examples = get_relevant_examples(...)` / `format_examples_for_prompt(...)` calls,
  and the `<examples>` block from `generate_strategic_prompt`. Keep
  `get_game_phase` logic by inlining the 3-line turn→phase mapping (it's used for
  the `<context>` line) — or drop the phase tag if not valuable.

### 3b. Send card guidance in full (no summarizing)
- `_summarize_example` is being deleted with the examples dir — good, that's the
  main offender.
- `card_loader.format_card_guidance_compact` → `get_relevant_card_guidance`:
  confirm it already emits the **full** trap/reminder/threat per relevant card
  (it does, today) and keep it sent verbatim in the selector prompt. Rename
  `format_card_guidance_compact` → `format_card_guidance` to stop implying it trims.
- **Broaden `generate_threat_priorities`** (decision #7): include MEDIUM threats,
  not just CRITICAL/HIGH. Note this function is currently only wired into the dead
  v3 single prompt — **wire the broadened version into the live enum selector
  prompt** (`generate_strategic_prompt`) so the threat ranking actually reaches the
  model, or fold its content into the board legend. Don't leave defined guidance
  unused.

### 3c. Sanity pass on the selector prompt
- After removing examples, re-read `generate_strategic_prompt` end-to-end and
  confirm the model still has enough to pick a non-zero sequence: board legend
  (full stats + effect text), full card guidance, threat priorities, and the
  per-sequence breakdown (charge/breaks/targets). This is the substance that lets
  it choose something other than sequence 0 — verify it's all present and full.

---

## 4. Admin UI / AI logs cleanup

The contract is: `llm_player.get_last_decision_info()` → `stats_service.log_ai_decision`
→ `AIDecisionLogModel` → `routes_admin` ai-logs endpoints → `AdminDataViewer.tsx`.
Rename consistently across **all** of these in one pass.

### 4a. Backend
- `db_models.py::AIDecisionLogModel`: the `ai_version` Integer column —
  **keep the column** (avoid a destructive prod migration) but stop writing version
  ints; write a constant or leave null and rely on the `turn_plan` JSON's
  `planner: "enum"`. Update the class docstring (it still says "2 or 3"). If a
  clean schema is wanted, add a follow-up alembic migration to drop
  `ai_version`/rename to `planner_mode` — **separate, optional step**, not blocking.
- `routes_admin.py` (`/ai-logs`, `/ai-logs/{id}`): the response dict keys mirror the
  columns; keep them but the embedded `turn_plan` JSON now carries the renamed keys
  from §1a. No endpoint signature change needed.
- `stats_service.log_ai_decision`: simplify signature — drop/repurpose the
  `ai_version` param.

### 4b. Frontend `frontend/src/components/AdminDataViewer.tsx`
- The `AILog['turn_plan']` type + the render code reference:
  `v4_request1_prompt/response`, `v4_request2_prompt/response`, `v4_metrics`,
  `v4_turn_debug`, `planner_mode`, `ai_version`.
- **Remove** all "Request 1 (sequence generation)" UI — enum has no LLM request 1.
  That includes the `isR1PromptSameAsPlanning` dedupe logic and the
  `v4_request1_*` view toggles (~lines 1268–1288, 685–691, 572–597).
- **Rename** "Request 2 (strategic selection)" → "Strategic selection
  (prompt/response)" using the new `selection_*` keys.
- `v4_turn_debug` → `enum_debug`; drop the dual-only debug fields shown
  (`request1_attempts`, `request1_temps_tried`, `sequences_rejected`/rejection
  messages for the LLM path). Keep enum-relevant ones (`sequences_generated`,
  `sequences_after_validation`, `request2_selected_index`/`_used`).
- `groupLogsByTurn` keys on `ai_version >= 3` — simplify to always-grouped (enum is
  always a planner). Replace the `ai_version` chip with a static `enum` label or
  drop it.
- `frontend/src/utils/plannerMode.ts`: simplify `plannerModeLabel` to return
  `'enum'` (or remove and inline) since there's no longer a mode to disambiguate.
  Check `VictoryScreen.tsx` + `statsService.ts` for the same `ai_version`/planner
  references and update.

### 4c. Quick label audit
Walk the AI Logs tab top-to-bottom in the running app and rename any remaining
"v2/v3/v4/dual/single" user-facing strings to the enum vocabulary.

---

## 5. Simulation harness alignment

`backend/src/simulation/*` (`runner.py`, `config.py`, `orchestrator.py`,
`reporter.py`, `cli.py`) carries `player{1,2}_ai_version` (2/3/4) and
`SUPPORTED_AI_VERSIONS = [2, 3, 4]`.
- Replace the version knobs with the single enum player (construct `LLMPlayer`
  directly, Gemini). Remove `ai_version_to_planner_mode` usage and the
  `if version == 4` branches.
- `config.py`: drop `SUPPORTED_AI_VERSIONS`, `player*_ai_version`,
  `v2_fallback_count` and other dual/v4 metrics fields that no longer occur.
- `reporter.py`: stop printing `AI v{version}`.
- Update `simulation/README.md` accordingly.
- This is dev-only tooling — lowest blast radius; do it after the live path is green.

---

## 6. Environment variables

> **Sequencing:** land the code that hardcodes enum + Gemini **first** (makes the
> old vars no-ops), deploy, then remove the vars from Render/Vercel manually. Safe
> in that order because nothing reads them anymore.

### 6a. Repo files
- `backend/.env.example`: rewrite the AI section. Keep only:
  ```
  # ===== AI Player (Gemini) =====
  GOOGLE_API_KEY=your-google-api-key-here
  # Primary model (floating alias to latest Flash Lite)
  GEMINI_MODEL=gemini-flash-lite-latest
  # Distinct pinned fallback for rate-limit / availability blips
  GEMINI_FALLBACK_MODEL=gemini-2.5-flash-lite
  ```
  Delete: `AI_PROVIDER`, `AI_MODEL`, `AI_FALLBACK_MODEL`, `AI_PLANNER_MODE`,
  `AI_VERSION`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, and the stale model comments
  (the file currently says default is `gemini-3.1-flash-lite-preview` — wrong).
- `backend/.env.production`: set `GEMINI_MODEL=gemini-flash-lite-latest` and
  `GEMINI_FALLBACK_MODEL=gemini-2.5-flash-lite` (currently pins `gemini-2.5-flash`
  / `gemini-2.5-flash-lite`). Note in a comment that `AI_PLANNER_MODE` is no longer
  read (enum is hardcoded).
- Local `.env`: mirror the same (user does this; list it in the PR/notes).

### 6b. Manual cleanup (user does after deploy) — list these explicitly in the PR body
- **Render** (backend): remove `AI_PLANNER_MODE`, `AI_VERSION`, `AI_PROVIDER`,
  `AI_MODEL`, `AI_FALLBACK_MODEL`, `AI_BASE_URL`, `AI_API_KEY`, `GROQ_API_KEY`,
  `OPENROUTER_API_KEY`, `OPENROUTER_SITE_URL`, `OPENROUTER_APP_NAME`. Set
  `GEMINI_MODEL=gemini-flash-lite-latest`, `GEMINI_FALLBACK_MODEL=gemini-2.5-flash-lite`.
  Keep `GOOGLE_API_KEY`.
- **Vercel** (frontend): grep the frontend for `import.meta.env.VITE_*` AI-related
  vars first (likely none — the frontend only reads logs via the API). Remove any
  that turn up unused.

---

## 7. Tests

Run `cd backend && pytest` after each phase. Expected fallout:
- **Remove/replace** (V2/V3/dual/provider-specific): `test_llm_player_v3.py`,
  `test_planner_mode_selection.py`, `test_ai_providers.py`, `test_ai_v4_components.py`,
  `test_ai_v4_decision_logging.py`, `test_ai_prompts_v4.py`,
  `test_charge_plan_grounding.py` (regrounding is being deleted),
  `test_strategic_selector_prompt.py` (update for removed `<examples>` block).
- **Keep/adapt** (enum path): `test_enum_planner_integration.py`,
  `test_ai_enum_scenario.py`, `test_ai_standard_scenario.py`, `test_ai_multi_target.py`,
  `test_card_id_disambiguation.py`, `test_stats_service.py`, `ai_test_support.py`,
  `test_cc_gain_tables.py` (still pins Surge/Rush/Cake gains used by enumerator).
- Add a small regression test: enum `select_action` never returns `None` (always at
  least `end_turn`) now that the V2 fallback is gone.

---

## 8. Docs

- Rewrite `docs/development/ai/AI_CURRENT_STATE.md` to describe the enum-only,
  Gemini-only architecture.
- Update `AGENTS.md`, `backend/AGENTS.md`, `backend/AI_SETUP.md`, `README.md`:
  remove v2/v3/v4/dual/provider references; state enum + Gemini + the two model env vars.
- `docs/development/KNOWN_ISSUES.md`: clear resolved dual/single-mode issues.
- Archive (move to `docs/development/ai/archive/`, don't rewrite): the V3/V4 design
  + remediation notes (`AI_V4_DESIGN.md`, `AI_V4_REMEDIATION_PLAN.md`,
  `AI_V3_*` dev-notes, etc.).

---

## 9. Suggested execution order (each step independently testable)

1. **Providers → Gemini only** (§2) + env files (§6a). Run tests.
2. **Collapse player to enum-only** (§1a–1c) + delete fully-dead prompt files (§1d)
   + partial prunes (§1e). Run tests.
3. **Prompt context** (§3): delete examples, broaden threat priorities, verify
   selector prompt richness. Run + eyeball a live AI turn.
4. **Admin UI rename** (§4) — backend keys + frontend together. Verify AI Logs tab.
5. **Simulation** (§5). Run a short sim.
6. **Docs** (§8).
7. Full `pytest` + a manual game vs AI + admin-log review.
8. Open PR; in the body list the **Render/Vercel env vars to remove manually**
   (§6b). Deploy code, then remove the vars.

---

## 10. Risks / watch-outs

- **The contract rename (§1a/§4) must be atomic** across backend keys, DB JSON,
  and the frontend type+render, or AI Logs silently render blank. Old rows in the
  DB will still have `v4_request2_*` keys — either keep the frontend tolerant of
  both for a release, or accept that historical logs lose some detail.
- **Don't migrate the `ai_version` column destructively** on a whim — production
  data lives there. Prefer keeping the column inert; do a migration only as a
  deliberate, separate step.
- **Verify each "delete" with a grep** before removing — a few helpers
  (`format_game_state_for_ai`, `effect_loader`, `get_replan_prompt`) were marked
  "verify" because their only callers appeared to be on dead paths but weren't
  100% confirmed during planning.
- **Deploy-then-remove-env-vars ordering** (§6) matters: removing
  `AI_PLANNER_MODE` from Render before the enum hardcode ships would flip prod
  back to `single` mode.
