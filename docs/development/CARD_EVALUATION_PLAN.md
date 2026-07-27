# Evaluating the 40-card pool by scripted simulation

*Written 2026-07-25. Supersedes the deck-first approach in
`DECK_EVALUATION_COST_PLAN.md`, which survives as Stage 5 below. Companion to
`backend/src/simulation/README.md`.*

The goal is to understand the card pool well enough to build decks that are good
for a reason. Ranking eight hand-made decks cannot do that; it measures eight
points in a space of C(40,6) = 3,838,380 decks and attributes the result to
whichever deck happened to win.

So the instrument changes. Decks become the *measurement apparatus*, not the
subject: sample thousands of random legal decks, play them against each other,
and regress outcomes onto which cards were present. Every card then gets a value
estimate drawn from thousands of different deck contexts, and no deck-design
judgement enters the measurement at all.

The other change is that the sweep is **LLM-free**, which makes it effectively
free and turns sample size into a non-issue.

## Why D1–D8 were dropped

They were invented before the pool grew and never validated. Checking them
against the card data and the stored simulation history surfaced four problems,
each sufficient on its own:

- **No prior data.** All 782 stored games use the *old* deck set (`Aggro_Rush`,
  `Control_Ka`, `Tempo_Charge`, `Disruption`, `User_Slot3`). Every empirical claim
  in the old plan — seat splits, matchup polarisation — describes different decks.
- **Redundancy.** D4 and D8 share 4 of 6 cards; D3/D4/D6/D8 is one archetype in
  four costumes. Umbruh appears in 4 of 8 decks, Wake in 4, Knight and Rush in 3.
- **Structural imbalance.** Deck cost totals run from 0 (D7) to 11 (D6). At
  ~4 Charge/turn over ~4 own turns, D6 spends its entire game budget deploying its
  hand while D7 deploys for free and spends everything on tussles.
- **Coverage.** Only 27 of 40 cards appear at all, so a third of the pool would
  have gone unmeasured.

## The measurement

### Sampling

`simulation.sweep` draws random 6-card decks from the full 40, requiring at least
`--min-toys` Toys (default 2). The floor exists because an all-Action deck cannot
tussle and barely interacts — those games are noise. It does mildly bias the
sample (Action cards are only ever observed alongside enough Toys), which is why
the floor is kept low.

Each sampled pair is played in **both seats** by default. Differencing the two
directions removes deck quality exactly and leaves the seat effect alone.

Sampling happens in the parent process, so a run is fully determined by
`--seed` regardless of worker count or scheduling order.

### The model

Bradley-Terry with additive card strengths:

```
logit P(player 1 wins) = seat + Σ_c β_c · (in_deck1[c] − in_deck2[c])
```

`β_c` is the card's contribution to the log-odds of winning with the rest of the
deck held fixed. Cards on both sides cancel. The intercept absorbs seat advantage
on its own instead of smearing it across the card estimates.

**One identification trap, worth stating because it is invisible until you look
at the standard errors.** Every deck holds exactly 6 cards, so the card features
sum to zero on *every row*: `Σ_c (in_deck1[c] − in_deck2[c]) = 0`. The 40
coefficients are therefore identified only up to an additive constant, the
Hessian is singular along that direction, and a naive fit returns ±9.8 intervals
on every card while the point estimates still look perfectly reasonable. The fix
is reference coding (pin one card to zero) followed by recentring all 40 to sum to
zero, propagating contrast variances through the same linear map. Card values then
read as **value relative to an average card**. `backend/scripts/analyze_sweep.py`
does this; intervals land around ±0.18 at 8,000 games.

The fit is Newton-Raphson (IRLS) in pure Python. Rows are sparse — at most 12
nonzero features — so it stays fast enough (~18 s at 200k games) to not be worth a
new dependency: numpy is not installed, and adding it to `requirements.txt` would
grow the Render build for a script the app never imports.

### The policy ladder — the part that actually matters

