# AI Current State

**Last Updated**: June 15, 2026

This is the single source of truth for the GGLTCG AI subsystem. It supersedes
the historical V4 design/baseline/remediation docs in this folder and in
`docs/plans/`. Read this first; treat the V4 docs as background.

The AI opponent plays a whole turn by asking an LLM for a plan, then executing
that plan step by step on the server with deterministic matching and graceful
fallbacks.

---

## Architecture: Planner Modes

There are two planner modes, **single** and **dual** (a.k.a. "V4").

> **Production runs `dual` (V4) on Gemini.** Prod sets `AI_VERSION=4`, which
> selects dual-request planning. "single" is the bare-checkout default, **not**
> what the deployed game uses.

### What actually selects the mode (read this — it is genuinely confusing)

The live request path (`routes_actions.py` → `get_ai_player()`) derives the mode
**from `AI_VERSION`**, not from `AI_PLANNER_MODE`:

- `AI_VERSION=4` → **dual**; any other value (or unset → default `3`) → **single**.
- `get_ai_player()` computes the mode from `AI_VERSION` and passes it *explicitly*
  into the planner, so `get_planner_mode()` — the only function that reads
  `AI_PLANNER_MODE` — is **never reached in the running application**.
- **So `AI_PLANNER_MODE` has no effect in the deployed app.** It is vestigial from
  an incomplete `AI_VERSION → AI_PLANNER_MODE` migration: setting it alone changes
  nothing; `AI_VERSION` is the real switch. (Tracked in
  [KNOWN_ISSUES.md](../KNOWN_ISSUES.md).)

| You set… | Live app behavior |
|----------|-------------------|
| `AI_VERSION=4` | **dual / V4** (this is prod) |
| `AI_VERSION=3` or unset | single |
| `AI_PLANNER_MODE=…` (alone) | **ignored** — no effect in the running app |

### single (code default — not what prod runs)

- **One LLM request** plans the entire turn (sequence of actions ending in
  `end_turn`).
- Optimized for **Groq token budgets** — the prompt is kept compact.
- After the response, the server applies:
  - **Plan pruning** — invalid/illegal steps are dropped rather than retried
    (a plan like `[play Rush (T1), direct_attack, end_turn]` is pruned down to
    something legal, at worst `[end_turn]`, so it never wastes CC or cheats the
    mid-turn replan logic).
  - **CC regrounding** (`_reground_cc_chain`) — recomputes CC along the plan so
    later steps see the correct CC after earlier ones.
- No second LLM call, no example injection.

### dual / V4 (what production runs)

Two LLM requests with a server-side validator between them:

1. **Sequence generation** (`prompts/sequence_generator.py`) — generate several
   candidate action sequences.
2. **`TurnPlanValidator`** (`validators/turn_plan_validator.py`) — server-side,
   discards illegal sequences. If none are valid, it retries generation at a
   higher temperature, then falls back to V2 single-action mode.
3. **Strategic selection** (`prompts/strategic_selector.py`) — pick the best of
   the valid sequences.

Dual mode uses the few-shot examples under `prompts/examples/`. It costs roughly
double the API calls of single mode; production accepts that for the higher plan
quality from validated sequence selection. Single mode exists as the lighter
fallback and the bare-checkout default.

---

## Execution Layer

The plan is executed action-by-action in `llm_player.py`. For each planned step:

1. **Heuristic plan-step matching** — match the planned action to an available
   valid action with no LLM call. This is the common path.
2. **LLM fallback matcher** — if the heuristic fails *and* the action type is
   actually available, a small LLM call resolves the match.
3. **Mid-turn replan** — if execution drifts from the plan, the planner may
   replan mid-turn. This is **capped at 2 replans per turn**
   (`_midturn_replan_count >= 2`) to avoid loops.
4. **V2 single-action fallback** — if there is no usable plan (or dual mode
   produced no valid sequences), fall back to V2, which picks a single safe
   action.
5. **Forced `end_turn` floor** — if everything above is exhausted, the AI ends
   its turn. `end_turn` is always available, so the AI can never get stuck.

---

## Providers

