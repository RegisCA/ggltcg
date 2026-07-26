# Evaluating D1–D8: simulation plan

> **Superseded, 2026-07-25.** D1–D8 were dropped: they have no stored games (all 782 are on the
> old deck set), D4 and D8 share 4 of 6 cards, deck cost totals run 0–11, and only 27 of 40 cards
> appear. See [`CARD_EVALUATION_PLAN.md`](CARD_EVALUATION_PLAN.md), which evaluates the whole card
> pool by LLM-free sweep instead.
>
> **This document is still live as Stage 4 of that plan.** The model pinning, the cost model, the
> seat-advantage analysis and the guardrails below all apply unchanged to the final validation run —
> only the deck set they operate on has changed. The one part that is simply wrong is the deck-level
> reading of the stored data, since those games were played by different decks entirely.

*Written 2026-07-25, revised after review. Companion to `backend/src/simulation/README.md` and
`docs/development/SIMULATION_SYSTEM.md`.*

Two objectives, weighted equally:

1. **Rank D1–D8** by overall strength.
2. **Quantify seat advantage** — globally, and per deck, since some decks are expected to prefer
   going first and others second. This is the balance question the card design actually hinges on.

The plan is a single-sitting run on the Tier 1 project, pinned to `gemini-2.5-flash-lite`, costing
roughly $2. The free-tier project is kept as an overflow lane, not the primary path.

## Requests per game: it is ~8, and that already counts both players

This is worth settling precisely, because every cost number downstream depends on it.

`turn_number` increments **once per player turn, not once per round**. That is the strict turn-parity
invariant in `CLAUDE.md` — odd turns are Player 1, even turns are Player 2 — and it is what
`TurnManager.end_turn` implements. The runner's main loop in `runner.py` runs one iteration per
`turn_number`, picks whichever `LLMPlayer` is active that turn, and `_needs_new_plan` fires exactly
once per `turn_number` because the plan is cached and only invalidated when the number changes.

The clearest confirmation is in the stored decision logs from a human-vs-AI game: the single AI player
has entries on turns 1, 3 and 5 — the human's turns 2 and 4 are interleaved in the same counter. In an
AI-vs-AI simulation those even turns are simply the second `LLMPlayer` making its own call. So the
8.08 mean across the 782 stored games is total player turns, roughly 4 per side, and the two AI
players do **not** double it.

What does add requests, and is the right thing to budget for:

- **Mid-turn re-planning.** `_maybe_replan` fires when the plan desyncs from the board, capped at 2
  per turn by `_midturn_replan_count`. Worst case is 3 calls in a turn; in practice it is rare.
- **Retries.** `generate_json` retries up to 3 times on a retryable error, then falls back once.

| Measure | Value across 782 stored games |
|---|---|
| Mean turns per game | 8.08 |
| Median / p90 / p95 | 8 / 11 / 12 |
| Draw rate | 6.9% |
| **Requests per game, planning budget** | **10** |

Ten per game is the number used throughout this document — a deliberate ~25% cushion over the
measured 8.08. If Stage 0 shows the real figure is materially higher, every cost below scales
linearly and you will know within twenty minutes.

`max_turns` is already 20 in `SimulationConfig`, which is correct: capping at 20 keeps 97% of all
turns played while truncating only 1.4% of games. Do not raise it.

## Pin the model

Agreed on `gemini-2.5-flash-lite`. Beyond stability and availability, three concrete reasons:

```bash
export GEMINI_MODEL=gemini-2.5-flash-lite
export GEMINI_FALLBACK_MODEL=gemini-2.5-flash-lite
```

Price, per million tokens: 2.5 Flash-Lite is $0.10 in / $0.40 out, against $0.30 / $2.50 for 3.5
Flash-Lite — 3× the input and 6× the output.