The sweep needs a player, and the choice of player is the main threat to validity.
`TurnPlanner` narrows each turn to ≤12 engine-legal sequences and the LLM's whole
contribution is choosing one index. `simulation.policies` supplies that index
locally:

| Policy | What it does | What it is for |
|---|---|---|
| `greedy` | Takes the enumerator's top-ranked line | The mass sweep |
| `random` | Uniform over legal lines | Null model — value on raw card quality |
| `softmax` | Uniform over the top 3 | Variance without giving up competence |
| `search2` | Depth-2: scores each line after the opponent's best reply | The competence check |

`greedy` follows `enumerator._rank_key` — wins, then most opponent breaks, fewest
self-breaks, least Charge wasted, shortest. That is a strong *single-turn*
heuristic and a biased judge of anything else: it never banks Charge for a bigger
next turn (the Charge-waste term actively discourages it) and never values a board
that only pays off later. Expect it to overrate tempo and underrate setup — cards
like Dream (cost 4), Clone, Copy, Cake (`gain_charge:5`) and Gibbers
(`opponent_cost_increase:1`).

**Running more games does not fix this.** A million greedy games gives a very
tight interval around a biased estimate. The defence is not volume but
disagreement: fit the same dataset under several policies and compare rankings.

- Cards ranked the same everywhere are settled.
- Cards that move a long way between `greedy` and `search2` are the ones whose
  value depends on being piloted well. That gap is the finding, not noise, and
  those cards are the shortlist for Stage 5.

`search2` costs about the same as `greedy` per game — it plays better, so games
end sooner — which makes the cross-check nearly free.

### Reproducibility

The engine has exactly one source of randomness: `random.choice(opponent.hand)`
on a direct attack, on the unseeded global module. `run_game(seed=...)` now seeds
it along with each player's policy RNG, and every seed is recorded per game, so
any run replays exactly.

## Stage 1 results (runs 4–6, 22,000 games, M1 Air, 6 workers)

These are the **post-fix** numbers. Runs 1–3 were run before the `ActionExecutor`
bug below was found and should not be used.

| Policy | Games | Wall clock | Rate | Mean turns | Draws | P1 win % (fitted) |
|---|---|---|---|---|---|---|
| `greedy` | 8,000 | 8.6 min | 15.6 /s | 6.10 | 1.2% | **47.1%** |
| `random` | 8,000 | 19.1 min | 7.0 /s | 7.35 | 0.4% | **45.8%** |
| `search2` | 6,000 | 145.2 min | 0.7 /s | 6.58 | 1.7% | **53.6%** |

Zero engine errors across all 22,000 games.

### The card ranking is robust to policy choice

Spearman rank correlation between the fitted card values:

| | |
|---|---|
| `greedy` vs `random` | ρ = **+0.877** |
| `greedy` vs `search2` | ρ = **+0.892** |
| `random` vs `search2` | ρ = **+0.903** |

This partly walks back the caution above: the fear that a `greedy` ranking would
be confidently wrong is not borne out. The same cards top all three policies, and
`greedy` is a defensible instrument for the mass sweep.

**Consistently strong** (top 8 under every policy): Dream, Umbruh, MaBookBook,
Car, Beary, Hind Leg Kicker, Block, Ka.

**Consistently weak**: Ballaber, Toynado, Paper Plane, Clone, VeryVeryAppleJuice,
Jumpscare.

MaBookBook, Block and Ka rank top-8 under all three policies and appear in **none**
of D1–D8 — direct confirmation that the old deck set left real strength unmeasured.

Biggest `greedy` → `search2` disagreements (the cards whose value depends most on
being piloted well, and the shortlist for Stage 5): Archer (rank 37→22), Raggy
(12→26), Cake (15→28), Copy (27→17), Bubble Blocker (24→15).

### Seat advantage flips with play strength — and survived the bug fix

| Play strength | P1 share (pre-fix) | P1 share (post-fix) |
|---|---|---|
| `random` | 45.8% | **45.8%** |
| `greedy` | 47.1% | **47.1%** |
| `search2` | 52.3% | **53.6%** |
| LLM V4 (older data, different decks) | 54.5% | — |

