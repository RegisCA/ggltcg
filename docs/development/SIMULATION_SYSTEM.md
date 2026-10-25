# Simulation System

GGLTCG has no shuffled deck: each player builds a 6-card deck and the whole
hand is visible from the start. Once the decks are chosen, the outcome depends
on the cards and on how well they are played. That makes the game a good fit
for simulation. Play enough games with the cards varied systematically and you
can measure how strong each card is, whether a new card is over- or
under-costed, and whether moving first is an advantage.

The simulation system exists to answer those balance questions for the game's
designer. It plays complete games with the real rules engine, records every
result, and fits a statistical model that turns win/loss records into a
strength score per card or per deck.

- [Two harnesses, one engine](#two-harnesses-one-engine)
- [Scripted sweeps](#scripted-sweeps)
- [LLM simulations](#llm-simulations)
- [Findings](#findings)
- [Limitations](#limitations)
- [Further reading](#further-reading)

## Two harnesses, one engine

The AI opponent plays a turn in three steps: the engine enumerates every legal
action sequence, one Gemini call picks one, and the server executes it (see
[AI_CURRENT_STATE.md](ai/AI_CURRENT_STATE.md)). Only the middle step involves
a model. The simulation system keeps the first and last steps and offers two
ways to do the middle one:

```text
                 enumerate legal sequences   →   choose one   →   execute
                 (engine, deterministic)                         (engine)
                                                    │
                     ┌──────────────────────────────┴──────────────┐
                     │                                             │
          Scripted sweep: a local policy               LLM simulation: Gemini
          (simulation.sweep, simulation.combo)         (simulation.cli, admin UI)
          free, ~15 games/s on 6 cores                 ~$0.001 and 5–6 requests per game
```

| | Scripted sweeps | LLM simulations |
| --- | --- | --- |
| Chooser | A local policy (`greedy`, `search2`, ...) | Gemini, exactly as in live games |
| Cost | CPU only, no API key | API requests, throttled against quota |
| Typical run | 10,000–200,000 random-deck games | 100–2,000 fixed-deck games |
| Storage | Local SQLite (`backend/data/sweep.db` by default) | `simulation_runs` / `simulation_games` tables |
| Used for | Card values, cost experiments, deck ranking, combos | Model comparison, prompt changes, final validation |
| Entry point | `python -m simulation.sweep` | `python -m simulation.cli`, Admin → Simulation |

The scripted harness is the default instrument. A 2,000-game Gemini run
reproduced its deck ranking exactly (see [Findings](#scripted-play-predicts-llm-play)),
so an LLM run is only needed when the question is about the model itself.

Both harnesses run games through `simulation/runner.py`, which uses the same
`ActionExecutor` as the live API. Every game is seeded. The engine's only
random event (a direct attack sends a random card from the defender's hand to
the break zone) and each scripted player's choices use per-game seeds that are
stored with the result, so any game can be replayed exactly.

## Scripted sweeps

### Measuring cards instead of decks

Ranking a handful of hand-built decks only tells you about those decks: there
are over 8 million possible 6-card decks from the current 45-card pool. A sweep
turns this around. Decks become the measuring apparatus rather than the
subject:

1. **Sample random legal decks.** Six distinct cards, at least 2 of them Toys
   (an all-Action deck can barely interact, so those games are noise).
2. **Play each pair twice**, once with each deck moving first. This cancels
   seat advantage out of the card estimates and measures it separately.
3. **Fit one strength score per card** from the outcomes.

Each card ends up observed in thousands of different decks, and no
deck-building judgement enters the measurement.

### The model

`backend/scripts/analyze_sweep.py` fits a Bradley-Terry model with additive
card strengths:

```text
logit P(player 1 wins) = seat + Σ_c β_c · (in_deck1[c] − in_deck2[c])
```

`β_c` is how much card *c* shifts the log-odds of winning, with the rest of
the deck held fixed. The scores are centred so the average card is 0, and are
reported as **win % against an average card**: `1 / (1 + e^−β)`. A card at 60%
wins 60% of the time against an otherwise identical deck holding an average
card instead.

One identification detail matters. Every deck has exactly 6 cards, so the
features on every row sum to zero and the coefficients are only defined up to
a constant. A naive fit returns sensible-looking point estimates with useless
±9.8 intervals. The script pins one reference card, fits, then recentres and
propagates the variances, which gives intervals of about ±0.09 at 10,000
games. The fit is plain Newton-Raphson in Python to avoid adding numpy to the
backend's dependencies.

### Policies

The policy that replaces Gemini is the main threat to validity, so there are
several (`simulation/policies.py`):

| Policy | Behaviour | Role |
| --- | --- | --- |
| `greedy` | Takes the enumerator's top-ranked line: most cards broken this turn | Fast mass sweeps |
| `search2` | Looks one turn ahead: scores each line after the opponent's best reply | Competence check |
| `softmax` | Picks at random among the top 3 lines | Adds variance |
| `random` | Picks uniformly among legal lines | Null model |

`greedy` is myopic. It never saves Charge for a bigger turn and never values
setup that pays off later. Running more games doesn't fix that, it just gives a
tighter interval around a biased number. The defence is to run the same deck
pairs under two policies and compare: reusing `--seed` replays identical deck
pairs, so the comparison is paired. Cards that rank the same under both are
settled; cards that move a long way are the ones whose value depends on being
played well, and that gap is a finding in its own right.

### Running a sweep

From `backend/src`, with the virtualenv active:

```bash
# Card values: 10,000 random-deck games, both policies, same deck pairs
python -m simulation.sweep --games 10000 --policy greedy  --seed 100
python -m simulation.sweep --games 10000 --policy search2 --seed 100
python ../scripts/analyze_sweep.py --compare 1 2   # values, seat effect, rank agreement

# Cost experiment: same seed, alternative card data
CARDS_CSV_PATH=~/ggltcg-sim/variant_A.csv \
  python -m simulation.sweep --games 10000 --policy search2 --seed 100 --db variant.db

# Fixed decks from simulation_decks.csv, round-robin
python -m simulation.sweep --decks all --iterations 100 --policy greedy
python ../scripts/deck_matrix.py --run <id>
```

`greedy` runs at roughly 15 games/second on 6 workers; `search2` is about 20
times slower. Runs are CPU-bound and parallel across processes, so a laptop
handles 20,000 `search2` games overnight. Partial runs analyse fine.

**Cost experiments** reuse the seed so that every variant replays the exact
same deck matchups and only the card's cost differs. Re-running the original
costs with the same seed reproduces the original numbers to the decimal, which
confirms the setup is paired.

**Candidate decks** are derived from the fitted values by
`backend/scripts/build_candidate_decks.py` rather than chosen by hand. It
picks the best deck, then the best deck sharing at most 2 cards with it, and so
on, plus two control decks that should lose. The output is
`backend/data/simulation_decks.csv`.

### Combos

An additive model scores a combo card at its average value across decks that
mostly can't use it. For declared combos, `simulation.combo` runs a paired
leave-one-out ablation: force the combo into every deck, then drop one piece
at a time against the same opponent and seed.

```bash
python -m simulation.combo \
  --combo "Hind Leg Kicker,Jumpscare,That was fun,Car|Dino|Block|MaBookBook" \
  --games 4000 --policy search2 --max-actions 16
```

`A|B|C` declares a role ("any 0-cost Toy") rather than a single card. Each game
also records the longest turn on the combo side, which distinguishes "the
combo is weak" from "the combo never fired".

## LLM simulations

The LLM harness plays fixed decks from `simulation_decks.csv` with the real
Gemini player. Runs are stored in the application database, so they appear in
the admin dashboard alongside runs started from the CLI.

```bash
cd backend/src
python -m simulation.cli list-decks
python -m simulation.cli baseline --decks Apex,Rival_A --iterations 50
python -m simulation.cli compare --model1 gemini-2.5-flash-lite --model2 gemini-flash-lite-latest
python -m simulation.cli status <run_id>
python -m simulation.cli resume <run_id>
```

The same runs can be started from **Admin → Simulation** (`/admin.html`) or
`POST /admin/simulation/start`, which caps a request at 500 games. The admin
tab shows a P1-win-rate matrix per matchup and a turn-by-turn Charge and
action log for each game. The `/admin/simulation/*` routes require an
allowlisted admin account.

**Pin the model** for comparable results. By default a simulation uses the
same model resolution as live games (`GEMINI_MODEL`, then the provider
default), which is a moving `-latest` alias. Set `GEMINI_MODEL` and
`GEMINI_FALLBACK_MODEL` to the same pinned model, and never mix models across
seats in a run meant to measure seat advantage.

### Throttling and multi-day runs

Long campaigns can exceed the Gemini daily quota. The run can throttle itself
and pause instead of failing:

- `--rpm N` caps requests per minute across all parallel workers.
- `--daily-budget N` stops starting new games after N requests in a day
  (Pacific time, matching Gemini's quota reset). The count is persisted in
  `api_usage_daily`, so it survives restarts.
- `--wait` (default) sleeps until the budget resets and resumes automatically.
  `--no-wait` exits with code 75 so cron or launchd can call `resume` later.

Completed games are persisted as they finish. On resume the orchestrator skips
exactly the stored game numbers and rebuilds the aggregate statistics from the
stored rows, so the final report covers the whole campaign. A run that runs out
of budget is parked, never recorded as draws. Server-started runs park and
wait for a resume call; only the CLI sleeps across days.

With a measured ~5.6 requests per game, a 2,000-game run costs about $2 on
`gemini-2.5-flash-lite`. The full CLI reference, including a cron wrapper, is
in [`backend/src/simulation/README.md`](../../backend/src/simulation/README.md).

## Findings

Results from July to October 2026. Numbers are from the scripted harness unless
marked otherwise. The research log, with every run and every retracted
hypothesis, is [CARD_EVALUATION_PLAN.md](CARD_EVALUATION_PLAN.md).

### Card rankings are robust to the choice of player

Across 22,000 games of the first validation sweep, the card rankings from
`greedy`, `search2` and `random` correlated at Spearman ρ = 0.88–0.90. The same
cards top every policy (Dream, Umbruh, MaBookBook, Car, Beary, Hind Leg Kicker,
Block, Ka), and the same cards sit at the bottom (Ballaber, Toynado, Paper
Plane, Clone, VeryVeryAppleJuice, Jumpscare). The original hand-built
simulation decks contained none of MaBookBook, Block or Ka, so they had left
real strength unmeasured.

### Scripted play predicts LLM play

Eight candidate decks derived from 220,000 scripted games were ranked by
round-robin under `greedy` and `search2` (ρ = 0.976). Five of them were then
played 2,000 times by the real Gemini player, for $2.10.

| Deck | `greedy` | `search2` | Gemini |
| --- | --- | --- | --- |
| Rival_A | 67.9% | 72.4% | 75.5% |
| Apex | 62.9% | 70.3% | 61.3% |
| Legacy_Best | 52.3% | 50.1% | 51.6% |
| Combo | 57.4% | 53.3% | 51.6% |
| Control_Worst | 6.2% | 6.2% | 10.0% |

The ranking matched exactly (ρ = 1.0 against both policies). Deck questions
can be answered in minutes for free, and LLM spend is reserved for questions
about the model.

### The game is seat-balanced

Under Gemini, player 1 won 49.0% ± 2.2 of decisive games: no measurable
advantage for moving first. Scripted policies disagreed with each other here
(`greedy` 47.1%, `search2` 53.6%), which is why the LLM run was needed.
Individual decks do care a lot. In mirror matches the first player won 67.5%
with Apex and only 10% with Legacy_Best, and `greedy` found the same direction
independently. These effects cancel out across decks.

### The AI's 8-action turn limit binds for combos

The enumerator caps a sequence at 8 actions. At that cap the 95th-percentile
longest turn sits exactly at the ceiling; at 16 it rises to 11 real actions,
and the Hind Leg Kicker combo deck wins more. The cap stays at 8 for live play
as a speed trade-off on the free-tier backend. Sweeps at the default cap
measure the game as the AI plays it; the combo harness raises the cap to
measure what the game allows a human to do.

### Batch 4: five "When played" Toys

The October 2026 card batch (MA14, Sock Serpent, Sir Scares a lot, Candy Golem,
Laundry Lad) was measured before release: 20,000 random-deck games over the
45-card pool, then 50,000 more for a cost experiment requested by the
designer. Values are win % against an average card under `search2`, with the
rank out of 45.

| Card | Cost | Win % | Rank |
| --- | --- | --- | --- |
| Sock Serpent | 3 | 65.1% | 2 |
| MA14 | 2 | 59.6% | 9 |
| Sir Scares a lot | 1 | 56.2% | 14 |
| Laundry Lad | 2 | 55.0% | 16 |
| Candy Golem | 6 | 46.2% | 28 |

- **A Toy beats its Action twin.** Three of the new Toys copy an existing
  Action's effect and then stay in play as a body. Sock Serpent scored 21 points
  above Drop, which has the same effect.
- **Candy Golem is held back by its up-front cost.** It nets out at 2 Charge
  (pay 6, gain 4 back) but needs 6 Charge in hand, so it often waits turns to
  be played. It ranks 9 places higher under `search2` than under `greedy`, so
  it rewards planning, but is below average under both.
- **Cost experiment.** Each extra Charge on Sock Serpent costs it roughly 6–14
  points (65.1% → 58.9% → 44.7% at costs 3, 4, 5). Candy Golem at cost 5 jumps
  to 57.0%; at cost 4 the body is effectively free and it becomes the strongest
  card in the game at 75.5%. Its fair cost sits between two whole numbers.

The cards shipped at their original costs. The results went to the designer as
a standalone report.

## Limitations

- **Scripted players are not people.** `search2`'s evaluation is
  material-flavoured (cards broken, board, stats, Charge). A human who banks
  Charge or plans multi-turn combos may value some cards differently.
- **Card values are additive.** Synergy needs explicit interaction terms or
  the combo harness. The data supports all pairwise terms at 200,000 games, but
  they are not built yet.
- **The 2-Toy minimum** slightly biases Action-card estimates, since Actions
  are only ever observed alongside enough Toys.
- **Simulation rows created before 2026-07-26** came from a runner version
  in which targeted effects did not resolve, so they should not be used for
  card-level analysis. They remain valid for turn counts and seat effects.

## Further reading

- [CARD_EVALUATION_PLAN.md](CARD_EVALUATION_PLAN.md): the full research log,
  including every run, the harness bug, combo measurements and retractions.
- [`backend/src/simulation/README.md`](../../backend/src/simulation/README.md):
  CLI reference for both harnesses.
- [DECK_EVALUATION_COST_PLAN.md](DECK_EVALUATION_COST_PLAN.md): cost model and
  run design for the LLM validation.
- [AI_CURRENT_STATE.md](ai/AI_CURRENT_STATE.md): the AI pipeline both harnesses
  are built on.
