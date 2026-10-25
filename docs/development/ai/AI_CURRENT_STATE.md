# AI Current State

**Last updated**: October 25, 2026

This is the single source of truth for the GGLTCG AI opponent. Historical
design notes for the V2, V3 and V4 architectures are archived under
[`archive/`](archive/) and describe code that no longer exists.

The AI plays a whole turn in three steps:

1. The engine **enumerates** every legal action sequence for the turn,
   deterministically, and ranks them.
2. **One Gemini call** picks the best of the top 12.
3. The server **executes** the chosen sequence one action at a time, with
   deterministic matching and fallbacks.

Because the model only ever chooses among engine-legal sequences, it cannot
make an illegal move. That failure class, which dominated the V3 and V4
architectures, is gone by construction.

---

## Runtime path

```text
POST /games/{id}/ai-turn                     routes_actions.ai_take_turn
  → get_ai_player()                          cached LLMPlayer singleton
  → LLMPlayer.select_action()
      → TurnPlanner.create_plan()            once per turn
          → enumerate_sequences()            deterministic, engine-legal
          → add_tactical_labels()            [Lethal], [Board Setup], ...
          → _select_sequence()               the only LLM call
          → convert_sequence_to_turn_plan()
      → _execute_planned_action()            once per action
```

The endpoint executes **one action per request**. The frontend calls it
repeatedly until the AI ends its turn, which is what lets the board animate
the AI's moves one at a time.

### 1. Enumeration (`game_engine/ai/enumerator.py`)