Monotone in competence, and essentially unchanged by the fix — so this is the most
solid finding in the set. **Moving second is better under weak play; moving first
is better under strong play.** Any seat-balance conclusion is therefore a statement
about an assumed skill level.

A scripted sweep cannot settle the seat question for real players on its own, but
it does mean the old plan's contradictory seat numbers (45.9% pooled vs 54.5%
clean) may reflect play strength, not just the AI-version confound.

### Sample size

Not the binding constraint. At 200,000 games each card appears in ~60,000 decks
and each *pair* co-occurs in ~7,700 — enough for all 40 main effects and all 780
pairwise synergies.

## Stages

**Stage 1 — validation. Done**, results above.

**Stage 2 — the overnight run. Done** (runs 7-8: 200k `greedy` + 20k `search2`).
`search2` measured at 0.7 games/sec, ~20× slower
than `greedy` (the depth-2 search pays a full `end_turn` per node), so the earlier
50,000-game figure was wrong: that would be 20 hours. Revised split for one night:

```bash
cd backend/src
# ~3.7 h
python -m simulation.sweep --games 200000 --policy greedy  --workers 6 --seed 100
# ~8 h — run second, kill it whenever; partial runs analyse fine
python -m simulation.sweep --games  20000 --policy search2 --workers 6 --seed 100
```

Reusing `--seed 100` across both makes the comparison paired. Given ρ ≈ 0.94, the
`search2` pass is now a confirmation step rather than a co-equal measurement, so
truncating it costs little.

**Stage 3 — analysis. Done.** Card values with intervals, the
greedy-vs-search2 disagreement table and the seat effect. Pairwise synergy terms
are still unbuilt; the data supports them (~7,700 co-occurrences per pair at 200k).

```bash
python backend/scripts/analyze_sweep.py --compare 7 8
```

**Stage 4 — candidate decks. Done**, results above.

```bash
python backend/scripts/build_candidate_decks.py --write
cd backend/src && python -m simulation.sweep --decks all --iterations 100 --policy greedy
python backend/scripts/deck_matrix.py --run <id>
```

**Stage 5 — targeted LLM validation. Done**, results below. Play the derived decks under the real
Gemini player to confirm the ranking survives competent play. This is the original
$2 run from `DECK_EVALUATION_COST_PLAN.md` — its model pinning, cost model and
seat-analysis cuts all still apply — but spent on decks that were earned rather
than invented.

Two things make it worth the money rather than a formality:

- The deck ranking held between `greedy` and `search2` (ρ = 0.976), so if it also
  holds under an LLM, it is a property of the game and the scripted harness can be
  trusted for future questions without further LLM spend.
- The **seat** question is unresolved and cannot be settled by a scripted policy,
  since per-deck preference flipped between the two policies already. An LLM run is
  the only remaining instrument for it here.

#### Measured cost (calibration, 20 games, 2026-07-26)

`GeminiProvider` now records `response.usage_metadata`, so cost is measured rather
than inferred. The old estimate was badly pessimistic:

| | Estimated | **Measured** |
|---|---|---|
| Requests per game | 10 | **5.45** |
| Input tokens / request | ~2,000 | **1,563** |
| Output tokens / request | ~120 | **61** |
| Cost per game | $0.0025 | **$0.00099** |

Three findings:

- **Thinking tokens: 2 in total.** Confirms `gemini-2.5-flash-lite` defaults to
  `thinkingBudget: 0`. Pinning to 2.5 rather than a 3.x model was correct.
- **Implicit caching barely engages** — 4,401 of 170,382 input tokens (2.6%),
  exactly as predicted: variable state near the top of the selector prompt breaks
  the shared prefix. Input is 86% of spend, so reordering would be worth real
  money — but it changes prompt behaviour, so it belongs in a *separate*
  experiment, never mid-comparison.
- **5.45 requests/game is a floor, not the expectation.** Calibration used
  Apex vs Control_Worst, which is lopsided (5.5 turns vs 8.08 across stored
  history). Requests track turns almost exactly (0.99 per turn), so budget ~7
  requests/game for a balanced matrix.