Thinking: 3.x models have thinking **on by default** and thinking tokens bill as output. Your code
never sets `thinking_config`, so on a 3.x model you pay for reasoning on a task ("pick the best index
from this list") that does not need it. If thinking consumes the 384-token `max_output_tokens` budget
in `_get_selector_output_budget`, the response comes back empty, `generate_json` raises, and you pay
for three retries plus a fallback. 2.5 Flash-Lite defaults to `thinkingBudget: 0` and sidesteps all of
this.

Reproducibility: `gemini-flash-lite-latest` is hot-swapped by Google with every release, and your
rate-limit dashboard shows traffic on both 3.5 and 3.1 Flash-Lite — consistent with the alias having
rolled underneath you. An alias that changes mid-run silently invalidates the comparison. Games 1–320
and 321–640 must be played by the same model or the rankings mean nothing.

**Also set both players to the same AI version.** More on this below — it is the single biggest
methodological trap in the existing data.

## What the existing data says about seat advantage — and why it is not yet an answer

Pooling all 782 stored games gives Player 1 a 45.9% share of decisive games, which looks like a solid
second-player advantage. **That number is contaminated.** Runs 9, 10 and 12 were configured with
`player1_ai_version: 4` and `player2_ai_version: 3`, so the two seats were not playing the same AI.
Any seat effect measured across those runs is entangled with a version effect.

Restricting to runs where both players were on V4:

| Slice (V4 vs V4 only) | Decisive games | P1 share of decisive | 95% CI |
|---|---|---|---|
| All matchups | 393 | 54.5% | ±4.9 pts |
| Mirrors only | 100 | 54.0% | ±9.8 pts |
| Non-mirrors | 293 | 54.6% | ±5.7 pts |

So the clean data leans the *opposite* way — a hint of **first**-player advantage — and the interval
barely clears 50%. The honest read is that the seat question is currently **unresolved**, and the
pooled 45.9% figure should be discarded rather than trusted. That is precisely why this run needs to
be designed for it rather than reading it off as a by-product.

A related finding worth your attention independently of cost: matchup outcomes are extremely
polarised. Across cells with 10+ games, 57% resolve to 20% or 80%+ win rates and only 25% land in the
35–65% band. After subtracting sampling noise, the genuine between-matchup spread in win rate is
about 0.31 — roughly eight times the sampling variance at ten games per cell. Decks in this game do
not gently out-perform each other; they mostly hard-counter or get hard-countered. Whatever the ranking says, that shape is the balance story.

One more: several mirror cells drew 9 out of 10 games in under two turns (`User_Slot3` mirror averaged
0.6 turns). A matchup that draws before turn 1 completes is more likely an engine or deck-construction
issue than a balance finding, and is worth a look before you spend games on it.

## Keeping mirrors — reversing my earlier advice

My first draft suggested a `--no-mirrors` flag to skip the 8 self-matchups and save ~12% of the run.
Given that seat balance is a primary objective, that was wrong. **Mirror matches are the cleanest
possible measurement of seat advantage**: identical decks on both sides means the only variable left
is who moves first. Every non-mirror cell confounds seat with matchup. Mirrors are the control, and
this plan buys more of them, not fewer.

They are also cheap — mirror games skew short, and the degenerate ones cost almost no requests at all.

## The run

`SimulationConfig.get_matchups` builds the full n² matrix, so 8 decks give 64 ordered matchups
including 8 mirrors. Player 1 always moves first, so A-vs-B and B-vs-A are genuinely different cells —
the matrix already gives you both seats for every pairing, which is exactly what the seat analysis
needs. No code change required.

**Main run — full matrix, 10 games per cell, 640 games.**

```bash
export GEMINI_MODEL=gemini-2.5-flash-lite
export GEMINI_FALLBACK_MODEL=gemini-2.5-flash-lite

python -m simulation.cli baseline --decks all -i 10 --parallel 10
```

**Mirror deepening — 30 extra games per deck, 240 games.** Run per deck so the CLI produces a single
mirror cell each time.

```bash
for D in D1 D2 D3 D4 D5 D6 D7 D8; do
  python -m simulation.cli baseline --decks $D -i 30 --parallel 10
done
```

| | Games | Requests (10/game) | Cost | Wall clock |
|---|---|---|---|---|
| Stage 0 — calibrate (`--decks D1,D2 -i 5`) | 20 | 200 | $0.05 | 2 min |
| Main matrix | 640 | 6,400 | $1.59 | ~43 min |
| Mirror deepening | 240 | 2,400 | $0.60 | ~16 min |
| **Total** | **900** | **9,000** | **~$2.24** | **~1 hour** |

Cost assumes ~2,000 input and ~120 output tokens per request, which is the order of magnitude implied
by the prompt structure and the TPM-to-RPM ratio on your dashboard. Treat it as ±2× — call it $1.20 to
$4.50 — until Stage 0 measures it. Your $5 cap covers the worst case comfortably.

On Tier 1 the 2.5 Flash-Lite ceiling is 4,000 RPM, so `--parallel 10` is nowhere near a rate limit;
wall clock is bounded by game latency, not quota.

### What this resolution buys

| Question | Games behind it | 95% interval |
|---|---|---|
| Global seat advantage | ~595 decisive | ±4.0 pts |
| Seat advantage, mirrors only (confound-free) | ~295 decisive | ±5.7 pts |
| Any one deck's overall win rate | 140 non-mirror | ±8.3 pts |
| Any one deck's seat preference (first vs second) | 70 + 70 | ±16.6 pts |

The global seat question gets answered properly: a real advantage of 4 points or more will show up
clearly, and the mirror-only estimate cross-checks it without any matchup confound.

Per-deck seat preference is the coarse one. At ±16.6 points this run flags decks with a *large* seat
skew and will miss subtle ones. That is a deliberate trade: halving that interval means quadrupling
the games — 2,560 in the matrix alone, about three hours and $6. My suggestion is to run this pass
first, see which decks show a swing worth chasing, and then spend a targeted second run only on those.
Simulation runs are stored, so a repeat pass pools cleanly with the first.

### Reporting the seat analysis

`analyze_simulation_results.py` currently reports per-matchup and per-deck win rates. For the balance
question you want three additional cuts, none of which need new games:

Per deck, its win rate **as Player 1** pooled over the 7 opponents, and its win rate **as Player 2**
over the same 7 — the difference is its seat preference, and because the opponent set is identical in
both halves the matchup effects cancel exactly.

Per unordered pair, the two directions side by side: `WR(A first vs B)` against `WR(B first vs A)`.
If both exceed 50% the seat effect dominates that pairing; if neither does, the matchup does.

Global first-player win rate with a confidence interval, computed separately for mirrors and
non-mirrors, so you can see whether the two agree.

## Guardrails and hygiene

**Never mix AI versions across seats.** Runs 9, 10 and 12 did, and it poisoned the seat estimate.
Assert `player1_ai_version == player2_ai_version` in the config, or at minimum have the analysis
script refuse to pool runs where they differ.

**Spend cap is set at $5** — that comfortably covers the plan even at the top of the uncertainty band.
Note AI Studio's own warning that overages can occur during roughly ten minutes of latency, so treat
it as a backstop rather than a hard gate.

**The free project is the overflow lane.** Free-tier Flash-Lite is 10 RPM / 250K TPM / 500 RPD, and
RPD is the binding constraint — 500 requests at 10 RPM is a 45-minute burst, then
`RateBudgetLimiter` raises `BudgetExhaustedError` and parks the run. That is roughly 50 games a day,
so the full 900-game plan would take about 18 days on the free key. Not worth it for a $2 run. Keep it
for exploratory work, prompt iteration, and anything you would otherwise think twice about launching.
When you do use it:

```bash
python -m simulation.cli baseline --decks all -i 10 --parallel 10 \
  --rpm 10 --daily-budget 450
```

Leave `RateBudgetLimiter`'s `tz` at its `America/Los_Angeles` default — it matches Google's
Pacific-midnight RPD reset. Overriding it to Toronto time would put your day boundary four hours out
of step and trip 429s. Keep the two keys in separate env files and source deliberately; the failure
mode is silent, since a mis-set key just bills the paid project instead of erroring.

## Two code changes worth making

**Log token usage.** Nothing in the codebase records `response.usage_metadata`, which is why the cost
figures here are estimates rather than facts. `GeminiProvider.generate_json` already holds the response
object; capturing `prompt_token_count`, `candidates_token_count` and `thoughts_token_count` turns every
future run into its own cost report and confirms the requests-per-game figure directly rather than by
inference. Highest-value change in this document.

**Reorder the prompt for implicit caching.** Gemini discounts input tokens matching a previously-seen
prefix by 75%, provided the shared prefix exceeds roughly 1,024 tokens. Your selector prompt is nearly
ideal — the system instruction and card-guidance block are identical across every request in a run —
but `generate_strategic_prompt` puts variable state (`opp_remaining`, the `<context>` line) near the
top, breaking the prefix on every call. Moving `<card_guidance>`, `<board_legend>` and the static
`<task>` text ahead of the volatile `<context>` and `<valid_sequences>` blocks would bill most of the
input at a quarter price. The comment in `strategic_selector.py` says prompt size "is not a real
constraint for this project" — true before 900-game sweeps.

Land this **before** Stage 0 or not at all in this experiment. Changing the prompt changes model
behaviour, and every game in the ranking must be played under identical conditions.

## On 2.5 versus 3.5

Worth doing eventually, but as a separate study, not folded into this one. `simulation.cli compare`
exists for it. Two cautions: hold the deck set and iteration count fixed so the model is the only
variable, and expect the 3.x default thinking behaviour to be part of what you are measuring — a
fairer comparison sets `thinking_level: "minimal"` on the 3.x side, which the code cannot currently do.
Adding `thinking_config` passthrough to `GeminiProvider` is a prerequisite for that experiment.

Your instinct that it will not change the outcome much is probably right for *ranking* purposes: the
enumerator already constrains the model to legal sequences, so the model only picks an index. Where a
stronger model could matter is the seat question — if better play narrows or widens first-player
advantage, that is a real design signal.
