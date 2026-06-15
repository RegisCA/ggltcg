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

The planner mode is selected by the `AI_PLANNER_MODE` environment variable and
resolved in `backend/src/game_engine/ai/turn_planner.py` (`get_planner_mode()`).

### single (DEFAULT)

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

### dual (EXPERIMENTAL — "V4")

Two LLM requests with a server-side validator between them:

1. **Sequence generation** (`prompts/sequence_generator.py`) — generate several
   candidate action sequences.
2. **`TurnPlanValidator`** (`validators/turn_plan_validator.py`) — server-side,
   discards illegal sequences. If none are valid, it retries generation at a
   higher temperature, then falls back to V2 single-action mode.
3. **Strategic selection** (`prompts/strategic_selector.py`) — pick the best of
   the valid sequences.

Dual mode uses the few-shot examples under `prompts/examples/`. It costs roughly
double the API calls of single mode, which is why single is the default.

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
| `AI_PROVIDER` | Provider to use: `gemini` (default), `groq`, `openrouter`. |
| `AI_MODEL` | Generic model override for the selected provider. |
| `AI_FALLBACK_MODEL` | Generic fallback model when the primary hits capacity. |
| `AI_PLANNER_MODE` | `single` (default) or `dual` (experimental). |
| `GEMINI_MODEL` | Gemini-specific model override (takes precedence over `AI_MODEL` for Gemini). |
| `GEMINI_FALLBACK_MODEL` | Gemini-specific fallback model. |
| `GOOGLE_API_KEY` | Gemini API key (required when provider is `gemini`). |
| `GROQ_API_KEY` | Groq API key (required when provider is `groq`). |
| `OPENROUTER_API_KEY` | OpenRouter API key (required when provider is `openrouter`). |

> Legacy note: `AI_VERSION=4` is still honored and maps to `dual`; any other
> value maps to `single`.

See `backend/.env.example` for the canonical commented list.

---

## Version History

| Version | When | What changed |
|---------|------|--------------|
| V1 | Nov 2025 | Per-action prompting — the LLM chose one action at a time. |
| V2 | Dec 2025 | Structured JSON output and card IDs (not names). |
| V3 | Dec 2025 | Single-request whole-turn planning. Prompts grew to 12–13k chars; illegal actions persisted. |
| V4 | Jan 2026 | Dual-request: sequence generation → server-side `TurnPlanValidator` → strategic selection. Balanced 160-game baseline. |
| Provider era | May–Jun 2026 | `AI_PLANNER_MODE` (`single`/`dual`); Groq and OpenRouter providers added; **single-request planning became the default**. |

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