#### The run

Five decks, not eight. Cells grow as n², so deck count is the expensive dial, and
three of the eight answer questions already settled (`Rival_B` is mid-tier with no
distinct question; `Curve` already underperformed; `Stat_Max` did its job). Keeping
`Apex`, `Rival_A`, `Combo`, `Control_Worst` and `Legacy_Best` puts the whole budget
on decks that each test something.

```bash
export GEMINI_MODEL=gemini-2.5-flash-lite
export GEMINI_FALLBACK_MODEL=gemini-2.5-flash-lite
# Local SQLite: production already holds the pre-2026-07-26 rows flagged above,
# and mixing experiment eras in one table is how they get trusted by accident.
export DATABASE_URL="sqlite:///$(pwd)/../data/llm_validation.db"
python -m simulation.cli baseline \
  --decks Apex,Rival_A,Combo,Control_Worst,Legacy_Best -i 80 --parallel 10
```

2,000 games (25 cells x 80), ~$2.60, ~70 min. Per-deck win rate ±3.5 pts; global
seat ±2.2 pts — enough to separate 50% from 53%, which is the point of spending.

Note the CLI assumes its database already exists. Against a fresh local file it
fails with a raw SQLAlchemy `no such table` rather than "run migrations"; create
the schema first via `Base.metadata.create_all`.

#### Stage 5 results (2,000 games, $2.10, zero errors)

Measured cost came in at 5.63 requests/game and $0.00105/game — within 3% of the
calibration figure, so the accounting is trustworthy.

**The deck ranking validates exactly: ρ = +1.000 against both scripted policies.**

| Deck | greedy | search2 | **LLM** |
|---|---|---|---|
| Rival_A | 67.9% | 72.4% | **75.5%** |
| Apex | 62.9% | 70.3% | **61.3%** |
| Legacy_Best | 52.3% | 50.1% | 51.6% |
| Combo | 57.4% | 53.3% | 51.6% |
| Control_Worst | 6.2% | 6.2% | 10.0% |

`Rival_A` (Dino, Dream, Hind Leg Kicker, Ka, Knight, Umbruh) wins under a greedy
bot, a depth-2 search bot and a real LLM, and gets *stronger* as the player
improves (67.9 → 72.4 → 75.5).

The consequence that matters beyond this experiment: **the free scripted harness
predicts LLM outcomes.** Deck questions can now be answered in nine minutes for
nothing, and an LLM run is only needed for questions about the model itself.

**Seat advantage: none. P1 wins 49.0% ± 2.2** (interval [46.9, 51.2], includes 50).

| Player | P1 win % |
|---|---|
| `random` | 45.8% |
| `greedy` | 47.1% |
| `search2` | 53.1% |
| **LLM** | **49.0%** |
| Historical LLM V4 (different decks) | 54.5% |

The monotone "seat advantage grows with skill" reading built from the scripted
ladder does **not** survive a real LLM, and is retracted. The game is
seat-balanced; no compensation rule is warranted.

**But mirrors are violently deck-specific**, and this is the finding that survives:

| Mirror | P1 win % (LLM) | P1 win % (greedy) |
|---|---|---|
| Control_Worst | 83.8% | — |
| Apex | 67.5% | 70.0% |
| Combo | 55.0% | — |
| Rival_A | 50.0% | 32.0% |
| Legacy_Best | **10.0%** | 17.0% |

Same deck on both sides, so the only variable is who moves first. In the
`Legacy_Best` mirror, moving first is close to a loss — and `greedy` found the
same thing independently (17%), as it did for `Apex` (70.0 vs 67.5). These large
effects **cancel in aggregate**, which is exactly why the global figure sits on
50%.

Per-deck *pooled* seat deltas still fail to replicate across policies (`Rival_A`
+9.0 under `search2`, −14.0 under the LLM). Trust the mirrors; do not trust the
pooled per-deck numbers.