A depth-limited search over the real action space. Each node is a cloned
`GameState`, and each edge is applied through the same `ActionValidator` and
`ActionExecutor` that the human endpoints use. Every sequence it returns is
legal and carries exact Charge costs, including discounted tussles (Raggy's
free tussles, Wizard's 1-Charge tussles) and target-dependent costs.

Search bounds:

| Constant | Value | Purpose |
| --- | --- | --- |
| `DEFAULT_MAX_ACTIONS` | 8 | Longest sequence considered |
| `DEFAULT_MAX_SEQUENCES` | 12 | Sequences passed to the selector |
| `DEFAULT_MAX_TARGET_OPTIONS` | 5 | Targets considered per targeted action |
| `DEFAULT_MAX_TARGET_COMBOS` | 8 | Combinations considered per multi-target action |
| `MAX_NODES` | 4000 | Hard stop on states expanded |

Sequences are ranked by `_rank_key`: winning lines first, then most opponent
cards broken, fewest own cards broken, least Charge wasted, and shortest. The
"pass" line is always included, so a plan always exists.

The 8-action cap is a deliberate trade-off. Simulation showed it binds for
Charge-refund combo turns, which a human can chain to 10+ actions. Raising it
makes the AI stronger but slower on Render's free tier, so it stays at 8 for
live play. The simulation harness can raise it per run (see
[SIMULATION_SYSTEM.md](../SIMULATION_SYSTEM.md#findings)).

### 2. Strategic selection (`game_engine/ai/prompts/strategic_selector.py`)

A single Gemini call with structured JSON output returns
`{selected_index, reasoning}`. The prompt is built from tagged blocks:
`<goal>`, `<context>`, `<board_legend>`, `<threat_priorities>`,
`<card_guidance>`, `<valid_sequences>` and `<task>`. Temperature is 0.4.

`<card_guidance>` comes from
[`card_guidance.yaml`](../../../backend/src/game_engine/ai/prompts/card_guidance.yaml):
short per-card notes on common traps (for example, "Archer has 0 strength and
cannot tussle"). It is the only place card-specific strategy lives. Facts
derived from card data, such as which cards gain Charge when played, are
computed from `cards.csv` at import time in `card_metadata.py` rather than
hardcoded.

If the call fails or returns an out-of-range index, the planner falls back to
the top-ranked sequence. The one exception is `BudgetExhaustedError` (the
simulation daily budget), which always propagates so the run can pause cleanly.

`TurnPlanner._select_sequence` is the only non-deterministic step in the
pipeline, and it is designed as an override point. The simulation harness
subclasses it to replace the Gemini call with a local policy, which is how
LLM-free simulation works (see
[SIMULATION_SYSTEM.md](../SIMULATION_SYSTEM.md)).

### 3. Execution (`game_engine/ai/llm_player.py`)

For each planned step:

1. **Heuristic match.** Match the planned action to one of the currently valid
   actions, with no LLM call. This is the normal path.
2. **LLM matcher.** If the heuristic fails but the action type is available, a
   small execution prompt resolves the match.
3. **Mid-turn replan.** If the board has drifted from the plan (for example,
   the planned tussle target is already broken), the planner replans. This is
   capped at 2 replans per turn.
4. **End turn.** If all of the above fail, the AI ends its turn. It can never
   get stuck.

Target IDs returned by the model are filtered against the action's
`target_options` (`_filter_to_valid_targets`), so a hallucinated card ID is
dropped rather than executed.

---

## Provider

Gemini only, via the `google-genai` SDK (`game_engine/ai/providers.py`). On
capacity errors (429) the provider retries with backoff, then falls back to a
second model.

| Role | Env var | Default |
| --- | --- | --- |
| Primary model | `GEMINI_MODEL` | `gemini-flash-lite-latest` |
| Fallback model | `GEMINI_FALLBACK_MODEL` | `gemini-2.5-flash-lite` (pinned, distinct from the `-latest` alias) |
| API key | `GOOGLE_API_KEY` | required |

In production these are Render environment variables, so the model can be
changed without a code deploy. `GET /health` reports the active values.

The provider records `usage_metadata` from every response (requests, input,
output, thinking and cached tokens, per model), so costs are measured rather
than estimated. In a 2,000-game validation run on `gemini-2.5-flash-lite`, a
game averaged 5.6 requests and cost about $0.001.

---

## Observability

- **`ai_decision_logs`** stores each turn's prompt, response, selected index
  and reasoning. The admin dashboard's AI Logs tab reads it.
- **`quality_metrics.py`** logs per-turn Charge efficiency. It is a coarse
  signal: wasting Charge is sometimes correct (saving for a bigger turn), so
  treat it as a smell detector, not a quality score.
- **`/health`** reports the planner (`enum`), model and fallback model, which
  is the quickest way to confirm what production is running.

---

## How to evaluate changes

- **Unit and integration tests**: `test_enumerator.py`,
  `test_enumerator_clone.py`, `test_enum_planner_integration.py`,
  `test_ai_multi_target.py`, `test_ai_turn1_planning.py` and
  `test_card_metadata.py`. None of them call Gemini.
- **Scripted simulation** for anything that changes which sequences exist or
  how they are ranked: enumerator changes, new cards, cost changes. It needs no
  API key and runs thousands of games in minutes. A 2,000-game LLM run
  confirmed that deck rankings from scripted play match LLM play exactly
  (Spearman ρ = 1.0), so the scripted harness is the default instrument.
- **LLM simulation** only for questions about the model itself: prompt
  changes, model swaps, selection quality. Pin the model for both seats, and
  use the throttling controls to stay within quota.

Both are described in [SIMULATION_SYSTEM.md](../SIMULATION_SYSTEM.md).

---

## Known issues

- **Target hallucinations.** In the 2,000-game validation run the model named a
  card ID outside `target_options` about once every five games. The execution
  layer drops these, so no game state was affected, but the rate is a
  prompt-quality signal worth investigating. Scripted players cannot
  hallucinate, so this only shows up in LLM runs.
- **No synergy awareness in the ranking.** `_rank_key` scores a line by what
  it breaks this turn. A setup turn that pays off next turn ranks low, and the
  model only sees the top 12, so some strong combo lines never reach it.

Engine-level issues are tracked in [KNOWN_ISSUES.md](../KNOWN_ISSUES.md).

---

## Version history

| Version | When | What changed |
| --- | --- | --- |
| V1 | Nov 2025 | The LLM chose one action at a time. |
| V2 | Dec 2025 | Structured JSON output; card IDs instead of names. |
| V3 | Dec 2025 | Whole-turn planning in one request. Prompts grew to 12–13k characters, and illegal actions persisted. |
| V4 | Jan 2026 | Two requests: the LLM generated candidate sequences, a server-side validator filtered them, and a second call picked one. In production for several months. |
| Providers | May–Jun 2026 | Groq and OpenRouter added experimentally; production stayed on Gemini. |
| Enumerator | Jun 2026 | Deterministic enumeration replaced V4's first LLM call. |
| Pruning | Jun 28, 2026 | Collapsed to enumerator + Gemini only. Removed the V2/V3/V4 code, the alternative providers, the prompt-examples library and their settings ([#342](https://github.com/RegisCA/ggltcg/pull/342)). The advisory `TurnPlanValidator` followed in [#344](https://github.com/RegisCA/ggltcg/pull/344). |
| Measurement | Jul 2026 | Selection made overridable for scripted policies ([#427](https://github.com/RegisCA/ggltcg/pull/427)); token usage recorded from API responses ([#429](https://github.com/RegisCA/ggltcg/pull/429)). |
