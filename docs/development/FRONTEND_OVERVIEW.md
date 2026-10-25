# Frontend Overview

The frontend is a React 19 single-page app in `frontend/`, built with Vite and
TypeScript and deployed to Vercel. It holds no game rules. Every legal move,
target list and cost comes from the backend, and the client's job is to
present state clearly, send the player's choice back as card IDs, and pace the
opponent's moves so they can be followed.

| Concern | Choice |
| --- | --- |
| UI | React 19, framer-motion for card movement |
| Server state | TanStack Query 5 over an axios client |
| Styling | Tailwind CSS 4 plus CSS custom properties (the "Paper & Ink" design system) |
| Auth | Google Identity Services (`@react-oauth/google`) exchanged for a backend JWT |
| Observability | Sentry, PostHog, Vercel Analytics and Speed Insights |
| Tests | Vitest, jsdom, Testing Library |

## Entry points

Vite builds three HTML entry points (`vite.config.ts`):

| Page | Source | Purpose |
| --- | --- | --- |
| `index.html` | `src/main.tsx` → `App.tsx` | The game |
| `admin.html` | `src/admin.tsx` → `AdminAuthGate` | Admin dashboard for allowlisted accounts |
| `design.html` | `src/design.tsx` → `pages/DesignPreview.tsx` | Fixture harness: real components against canned states, no backend |

The game's provider stack is `GoogleOAuthProvider` → `AuthProvider` → Sentry
`ErrorBoundary` → `App`, which creates the `QueryClient` (one retry, no refetch
on window focus).

## Screens

There is no router. `App.tsx` holds a `GamePhase` state (`loading`, `menu`,
`lobby-create`, `lobby-join`, `lobby-waiting`, `deck-selection-p1`,
`deck-selection-p2`, `playing`, `game-over`, plus the privacy and terms pages)
and renders one screen per phase. Signed-out players see `LoginPage` instead.

From the menu (`LobbyHome`) a player can:

- **Play vs AI**: pick their deck, then the AI's deck, then play.
- **Quick Play**: start immediately with random decks.
- **Create or join a lobby** for a game against another person, using a short
  game code.
- Open the leaderboard, player stats, card stats or How to Play, which are
  modals over the menu rather than separate phases.

The first screen, `LoadingScreen`, polls `/health` while the free-tier backend
wakes up, with a progress bar calibrated to its typical cold-start time.

## The game board

`GameBoard.tsx` composes the in-game screen:

```text
┌──────────────────────────────┬───────────────────────────────┐
│ PlayerInfoBar (you)          │ PlayerInfoBar (opponent)      │  score chips: hand, broken, Charge
├──────────────────────────────┴───────────────────────────────┤
│ GameMessages                                                 │  play-by-play log, collapsible
├──────────────────────────────┬───────────────────────────────┤
│ InPlayZone (you)             │ InPlayZone (opponent)         │
│ BreakZoneDisplay (you)       │ BreakZoneDisplay (opponent)   │
├──────────────────────────────┴───────────────────────────────┤
│ HandZone                                                     │
├──────────────────────────────────────────────────────────────┤
│ ActionBar                                                    │  End Turn, or "waiting" on their turn
└──────────────────────────────────────────────────────────────┘
```

The grid areas are defined in `index.css` (`.game-board-grid`) and the action
bar stays pinned to the bottom of the screen. Other pieces:

- `CardDisplay` renders a card. `AnimatedStat` flashes a stat when it changes.
- `TargetSelectionModal` opens when an action needs targets or offers an
  alternative cost (Ballaber's "break one of your cards instead of paying").
- `CardDetailModal` shows an enlarged card on phones, where tapping a card
  opens it rather than acting immediately.
- `VictoryScreen` shows the result and can generate a short "Story Mode"
  narrative of the game (`POST /games/narrative`).

## Data flow

### Reading state

`hooks/useGame.ts` wraps the API in TanStack Query hooks keyed by game and
player:

- **Game state** is polled every 2 seconds while the board is mounted. The
  player ID is sent with the request, and the response includes only that
  player's hand (the opponent's is a count).
- **Valid actions** (`GET /games/{id}/valid-actions`) are fetched only on the
  local player's turn and refetched after each action. Each `ValidAction`
  carries the action type, card ID, Charge cost, `target_options`,
  minimum and maximum target counts, and whether an alternative cost exists.
  The board derives which cards are playable, can tussle or can activate an
  ability directly from this list.

### Sending actions

`hooks/useGameActions.ts` posts the player's choice using card instance IDs,
never names. Several cards can share a name across zones, so names are
ambiguous.

```ts
// POST /games/{id}/play-card
{ player_id, card_id, target_card_id?, target_card_ids?, alternative_cost_card_id? }
// POST /games/{id}/tussle
{ player_id, attacker_id, defender_id? }   // no defender = direct attack
```

Each mutation invalidates the game's queries, so the next state and action
list arrive straight away.

### The AI's turn and pacing

When it is the AI's turn, `hooks/useGameFlow.ts` calls
`POST /games/{id}/ai-turn` after a one-second delay. The backend executes one
AI action per request, the new state arrives, and the hook fires again until
the AI ends its turn.

`hooks/usePacedGameState.ts` sits between polling and rendering. On the
opponent's turn it queues incoming snapshots and presents them at least 800 ms
apart, so a fast sequence of moves plays out one at a time. At the turn
handoff it flushes the rest quickly, and at game over it jumps to the final
state. It applies to human opponents too. Duplicate snapshots are dropped using
`game/stateDiff.ts`, a pure function that describes the difference between two
states as events (card moved, stat changed, Charge changed and so on).

Card movement between zones is animated with framer-motion: each card has a
`layoutId` based on its ID, so moving from hand to play or from play to the
break zone animates automatically.