#### Open: target hallucinations

382 occurrences across 2,000 games — roughly one every five games — where the model
names a card id absent from the action's `target_options`. `_filter_to_valid_targets`
drops every one, so no game was corrupted, but the frequency is a real
prompt-quality signal. It is invisible to scripted sweeps by construction, since a
scripted player cannot hallucinate. Worth its own investigation.

## Carried over from the old plan

Still true and still worth doing:

- **Pin the model** to `gemini-2.5-flash-lite` for Stage 5; never mix AI versions
  across seats (runs 9, 10 and 12 did, poisoning their seat estimates).
- **Log token usage.** Nothing captures `response.usage_metadata`, so LLM cost
  remains an estimate.
- `max_turns: 20` is correct; do not raise it.

Superseded:

- The 64-cell D1–D8 matrix and the mirror-deepening pass.
- Any conclusion drawn from pooling runs with mismatched AI versions.

## The bug the sweep uncovered

Chasing the plan-execution fallback rate found a real defect **in the simulation
harness** (production was never affected):

`simulation.runner._execute_action` called `engine.play_card()` and
`engine.initiate_tussle()` directly, while `api/routes_actions.py` — and the
enumerator that builds every plan — both go through `ActionExecutor`. The direct
calls skip `ActionExecutor._handle_targets`, so **every targeted effect resolved
with no target**: the card was paid for, did nothing, and went to the break zone.

Reproduced in isolation — same state, same valid target:

| Path | Result |
|---|---|
| `engine.play_card` (runner) | Copy → break zone, still `Copy`/ACTION, 3 Charge spent for nothing |
| `ActionExecutor` (production + enumerator) | Copy → in play as `Copy of Raggy`, TOY 2/3/2, gains a tussle |

It was silent because games still completed. The only symptom was the plan/board
desync it caused, surfacing as "LLM execution fallbacks" — which a live LLM player
papers over with an extra API call, and a scripted player cannot.

**Affected:** at minimum the 9 cards with targeted effects (Ballaber, Copy,
Toynado, Clean, Drop, Jumpscare, Monster, Clone, Stomp), plus the variable-cost
cards (Copy, Glue, Stomp) whose *cost* depends on the chosen target and was
therefore also wrong.

**Measured impact** (runs 1–3 vs 4–6, identical seeds and deck pairs). The damage
was concentrated in three cards; everything else moved by less than 0.2 and the
top of the ranking barely changed:

| Card | greedy pre → post | rank | search2 rank |
|---|---|---|---|
| Copy | −0.807 → −0.153 | 40 → 27 | 40 → 17 |
| Twist | −0.699 → −0.031 | 39 → 18 | 38 → 12 |
| Ballaber | +0.065 → −0.582 | 16 → 38 | 16 → 40 |

Copy and Twist were being scored as the worst cards in the pool while doing
literally nothing for their Charge. Ballaber moved the *other* way: its
alternative cost (break one of your own cards) now actually gets paid, so it is
correctly much worse. Overall pre/post rank correlation: ρ = +0.88 (`greedy`),
+0.78 (`random`), +0.80 (`search2`).

**Consequences:**

- Runs 1–3 (22,000 games) are superseded by runs 4–6. They stay in the database
  for this comparison only.
- **The 782 historical LLM simulation games have the same flaw**, since they ran
  through the same runner. Any card-level reading of them is unsafe — though the
  seat-advantage figures proved insensitive to the fix.

  > **Do not use `simulation_games` rows created before 2026-07-26 for card-level
  > analysis.** Nothing in the schema marks them, so a future reader will find
  > them and reasonably assume they are sound. They remain valid for turn counts,
  > draw rates and seat effects, which do not depend on targeted effects
  > resolving. Anything about a specific card's strength does. The cleanest fix is
  > a `runner_version` column on `simulation_runs`, tracked separately.
- Fixing it dropped the `random` fallback rate from **10.8% → 3.0%** and left
  `greedy` at 0.8%.

Pinned by `test_runner_resolves_targeted_effects_like_production` in
`backend/tests/test_scripted_player.py`.