> **In practice the game always runs on Gemini.** Production is
> `AI_PROVIDER=gemini`, `GEMINI_MODEL=gemini-flash-lite-latest`, fallback
> `gemini-2.5-flash-lite`. The Groq/OpenRouter abstraction works *mechanically*,
> but the prompts are tuned for Gemini — pointing the game at another provider
> runs without errors yet degrades gameplay, because each model needs its prompts
> re-optimized. Treat non-Gemini providers as experiments, not a drop-in swap.

Provider abstraction lives in `backend/src/game_engine/ai/providers.py`.
Selected via `AI_PROVIDER`; the model via `AI_MODEL` (or provider-specific
overrides). Supported providers and their default models:

| Provider | `AI_PROVIDER` | Default model |
|----------|---------------|---------------|
| Google Gemini (default) | `gemini` | `gemini-flash-lite-latest` |
| Groq | `groq` | `llama-3.3-70b-versatile` |
| OpenRouter | `openrouter` | `openai/gpt-oss-20b` |

All providers use native/structured JSON output for reliable parsing.

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `AI_VERSION` | **The real planner-mode switch in the live app.** `4` → dual/V4 (prod); `3` or unset → single. |
| `AI_PLANNER_MODE` | **No effect in the running app** — vestigial; the live path reads `AI_VERSION` instead (see Planner Modes). |
| `AI_PROVIDER` | Provider to use: `gemini` (default and what prod uses), `groq`, `openrouter`. |
| `AI_MODEL` | Generic model override for the selected provider. Ignored for Gemini (use `GEMINI_MODEL`). |
| `AI_FALLBACK_MODEL` | Generic fallback model when the primary hits capacity. |
| `GEMINI_MODEL` | Gemini model (prod: `gemini-flash-lite-latest`). Takes precedence over `AI_MODEL` for Gemini. |
| `GEMINI_FALLBACK_MODEL` | Gemini fallback model (prod: `gemini-2.5-flash-lite`). |
| `GOOGLE_API_KEY` | Gemini API key (required when provider is `gemini`). |
| `GROQ_API_KEY` | Groq API key (required when provider is `groq`). |
| `OPENROUTER_API_KEY` | OpenRouter API key (required when provider is `openrouter`). |

> **Two env vars, one switch.** `AI_VERSION` and `AI_PLANNER_MODE` both look like
> they select the planner mode, but only `AI_VERSION` does in the running app.
> This is an unfinished migration — until it's resolved, set `AI_VERSION`.

See `backend/.env.example` for the canonical commented list.

---

## Version History

| Version | When | What changed |
|---------|------|--------------|
| V1 | Nov 2025 | Per-action prompting — the LLM chose one action at a time. |
| V2 | Dec 2025 | Structured JSON output and card IDs (not names). |
| V3 | Dec 2025 | Single-request whole-turn planning. Prompts grew to 12–13k chars; illegal actions persisted. |
| V4 | Jan 2026 | Dual-request: sequence generation → server-side `TurnPlanValidator` → strategic selection. Balanced 160-game baseline. |
| Provider era | May–Jun 2026 | Provider abstraction (Groq/OpenRouter) added; `AI_PLANNER_MODE` introduced but left vestigial (the live path still reads `AI_VERSION`). Prod stays on **Gemini + V4/dual**. |

---

## How to Evaluate Changes

- **Quality metrics** (`quality_metrics.py`) — the primary signal is **CC waste**
  per turn (advanced play wastes <1 CC/turn; 4+ is "wasteful"). Watch this when
  changing prompts or planner logic.
- **Standard scenario test** — `backend/tests/test_ai_standard_scenario.py`
  exercises the AI against a fixed game state and is the fastest regression check
  that does not burn LLM credits unpredictably.
- **Simulation CLI** — `backend/src/simulation/` runs AI-vs-AI batches for
  win-rate and balance analysis (see
  [SIMULATION_SYSTEM.md](../SIMULATION_SYSTEM.md)). **Currently dormant** due to
  LLM-credit constraints; use it deliberately, not as a routine gate.

---

## Known AI Issues

See [KNOWN_ISSUES.md](../KNOWN_ISSUES.md) for active items, notably the `HLK`
CC-gain mapping bug and the pending centralization of AI card metadata (card
names are still hardcoded across several `ai/` files).
