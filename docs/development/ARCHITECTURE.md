# Architecture

GGLTCG is a two-player card game played in the browser, against an AI opponent
or another person. This document describes how the system fits together: the
rules engine at its centre, the API and persistence around it, the web client,
and the AI and simulation layers built on top of the engine.

- [System overview](#system-overview)
- [Repository layout](#repository-layout)
- [The game engine](#the-game-engine)
- [Card effects](#card-effects)
- [One path for every action](#one-path-for-every-action)
- [API and persistence](#api-and-persistence)
- [Multiplayer and synchronisation](#multiplayer-and-synchronisation)
- [Authentication](#authentication)
- [AI opponent and simulation](#ai-opponent-and-simulation)
- [Operations](#operations)
- [Testing](#testing)
- [Design decisions](#design-decisions)
- [Known limitations](#known-limitations)

## System overview

```text
 Browser (Vercel)                        Backend (Render)                          External
┌──────────────────────┐   HTTPS/JSON   ┌───────────────────────────────────┐
│ React SPA            │ ─────────────► │ FastAPI routers                   │
│  game, lobby, stats  │  poll every 2s │   │                               │
│  admin dashboard     │ ◄───────────── │   ▼                               │     ┌──────────────┐
└──────────────────────┘                │ GameService ── cache + DB I/O ────┼───► │ PostgreSQL   │
                                        │   │                               │     └──────────────┘
                                        │   ▼                               │
                                        │ ActionValidator / ActionExecutor  │
                                        │   │                               │
                                        │   ▼                               │
                                        │ GameEngine ── GameState, effects  │
                                        │   ▲                               │
                                        │   │ same engine, cloned states    │     ┌──────────────┐
                                        │ AI: enumerator + selector ────────┼───► │ Gemini API   │
                                        └───────────────────────────────────┘     └──────────────┘
```

The engine is the single authority on the rules. The browser holds no rules: it
asks the backend which moves are legal, shows them, and sends back the player's
choice. The AI and the simulation harness use the same engine and the same
validation code as a human player, so there is exactly one implementation of the
game.

| Layer | Technology |
| --- | --- |
| Engine and API | Python 3.13, FastAPI, Pydantic |
| Persistence | SQLAlchemy, Alembic; PostgreSQL in production, SQLite locally and in CI |
| Web client | React 19, TypeScript, TanStack Query, Vite, Tailwind CSS 4 |
| AI | Google Gemini via `google-genai`, structured JSON output |
| Hosting | Render (API, database), Vercel (client), both auto-deploying from `main` |

## Repository layout

```text
backend/
  data/cards.csv            card definitions: stats, cost, effect DSL
  src/game_engine/          rules, with no web or database code
    models/                 Card, Player, GameState
    rules/effects/          effect classes and the CSV effect parser
    validation/             ActionValidator, ActionExecutor
    ai/                     enumerator, Gemini selector, execution
    game_engine.py          GameEngine: turns, costs, tussles, breaking
  src/api/                  FastAPI routers, GameService, auth, serialization, DB models
  src/simulation/           AI-vs-AI harnesses (LLM and scripted)
  alembic/                  database migrations
  tests/                    pytest suite
frontend/src/               React app, admin dashboard, design fixture harness
docs/                       rules, architecture, plans, research logs
```

## The game engine

### Rules in brief

Each player brings 6 distinct cards, all of which start in hand; there is no
draw. **Toys** have speed, strength and stamina and stay in play. **Actions**
resolve and go to the break zone. Players spend **Charge** to play cards and to
start tussles: they gain 2 on the first turn of the game and 4 on every later
turn, carry unspent Charge over, and can hold at most 7. In a **tussle** the
faster Toy strikes first (the active player's Toy gets +1 speed), dealing its
strength as damage to the other's stamina. A Toy at 0 stamina is broken. With no
Toys left to defend, a player can be **directly attacked**, which sends a
random card from their hand to the break zone. A player wins when every one of
the opponent's cards is in the break zone. The full rules are in
[QUICK_REFERENCE.md](../rules/QUICK_REFERENCE.md).

### Models

| Class | File | Holds |
| --- | --- | --- |
| `Card` | `models/card.py` | Printed stats and cost, a unique `id`, the effect string, `owner` (never changes), `controller` (changes when a card is stolen), `zone`, current stamina and temporary modifications |
| `Player` | `models/player.py` | Charge (with the cap enforced in `gain_charge`), hand, in-play and break-zone lists, per-turn counters |
| `GameState` | `models/game_state.py` | Both players, turn number, active and first player, winner, play-by-play log, Charge history. Also zone transitions such as `change_control` and `find_card_by_id` |
| `GameEngine` | `game_engine.py` | Rules: turn start and end, card costs, stat calculation, tussle resolution, breaking, state-based checks |

Cards are always looked up by `id`, never by name. Copy can put two cards with
the same name on the board, and a name lookup would pick the wrong one.

Zone changes go through methods (`player.move_card`, `engine._break_card`,
`state.change_control`) rather than attribute assignment, because leaving play
has side effects: damage and modifications reset, a transformed Copy reverts,
and a stolen card returns to its owner's break zone.

### Turn lifecycle

```text
start_turn ──► gain Charge (2 on turn 1, else 4; cap 7)
           ──► start-of-turn triggers
           ──► MAIN: play cards, tussle, activate abilities, in any order
end_turn   ──► finalise Charge tracking ──► switch player ──► turn_number += 1 ──► start_turn
```

`turn_number` advances on every player's turn, so odd turns always belong to
the first player. The first player is chosen at random when a game is created.

After every action the engine runs `check_state_based_actions`, which breaks
any Toy at 0 stamina, fires "when broken" triggers, and checks for a winner.

### Stats and costs are computed, not stored

A card's effective strength is never written onto the card. `get_card_stat`
starts from the printed value and applies every continuous effect currently in
play (Ka's +2 strength for all your cards, for example), then any turn-scoped boosts.
Costs work the same way: `calculate_card_cost` applies every cost modifier in
play, and variable-cost cards such as Copy take their cost from the chosen
target. When a card leaves play, its effects stop applying automatically
because nothing was ever written.

### Randomness

The rules contain one random event: a direct attack picks a random card from
the defender's hand. Everything else is deterministic. The simulation harness
seeds this per game so that every simulated game can be replayed exactly.

## Card effects

Card behaviour is data. Each row of `backend/data/cards.csv` has an `effects`
column in a small DSL, and `EffectFactory` parses it into effect objects:

```text
Ka            stat_boost:strength:2
Sock Serpent  break_target:1:opponent
Archer        cannot_tussle;remove_stamina_ability:1
```

There are 27 effect types in four families: continuous (stat and cost
modifiers, protection), triggered (start of turn, when broken, when another
card is played), play effects (Actions, and Toys' "when played" abilities) and
activated abilities. All 45 cards are expressed this way, including Copy,
Twist and Knight. A new card usually needs a CSV row and nothing else; a new
mechanic needs one effect class and one parser branch.

[EFFECT_SYSTEM_ARCHITECTURE.md](EFFECT_SYSTEM_ARCHITECTURE.md) covers the DSL,
the class hierarchy and where each family hooks into the engine.
[ADDING_NEW_CARDS.md](ADDING_NEW_CARDS.md) is the how-to.

## One path for every action

Two classes sit between callers and the engine:

- **`ActionValidator.get_valid_actions(player_id)`** lists every legal action
  for the active player as `ValidAction` objects: action type, card ID, Charge
  cost, the legal targets (`target_options`), minimum and maximum target
  counts, and any alternative cost. Tussles that would certainly lose are
  filtered out for the AI.
- **`ActionExecutor`** carries out a chosen card play or tussle: it resolves
  target IDs to cards, rejects targets outside the effect's legal set, works
  out the cost, calls the engine and builds the play-by-play description.

The web client renders `ValidAction`s directly, the AI's enumerator searches
over them, and the simulation runner replays through the executor. When a
targeting rule changes, every caller sees the change at once.

### A card play, end to end

```text
POST /games/{id}/play-card  { player_id, card_id, target_card_id }
  routes_actions.play_card
    → GameService.get_game(id)                    cache hit, or load and deserialise from DB
    → check it is player_id's turn
    → ActionExecutor.execute_play_card
        → _handle_targets, _validate_effect_targets
        → engine.calculate_card_cost              depends on the target for variable-cost cards
        → engine.play_card
            → can_play_card, spend Charge
            → Toy: into play, fire "when played" effects
              Action: resolve play effects, move to break zone
            → check_state_based_actions
            → fire "when another card is played" triggers
    → state.add_play_by_play
    → GameService.update_game                     cache + DB upsert; stats and playback if the game ended
  ← ActionResponse { success, message, game_state }
```

## API and persistence

### Routers

| Router | Prefix | Purpose |
| --- | --- | --- |
| games | `/games` | Create a game, quick play, random deck, card list, game state, narrative |
| actions | `/games/{id}` | `play-card`, `tussle`, `end-turn`, `activate-ability`, `valid-actions`, `ai-turn` |
| lobby | `/games/lobby` | Create, join, poll and start a multiplayer game by code |
| auth | `/auth` | Google sign-in, token refresh, profile, saved decks |
| stats | `/stats` | Leaderboards, player and card statistics |
| admin | `/admin` | Read-only views of games, AI logs, playbacks and users |
| simulation | `/admin/simulation` | Start, pause, resume and inspect simulation runs |
| maintenance | `/maintenance` | Database stats and cleanup, for the scheduled job |

`GET /health` reports database status, the applied migration, the deployed
commit and the active AI models. Interactive API docs are at `/docs`.

### Game state storage

`GameService` keeps live games in an in-process cache and writes through to the
database after every action. Each game is a row in `games` holding the full
serialised `GameState` as JSON, plus a few denormalised columns (players,
status, turn, winner) for queries. A game survives a server restart or a
free-tier sleep: the next request loads and deserialises it.

`api/serialization.py` converts between the engine's objects and JSON. Effect
objects are never stored. A card's effect string is the source of truth, and
effects are rebuilt from it on load, including a transformed Copy's borrowed
effects.

| Table | Contents |
| --- | --- |
| `users` | Google accounts, display names, saved decks |
| `games` | One row per game: JSON state plus metadata |
| `game_playback` | Turn-by-turn record of finished games |
| `game_stats`, `player_stats` | Per-game summaries and per-player, per-card aggregates for leaderboards |
| `ai_decision_logs` | Every AI turn's prompt, response and chosen sequence |
| `simulation_runs`, `simulation_games` | LLM simulation results |
| `api_usage_daily` | Daily Gemini request counts for simulation budgets |

Schema changes ship as Alembic migrations (14 so far), applied by the
production start command before the server starts. `database.py` configures
connection pooling for PostgreSQL and skips it for SQLite.

## Multiplayer and synchronisation

A player creates a lobby and gets a 6-character code; the second player joins
with it; both pick decks; the server creates the game when both decks are in.
During play, both clients poll game state every 2 seconds. There are no
websockets. Turns in this game take seconds to minutes and nothing happens
between turns, so polling costs little and fits a free-tier host that sleeps
and cannot hold long-lived connections.

The AI's turn is driven the same way. The client calls `POST /ai-turn`, the
server executes one AI action and returns, and the client calls again until
the AI ends its turn. The client paces the resulting snapshots so each move is
visible (see [FRONTEND_OVERVIEW.md](FRONTEND_OVERVIEW.md#the-ais-turn-and-pacing)).

## Authentication

The client gets a Google ID token from Google Identity Services and posts it
to `/auth/google`. The backend verifies it against the OAuth client ID,
creates or loads the user, and returns its own JWT (HS256, 24-hour lifetime),
which the client sends as a bearer token and refreshes on expiry. Admin routes
additionally require the token's email to be in the `ADMIN_EMAILS` allowlist;
an empty allowlist admits nobody. Auth endpoints are rate-limited per IP.
Details are in [AUTH_IMPLEMENTATION.md](AUTH_IMPLEMENTATION.md).

## AI opponent and simulation

The AI never generates moves. For each turn the enumerator searches the real
action space on cloned game states, using `ActionValidator` and
`ActionExecutor`, and ranks the legal sequences it finds. One Gemini call
picks one of the top 12, and the server executes it step by step. The model
cannot make an illegal move because it only ever sees legal ones. See
[AI_CURRENT_STATE.md](ai/AI_CURRENT_STATE.md).

Because only the selection step uses a model, the same pipeline runs without
one. The simulation harness swaps the Gemini call for a local policy and plays
tens of thousands of games on a laptop to measure card and deck strength. A
2,000-game Gemini run confirmed that the scripted results predict LLM play.
See [SIMULATION_SYSTEM.md](SIMULATION_SYSTEM.md).

## Operations

- **Deploys**: merging to `main` deploys the API to Render and the client to
  Vercel. See [DEPLOYMENT.md](../deployment/DEPLOYMENT.md).
- **Health**: `/health` shows the deployed commit, so a merge can be confirmed
  live without playing a game.
- **Errors**: Sentry on both sides, enabled by DSN environment variables.
- **Analytics**: PostHog. The client sends lobby and game lifecycle events; the
  server sends one game-analysis event per human player at game end, joined on
  the Google account ID.
- **Cleanup**: a daily GitHub Actions job calls `/maintenance/cleanup` to mark
  abandoned games and purge old logs, keeping the free-tier database small.
- **AI debugging**: the admin dashboard shows each AI decision with its full
  prompt and response, and every finished game's playback.

## Testing

- **Backend**: 60 pytest modules covering the engine and every card effect
  (one module per card batch), serialization round-trips, card-data integrity
  (every effect string in `cards.csv` must parse), auth, admin gating, the AI
  enumerator and planner, and the simulation harnesses. CI runs them against
  in-memory SQLite with a dummy API key, so no test depends on Gemini or a real
  database.
- **Frontend**: Vitest and Testing Library for components, hooks, the state
  diff and the admin client.
- **CI** (`.github/workflows/ci.yml`): backend tests, frontend lint, type-check,
  build and tests on every pull request.

Engine tests must respect turn parity: turn 2 belongs to the second player.
A fixture that sets `turn_number=2` with the first player active describes a
state the game can never reach.

## Design decisions

**Rules live only on the server.** The client never decides what is legal.
This costs a round trip per action but removes a whole class of client/server
disagreement, and it is what lets the AI, the simulations and the web client
share one implementation.

**Card effects are data.** Early cards were Python classes, one per card. The
move to a CSV DSL with generic, parameterised effect classes means most new
cards are a spreadsheet row, the game's designer can read and propose them, and
an integrity test checks every row in CI.

**The AI chooses; the engine enumerates.** Earlier versions asked the model to
produce move sequences, and it kept producing illegal ones (wrong Charge sums,
impossible targets). Moving sequence generation into the engine made illegal
moves impossible by construction and cut the AI to one model call per turn.

**Game state is a JSON document.** The game state is a deeply nested object
that is always read and written whole, so it is stored as one document per
game, with a few columns pulled out for queries. Analytics that need structure
use the playback and stats tables instead.

**Polling instead of websockets.** Explained under
[Multiplayer and synchronisation](#multiplayer-and-synchronisation).

## Known limitations

- **Two actions bypass `ActionExecutor`.** The human `tussle` route calls the
  engine directly, and activated abilities (Archer) are applied inline in their
  route, with the same logic repeated in the AI route and the enumerator.
  Folding both into the executor would complete the single-path design.
- **The engine imports from the API package** (`ValidAction` from
  `api.schemas`, database models for the simulation rate limiter). The
  dependency should point the other way.
- **Effects are re-parsed on every lookup.** `EffectRegistry.get_effects`
  rebuilds effect objects from the CSV string each time it is called, including
  inside stat calculations. This is fast enough at this scale, and keeps
  effects stateless, but it is the first thing to cache if enumeration ever
  needs to go deeper.
- **Single-process cache.** `GameService`'s cache assumes one backend process,
  which matches the free-tier deployment. Scaling out would mean reading
  through to the database on every request or adding a shared cache.

Resolved issues and their history are in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