## Stage 3 results: candidate decks

Decks are derived from the fitted values by
`backend/scripts/build_candidate_decks.py`, so the set is a function of the data
rather than of taste. Two are controls whose job is to fail.

**An additive card model has exactly one best deck.** The first attempt produced
three identical decks (top-6 by greedy, by search2 and by consensus were the same
six cards) — the same redundancy that made D1–D8 uninformative. Diversity has to
be imposed: each rival is the best deck sharing at most 2 cards with everything
chosen before it.

Round-robin, 8 decks x 64 cells x 100 games = 6,400 games, `greedy`:

| Deck | Win% | 95% CI | Σβ (predicted) |
|---|---|---|---|
| Rival_A | **67.9%** | [65.6, 70.2] | +2.93 |
| Apex | 62.9% | [60.5, 65.3] | +3.48 |
| Rival_B | 60.9% | [58.5, 63.2] | +2.53 |
| Combo | 57.4% | [55.0, 59.8] | +1.79 |
| Curve | 53.0% | [50.6, 55.4] | +3.16 |
| Legacy_Best | 52.3% | [49.9, 54.8] | +2.51 |
| Stat_Max *(control)* | 39.2% | [36.9, 41.7] | +2.16 |
| Control_Worst *(control)* | **6.2%** | [5.2, 7.5] | −2.86 |

**Both controls behaved.** `Control_Worst` won 6.2%, so the card model predicts
decisively. `Stat_Max` — the best deck by raw speed+strength+stamina, ignoring the
fit entirely — lost to `Apex` by 24 points, so the 220,000 games bought something
that adding up the numbers on the card does not.

**But the model's own best deck is not the best deck.** `Rival_A` (Σβ +2.93) beats
`Apex` (Σβ +3.48). Spearman between predicted Σβ and measured win rate is **+0.69**,
and only **+0.54** excluding the trivially-correct `Control_Worst`. The additive
model sorts good from bad emphatically and ranks *among the good* weakly. The two
large misses are informative:

- `Curve` predicted 2nd, finished 5th — cheap deployment did not pay off.
- `Combo` predicted 7th, finished 4th — the Hind Leg Kicker shell beating its
  parts by three places, independently confirming the ablation's superadditivity
  with a different instrument.

`Legacy_Best` (the strongest of the original hand-made decks) finished 6th of 8.

### The deck ranking survives a policy change; the seat effect does not

Same matrix re-run under `search2` (3,840 games, 60 per cell, same decks and seed):

| Deck | greedy | search2 | shift |
|---|---|---|---|
| Rival_A | 67.9% | **72.4%** | +4.5 |
| Apex | 62.9% | **70.3%** | +7.4 |
| Rival_B | 60.9% | 58.8% | −2.1 |
| Combo | 57.4% | 53.3% | −4.1 |
| Legacy_Best | 52.3% | 50.1% | −2.2 |
| Curve | 53.0% | 46.0% | −7.0 |
| Stat_Max | 39.2% | 42.9% | +3.7 |
| Control_Worst | 6.2% | 6.2% | 0.0 |

**Deck ranking: ρ = +0.976.** Only `Curve` and `Legacy_Best` swap. `Rival_A` wins
under both policies, and `Apex`/`Rival_A` both improve under lookahead — good decks
reward good piloting. `Combo` drops, consistent with the ablation's finding that
Jumpscare and That was fun are net-negative and that greedy simply cannot punish
them.

**Per-deck seat preference: ρ = +0.333. Do not trust it.**

| Deck | seat Δ greedy | seat Δ search2 | |
|---|---|---|---|
| Rival_A | −28.6p | +9.0p | **flipped** |
| Combo | +20.9p | −9.2p | **flipped** |
| Legacy_Best | −7.4p | +9.1p | **flipped** |
| Rival_B | −30.2p | −13.9p | same sign |
| Apex | +13.9p | +21.8p | same sign |
| Curve | +15.8p | +19.1p | same sign |