### Multiplayer

The lobby flow is `LobbyCreate` or `LobbyJoin` → `LobbyWaiting`, where both
players pick decks. `hooks/useLobbyPolling.ts` polls the lobby status every 2
seconds until both players have joined and submitted decks, then hands over to
the board. In game there is no separate channel: both clients poll the same
game state, which is simple and fits the free-tier hosting.

## Authentication

1. `LoginPage` gets a Google ID token from Google Identity Services.
2. `POST /auth/google` verifies it on the backend and returns a JWT and the
   user profile.
3. `AuthContext` stores both in `localStorage` and checks the token's expiry on
   load and every 5 minutes.
4. The axios client (`api/client.ts`) attaches the token to every request. On a
   401 it calls `POST /auth/refresh` once, holds concurrent requests until the
   refresh completes, and signs the user out if the refresh fails.

The admin dashboard reuses the same sign-in. `AdminAuthGate` makes one probe
request and shows a sign-in prompt, an access-denied message (account not in
the backend's `ADMIN_EMAILS`), or the dashboard.

## Design system: Paper & Ink

The July 2026 redesign is documented in
[DESIGN_SYSTEM_PAPER_AND_INK.md](../plans/DESIGN_SYSTEM_PAPER_AND_INK.md).
Cards look like hand-drawn paper cards on a dark desk. The local player's cards
are cream paper and the opponent's are dark ink, so ownership is readable at a
glance. That distinction comes from `card.owner` compared with the local player
ID, which `GameBoard` provides through `LocalPlayerContext`.

Tokens live in `src/index.css`:

- **Surfaces and text**: `--desk-*`, `--paper`, `--paper-ink-*`, `--ink`,
  `--ink-*`.
- **Meaning**: `--gold` (your Charge, primary actions), `--you` and `--them`
  (player identity), `--danger`.
- **Crayons**: seven card identity colours. `theme/crayon.ts` maps each card's
  `primary_color` from `cards.csv` to its crayon.
- **Spacing**: `--spacing-component-xs` to `-xl` (8–32 px). Components use these
  rather than hardcoded pixels or Tailwind spacing utilities.
- **Card sizes and touch targets**: `--spacing-card-*`, `--size-touch-target-*`
  (minimum 44 px).
- **Fonts**: Lato for text, Gochi Hand for card names.

Tailwind 4 is configured through the `@theme` block in `index.css`; there is no
`tailwind.config` file. Breakpoints come from one hook, `useResponsive`
(phone under 768 px, desktop over 1024 px). Animations respect
`prefers-reduced-motion`, both in a global CSS rule and through
`useReducedMotion` in animated components.

### The fixture harness

`/design.html#<fixture>` renders real components against canned data: four
board states (opening, midgame, break zones, opponent's turn) and fifteen
screens (deck selection, victory, lobby, login, leaderboard and others). It
needs no backend or account, so any Vercel preview deploy can be checked on a
real phone. Game IDs starting with `fixture-` are answered from
`fixtures/designFixtures.ts`, which is lazy-loaded and stays out of the main
bundle. Components that fetch data accept an override prop (for example
`cardsOverride` on `DeckSelection`) for this purpose. UI changes are reviewed
here at 390, 768 and 1280 px before merging.

## Admin dashboard

`components/admin/AdminApp.tsx` has seven tabs, each in `tabs/`:

| Tab | Shows |
| --- | --- |
| Summary | Counts of users, games, AI decision logs and playbacks |
| AI Logs | Each AI turn's prompt, response and chosen sequence |
| Games | Recent games and their status |
| Playbacks | Turn-by-turn recordings of finished games |
| Users | Registered players, sortable |
| Simulation | Start, pause and resume simulation runs; results matrix and per-game logs |
| Maintenance | Database stats and a manual cleanup trigger |

The selected tab and filters live in the URL hash (`useHashTab`), so a view can
be bookmarked or shared.

## Analytics and error tracking

All of these are disabled when their environment variable is unset.

- **PostHog** (`analytics/posthog.ts`): lobby and game lifecycle events, with
  the Google account ID as the user ID so they join with the backend's
  game-analysis events.
- **Sentry**: production builds only, with an error boundary around the app.
- **Vercel Analytics and Speed Insights**: page views and Core Web Vitals.

## Tests

`npm test` runs 26 Vitest files (about 170 tests) in jsdom. They cover the
pacing hook, the state diff, the target modal, the break zone, the lobby, the
victory screen, the admin dashboard and its API clients, among others. CI runs
lint, type-check and build, then the tests, on every pull request.

The main gaps are `GameBoard` itself and the game hooks (`useGameFlow`,
`useGameActions`, `useLobbyPolling`), which are exercised manually through the
fixture harness and real games.

## Running locally

```bash
cd frontend
npm install
cp .env.example .env.local   # set VITE_GOOGLE_CLIENT_ID
npm run dev                  # http://localhost:5173
```

`VITE_API_URL` defaults to `http://localhost:8000`. See the
[README](../../README.md#run-it-locally) for the backend, and
[DEPLOYMENT.md](../deployment/DEPLOYMENT.md) for every environment variable.

## Further reading

- [ARCHITECTURE.md](ARCHITECTURE.md): the whole system, backend included.
- [AUTH_IMPLEMENTATION.md](AUTH_IMPLEMENTATION.md): the authentication design.
- [MULTIPLAYER_LOBBY_IMPLEMENTATION.md](MULTIPLAYER_LOBBY_IMPLEMENTATION.md):
  the lobby protocol.
- [UI_REFRESH_2026_06.md](../plans/UI_REFRESH_2026_06.md): how the redesign was
  planned and delivered.
