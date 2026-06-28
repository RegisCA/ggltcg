# AI Current State

**Last Updated**: June 28, 2026

This is the single source of truth for the GGLTCG AI subsystem. It supersedes
the historical V2/V3/V4 design/baseline/remediation docs, which have been
archived under `docs/development/ai/archive/`. Read this first.

The AI opponent plays a whole turn by deterministically enumerating every
engine-legal action sequence, asking Gemini to pick the best one, then
executing that sequence step by step on the server with deterministic matching
and graceful fallbacks.

---

## Architecture: enum + strategic selection

There is a single planner architecture — no provider switch, no planner-mode
switch. The runtime path is:

```text
routes_actions.ai_turn
  → get_ai_player()                       # cached singleton, Gemini
  → LLMPlayer.select_action()
      → TurnPlanner.create_plan()
          → enumerator.enumerate_sequences()        # deterministic, engine-legal
          → strategic_selector.generate_strategic_prompt()  # 1 Gemini call
          → convert_sequence_to_turn_plan()
      → _execute_planned_action()         # heuristic match, LLM only when ambiguous
```

1. **Sequence enumeration** (`enumerator.py::enumerate_sequences`) — a
   depth-limited DFS over the real action space on cloned game states, using
   the same `ActionValidator` / `ActionExecutor` the live game trusts.
   Produces only engine-legal sequences with exact CC by construction. No LLM
   call.
2. **`TurnPlanValidator`** (`validators/turn_plan_validator.py`) — advisory
   only. The enumerator's sequences are engine-legal by construction, but the
   validator is a weaker heuristic with incomplete hardcoded card knowledge
   (e.g. it assumes tussle/direct always cost 2 — wrong for Raggy's 0-cost
   tussles — and doesn't model Jumpscare returning a toy to hand), so it can
   false-reject valid lines. We keep every enumerated sequence and only log
   disagreements (a signal of validator blind spots, or a genuine enumerator
   bug) rather than filtering on them.
3. **Strategic selection** (`prompts/strategic_selector.py`) — a single Gemini
   call picks the best enumerated sequence, given the board legend, full card
   guidance, and threat priorities (CRITICAL/HIGH/MEDIUM).

Result: the illegal-action failure class is eliminated by construction, and
the AI costs exactly **1 Gemini call per turn** (selection only) plus, rarely,
a small execution-matcher call when a heuristic step match is ambiguous.

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
4. **Forced `end_turn` floor** — the enumerator always includes at least the
   "pass" sequence, so a plan always exists; if every step above is exhausted,
   `select_action` falls straight through to `end_turn`. The AI can never get
   stuck with no action to take.

---

## Provider

**Gemini only.** There is no provider abstraction or `AI_PROVIDER` switch —
`game_engine/ai/providers.py` builds a `GeminiProvider` directly, with
model-level retry/fallback kept (`_is_retryable`, `_is_location_precondition`,
the `allow_fallback` recursion) for capacity (429) errors.

| Role | Env var | Default |
| --- | --- | --- |
| Primary model | `GEMINI_MODEL` | `gemini-flash-lite-latest` |
| Fallback model | `GEMINI_FALLBACK_MODEL` | `gemini-2.5-flash-lite` (pinned, distinct from the `-latest` alias) |
| API key | `GOOGLE_API_KEY` | — (required) |

See `backend/.env.example` for the canonical commented list.

---

## Version History

| Version | When | What changed |
| --- | --- | --- |
| V1 | Nov 2025 | Per-action prompting — the LLM chose one action at a time. |
| V2 | Dec 2025 | Structured JSON output and card IDs (not names). |
| V3 | Dec 2025 | Single-request whole-turn planning. Prompts grew to 12–13k chars; illegal actions persisted. |
| V4 / dual | Jan 2026 | Dual-request: LLM sequence generation → server-side `TurnPlanValidator` → strategic selection. Ran in production for several months. |
| Provider era | May–Jun 2026 | Groq/OpenRouter provider abstraction added as an experiment; prod stayed on Gemini. |
| enum (WP-4) | Jun 2026 | Deterministic enumerator replaces dual's Request 1 LLM call with engine-side sequence enumeration. Promoted to prod. |
| **Pruning** (this doc) | Jun 28, 2026 | Collapsed to enum + Gemini only. Removed V2/V3/dual code paths, the Groq/OpenRouter providers, the static prompt-examples library, and all related env vars/admin-UI fields. This is now the only architecture. |

---

## How to Evaluate Changes

- **Quality metrics** (`quality_metrics.py`) — the primary signal is **CC waste**
  per turn (advanced play wastes <1 CC/turn; 4+ is "wasteful"). Watch this when
  changing prompts or planner logic.
- **`test_ai_enum_scenario.py`** exercises the AI against fixed game states and
  is the fastest regression check that does not burn LLM credits
  unpredictably.
- **Simulation CLI** — `backend/src/simulation/` runs AI-vs-AI batches for
  win-rate and balance analysis (see
  [SIMULATION_SYSTEM.md](../SIMULATION_SYSTEM.md)). **Currently dormant** due
  to LLM-credit constraints; use it deliberately, not as a routine gate.

---

## Known AI Issues

See [KNOWN_ISSUES.md](../KNOWN_ISSUES.md) for active items, notably the
pending centralization of AI card metadata (card names are still hardcoded
across several `ai/` files).