Three of eight flip sign and `Rival_A` swings 37.6 points, so the large per-deck
seat preferences measured under `greedy` are **artifacts of that policy, not
properties of the game**. An earlier revision of this document reported them as a
finding; that was wrong and is retracted here.

What survives: the *global* direction (P1 53.4% on this matrix, matching 53.1% from
the random sweep), and three decks whose sign is stable (`Rival_B` prefers second;
`Apex` and `Curve` prefer first). The original plan doc's hypothesis — that decks
differ in seat preference — is neither confirmed nor refuted by a scripted sweep;
it needs a policy whose seat behaviour is itself trustworthy.

### Engine-rejected actions

The fixed-deck matrices show ~0.2 engine-rejected actions per game (1,339 in the
greedy run, 719 in `search2`), against ~0.06 in random-deck sweeps: stronger decks
push Charge limits harder, so roughly a fifth of games contain an action the engine
declined. Not an error, and invisible before the `rejected` counter existed.

## Combos: declared, not discovered

Multi-card combos need a different instrument. At 200,000 games:

| Subset | Combinations | Co-occurrences each | Verdict |
|---|---|---|---|
| Pairs | 780 | ~7,700 | Well powered |
| Triples | 9,880 | ~810 | Large effects only |
| 4-sets | 91,390 | ~66 | Not recoverable at any realistic sample size |

Blind 4-set search is not underpowered, it is impossible: 66 samples against
91,390 hypotheses. A specific named 4-card combo appears in roughly 293 of the
400,000 deck instances.

Worse, sample size is not even the binding constraint. `greedy` ranks lines by
`cards_broken` first, so a Charge-engine turn that bounces the opponent's board
but breaks nothing scores zero on the primary key and is never selected. **More
games cannot fix a combo that is never played.**

So `simulation.combo` measures *declared* combos by leave-one-out ablation: force
the card set into every deck, then drop one piece and replace it with the same
neutral filler, against the same opponent under the same seed. Everything is
paired, so variant decks differ by exactly one card — that removes filler and
opponent variance instead of averaging over it, which is what makes a few thousand
games sufficient.

```bash
python -m simulation.combo \
  --combo "Hind Leg Kicker,Jumpscare,That was fun,Car|Dino|Block|MaBookBook|Bubble Blocker" \
  --games 4000 --policy search2 --max-actions 16
```

`A|B|C` declares a *role* ("a 0-cost Toy") rather than a card, and aggregates into
one variant. Every game records the longest single turn on the combo side, because
without it you cannot tell "the combo is weak" from "the combo never fired".

### First combo measured: Hind Leg Kicker engine

3,996 games, `search2`, `--max-actions 16`, 333 paired trials x 2 seats. Because
the design is paired (same opponent, seed and fillers; one card swapped), the
correct test is the per-trial difference, not the marginal intervals:

| Variant dropped | Mean delta | 95% CI | p |
|---|---|---|---|
| Hind Leg Kicker | **+15.0 pts** | [+10.6, +19.5] | <0.0001 |
| 0-cost Toy slot | **+11.9 pts** | [+7.2, +16.6] | <0.0001 |
| Jumpscare | −3.7 pts | [−7.9, +0.6] | 0.09 (ns) |
| That was fun | −3.2 pts | [−7.5, +1.2] | 0.16 (ns) |
| all four | +6.4 pts | [+1.5, +11.2] | 0.01 |

Against the additive prediction from each card's solo value:

| Card | solo β | predicted | observed | excess |
|---|---|---|---|---|
| Hind Leg Kicker | +0.341 | +8.5 pts | +15.0 | **+6.5 superadditive** |
| 0-cost Toy | +0.368 | +9.1 pts | +11.9 | +2.8 (additive) |
| Jumpscare | −0.351 | −8.3 pts | −3.7 | **+4.6 superadditive** |
| That was fun | −0.358 | −8.4 pts | −3.2 | **+5.2 superadditive** |

**The combo is real.** All three engine pieces beat their solo values inside this
shell. Jumpscare and That was fun are ~5 points *less bad* here than in a random
deck — but they start from −0.35 each, so the bonus does not carry them to
break-even. The shell is carried by Hind Leg Kicker, which is worth nearly double
its solo value when surrounded by cheap cards.

Turn length tells the same story: dropping Hind Leg Kicker collapses the mean
longest turn from 8.6 to 5.1, while dropping the Toy leaves it at 8.7 (the Toy
supplies a body, not tempo). Longest turn observed: **17 actions**.

Also note `drop:Hind Leg Kicker` (42.5%) is *worse* than `none` (51.1%): without
the engine, Jumpscare and That was fun are two dead slots.

**Caveat, and it matters.** The solo betas come from run 8, which ran at the
default 8-action cap, while the ablation ran at 16. Cards that benefit from long
turns would show inflated "excess" — and Hind Leg Kicker, Jumpscare and That was
fun are exactly those cards, so the confound pushes the same way as the finding.
Separating them needs a sweep at `--max-actions 16` to produce matched solo values.

### The 8-action enumerator cap is binding

`DEFAULT_MAX_ACTIONS = 8` caps enumerated sequence length, and a turn that is never
enumerated can never be played by *any* selector — scripted or LLM. Real players
chain 8-10 actions via Charge-refund engines, which sits right at that ceiling.

Measured, same combo and seeds, only the cap changed (n=60/cell, greedy):

| | max_actions=8 | max_actions=16 |
|---|---|---|
| Longest turn, p95 | **9** (= 8 + end_turn: the cap binds exactly) | **12** |
| Full-combo deck, mean actions/turn | 6.9 | 8.0 |
| Full-combo deck win rate | 54.2% | 60.0% |
| Contribution of Hind Leg Kicker | −9.2 pts | −17.5 pts |
| Contribution of the 0-cost Toy slot | −5.0 pts | −16.7 pts |

The turn-length result is structural and certain: at cap 8 the p95 sits exactly at
the ceiling, and raising it lets turns run to 11 real actions. The win-rate deltas
point the same way but are **not** statistically separated at n=60 (±12 pts) — they
need a proper run before being quoted.

**Decision (2026-07-26): `DEFAULT_MAX_ACTIONS` stays at 8.** The backend runs on
Render's free tier, and 8 is a reasonable speed-vs-challenge trade for the AI
opponent. Human players have no such limit, which is fine and arguably the point —
the ceiling constrains the bot, not the game.

This settles the measurement question too, by splitting it in two:

- **Cap 8 (runs 7–8)** measures *what the AI opponent actually plays like*. This
  is the right baseline for balancing the game as shipped.
- **Cap 16 (combo harness)** measures *what the game itself supports*. This is the
  right lens for design questions about human play.

Both are valid; they answer different questions. A matched-cap sweep is therefore
not needed for production, only if someone wants a confound-free superadditivity
number for a human-play combo.

`TurnPlanner.enum_max_actions` / `enum_max_sequences` default to `None` (engine
defaults) so live behaviour is unchanged; only the combo harness raises them.

## Known gaps

- **Residual plan-execution fallbacks** (`greedy` 0.8%, `random` 3.0%). These are
  genuine plan/board desync, not a bug: the enumerator commits to a multi-step
  line at turn start, and by step 3 the planned defender may be gone so only a
  direct attack is legal. A scripted player then ends its turn early. Small enough
  to accept; the graceful fix is to skip the single step rather than abandon the
  turn.
- **`analyze_simulation_results.py` was deleted** in commit `5d177fb`, so the
  LLM-run reporting from the old plan has nothing to run in.
  `analyze_sweep.py` covers the scripted dataset only.
- **Card values are additive by construction.** Synergy has to be added as
  explicit interaction terms; the main-effects model will score a combo card at
  its average contribution across decks that mostly cannot use it.
- **`min_toys` conditioning** slightly biases Action-card estimates.
- **`search2`'s evaluation function is material-flavoured** (breaks, board, stats,
  Charge). It is a better judge than `greedy`, not an authority.
