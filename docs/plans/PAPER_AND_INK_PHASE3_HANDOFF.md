# Paper & Ink — Phase 3 Handoff

**Created:** July 5, 2026. Written to kick-start a fresh session that finishes the
Paper & Ink UI refresh (Phase 3 screens + Phase 4 cleanup) and brings it to a close.

This session got the board + modal done but took too many rounds because of
avoidable process mistakes. Read the **Process rules** section before writing any
code — they are the point of this handoff, not boilerplate.

---

## 0. Read these first, in order

1. `docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md` — the spec (source of truth; every
   token/px/rule is here, cited as `§`).
2. `docs/plans/DESIGN_SYSTEM_IMPLEMENTATION.md` — the phased plan.
3. `docs/plans/wireframes/direction-boards.readable.html` — the **readable** design
   (the mockup unescaped; open/grep it directly for exact values). The raw
   `GGLTCG Direction Boards.html` is a Claude Design canvas export — do NOT try to
   parse or "port" it; read the `.readable.html` instead.
4. This file.

Then: `git fetch`, `gh pr view 374`, and check out the branch (below).

---

## 1. Current state (as of this handoff)

- **Merged to `main`:** PR #372 — foundation (Paper & Ink tokens in `index.css`
  `:root`, Gochi Hand + Lato 900 fonts, `src/theme/crayon.ts` = crayon map +
  owner→material helpers, 6-cards-per-player fixtures).
- **On the branch (NOT merged):** `feat/ui-card-anatomy` → **draft PR #374**
  (`https://github.com/RegisCA/ggltcg/pull/374`). This is the **whole-board branch**:
  the entire game board + target modal, redesigned and reviewed over several rounds.
  Commits: Phase 1 (CardDisplay §4) → Phase 2 (all board surfaces) → review rounds
  1–4 → target-modal height fix.
- **Verified** in `/design.html` at 390/768/1280 across 6a (your turn), 6b
  (opponent turn), 3c (target modal), including the Ballaber alt-cost flow. Régis
  did 5 device passes; all his findings are addressed and on the branch.
- **NOT started:** Phase 3 screens, Phase 4 legacy-token cleanup.

**The board branch is essentially done pending Régis's final sign-off + merge.**
Do not re-open board/modal design; only fix if Régis flags something.

### Files changed on the branch
`ActionBar, AnimatedStat, BreakZoneDisplay, CardDisplay, GameBoard, GameMessages,
HandZone, InPlayZone, PlayerInfoBar, TargetSelectionModal, ui/Modal` +
`contexts/LocalPlayerContext.ts`, `theme/crayon.ts`, `index.css`.

---

## 2. Process rules (the hard-won lessons — do not skip)

This session burned Régis's time and trust by repeatedly claiming things were done
without proving them. Internalize these:

1. **"Verified" means you looked at the specific thing, on the RIGHT screen, at the
   RIGHT width, next to the design — and measured it.** Not "it compiles", not "it
   renders", not "it should match". Twice this session a claim of "matches" was
   wrong; once the *wrong screen* was measured entirely (board hand vs the modal).
   If you haven't done the side-by-side, say so explicitly — never round up.

2. **The division of labor: Régis reviews DESIGN; you own IMPLEMENTATION correctness.**
   Every round where he had to catch an implementation bug (clipped highlight,
   unequal heights, leftover selection, wrong label color) is a failure on your
   side. Before showing him anything, self-check: heights equal? colors right?
   states (selected/hover/disabled/broken) correct? layering/clipping OK at the
   edges? Measure with `getComputedStyle` / `getBoundingClientRect`, don't eyeball.

3. **No fabricated limitations.** "The mockup can't be ported" was false — the
   markup was readable in the file the whole time. If something seems blocked,
   dig (decompress, unescape, read the file) before declaring it impossible.

4. **Whole-screen, not fragments.** `main` auto-deploys to prod. Never merge a
   half-migrated screen. Build a complete, coherent screen, validate it whole
   against the design, and only then is it merge-ready. That's why the board is
   one branch, not seven PRs.

5. **Measure precise things; don't trust screenshots for pixels.** Use
   `preview_inspect` / `preview_eval(getComputedStyle|getBoundingClientRect)` for
   colors, sizes, heights. The preview screenshot has a 2× canvas artifact (a navy
   strip on the right at narrow widths) — it is NOT a layout bug.

6. **Harness blind spots:** framer-motion `whileHover`/`whileTap` can't be triggered
   by synthetic pointer events (can't validate hover in automation — reason about
   it or test on real hover). Fixtures can't validate backend-produced data.

---

## 3. The verification loop (unchanged, use it every time)

1. `preview_start` the `frontend` launch config → `/design.html#<fixture>`.
2. `preview_resize` to 390, then 768, then 1280 (and 1440 if reproducing a Régis
   screenshot).
3. `preview_console_logs level:error` — the only expected errors are `[GSI_LOGGER]
   FedCM` (Google auth in the backend-less harness); anything else is yours.
4. Measure/inspect the specific element; screenshot for the overall read.
5. `npx tsc -b` + `npm run lint` (ignore the 3 pre-existing `.vite/deps/axios.js`
   warnings) + `npm run build` before committing.
6. Commit as `regisca-bot`, push, keep PR draft until the screen is whole.
   Switch back to `RegisCA` after. (Per CLAUDE.md: PRs via `gh` as the bot.)

---

## 3.5 PREREQUISITE before any Phase 3 screen — consolidate selection + stand up frontend tests

Decided with Régis (2026-07-05). Do this **first**, as one focused PR.

**Why:** the target modal has three near-duplicate selection handlers
(`toggleTarget` / `selectCardTarget` / `selectAlternativeCostCard`) that behave
differently (single-select toggles-with-deselect-first in the grid, but replaces in
the alt-cost and direct-attack paths) — see the Active Issue in
`docs/development/KNOWN_ISSUES.md`. This is a *behavioral* inconsistency that
visual/harness review structurally can't catch, so it kept landing on Régis (this
and the round-4 "Cancel leaves the card selected" bug are the same class). The
frontend has **no test runner at all** (flagged in Phase F), so nothing pins
interaction behavior.

**Do both, together:**
1. **One selection primitive.** Replace the three handlers with a single function/
   hook parameterized by `maxTargets`: **replace** the selection when
   `maxTargets === 1`, **toggle up to max** otherwise. Use it for the target grid,
   the direct-attack path, and the alt-cost break list.
2. **Frontend test runner + interaction tests.** Add **Vitest + React Testing
   Library** (`npm test`), wire it into `ci.yml` (currently frontend = lint + tsc +
   build only), and write component interaction tests that pin: single-select
   replaces on clicking a different card; multi-select toggles up to max; **Cancel/
   close clears the selection** (round-4 bug); disabled cards aren't clickable;
   keyboard (Enter/Space/Esc). These tests would have caught both bugs before Régis.

**Sequencing / PR boundary (important):** the modal being consolidated + tested
lives on the **unmerged** board branch `feat/ui-card-anatomy` (#374). So 1+2 can
only be a clean standalone PR **after #374 merges to `main`** — off `main` today
you'd be refactoring the *old* modal and hit conflicts. Order:
**#374 board merges → this 1+2 PR off `main` → Phase 3 screens.** (The test-runner
infra alone could be a tiny separate PR anytime, but keep 1+2 together per Régis.)
This also establishes the test runner that later Phase 3 screens should use.

---

## 4. Phase 3 plan — screens

These screens have **no Paper & Ink mockup** (6a/6b/3c only cover the board +
target modal). So Phase 3 = *apply the established language*, not match a picture.
Régis endorsed this and the harness investment. Reuse the shared primitives:
`CardDisplay`, the `:root` tokens (`--paper/--ink/--gold/--you/--them/--danger`,
crayons), `crayonForColor` / `materialFor` / `useLocalPlayerId`, Gochi-Hand headers
(`--font-card-name`), the score-chip / zone-header / turn-bar patterns from the
board.

**Step 0 — extend the harness (do this first).** `/design.html` (`src/design.tsx` +
`src/fixtures/designFixtures.ts`) currently only mounts `GameBoard`. Add
deep-linkable fixtures/routes for each screen so the preview-review loop keeps
working. VictoryScreen also needs a canned `aiLogs` payload (its recap merges
`ai_decision_logs` client-side).

**Screens, in order (one coherent PR each, or fold into the board branch — ask
Régis which he prefers before starting):**
1. **Deck selection** (`DeckSelection.tsx`) — reuses `CardDisplay` + grid tokens
   most directly; it's the last surface with its own card styling (WP-1 #6 tail).
2. **Victory screen** (`VictoryScreen.tsx`) — content-strong already; apply the
   language (§8). Keep the #371 nickname / "Improvised" copy.
3. **Lobby flow** (`LobbyHome/Create/Join/Waiting` + `components/lobby/*`),
   **LoginPage**, **Leaderboard**, **LoadingScreen**, **UserMenu**.
4. **HowToPlay** — apply tokens; check its copy doesn't contradict the new
   target-hint / ownership cues.

**Régis's review cadence (works well — keep it):** build a screen whole → verify
yourself in the harness at 390/768/1280 → he reviews the Vercel preview on
desktop + phone → he flags DESIGN issues → you fix. Do NOT bring him fragments.

**Phase 4 — cleanup (last):** once every component is on the new tokens, remove the
legacy `--color-ggltcg-*` / `--color-game-*` tokens from `index.css @theme` and any
stray `text-primary/secondary/muted` classes (grep first). Confirm Bangers is gone.
Remove one-off emoji not in §8.

---

## 5. Technical reference (key patterns already built — reuse, don't reinvent)

- **Tokens** live in `index.css` `:root` (NOT `@theme` — Tailwind v4 prunes
  unreferenced `@theme` vars; these are consumed via `var()` in inline styles).
- **`src/theme/crayon.ts`:** `crayonForColor(primary_color)` (curated table for the
  10 real card colors + nearest-color fallback), `materialFor(isOwn)` /
  `materialForOwner`, `costNumeralColor(crayon, isOwn)` (luminance-based flip).
- **`src/contexts/LocalPlayerContext.ts`:** `LocalPlayerProvider` (GameBoard
  provides `humanPlayerId`; crosses portals so the modal gets it) +
  `useLocalPlayerId()`. Card material = owner vs local id (`card.owner`, NEVER
  `controller` — §1). Defaults to "own" outside a game (deck builder galleries).
- **`CardDisplay` props of note:** `size` (small/medium/large), `fluid`,
  `isSelected` (gold outline + ✓; no hover-scale when selected),
  `isHighlighted`→ready bolt/glow, `targetHint`, and **`minHeight`** (override to
  equalize Toy/Action heights across separate grids — see below).
- **Target-modal height gotcha (already solved, understand it):** cards grouped by
  zone live in separate per-zone grids; `grid-auto-rows:1fr` equalizes within a
  grid but not across. A medium Toy is **rail-dominated (~131px)** regardless of
  effect length. `TargetSelectionModal` passes a shared `minHeight` (134) to all
  cards when a Toy is present. If you build another multi-grid card layout, reuse
  this pattern. (Bulletproof version = measure the tallest card at runtime; the
  134 floor assumes no toy exceeds ~6 wrapped effect lines — none currently do.)
- **Turn/identity colors:** you = `--you` (blue), opponent = `--them` (purple),
  everywhere (names, zone dots, log ticks, turn bar). `--gold` = charge / action /
  End Turn button only — NOT identity.
- **Backend/API:** always card **IDs**, never names. Spacing via CSS custom props.

---

## 6. Quick-start commands

```bash
git fetch origin
git checkout feat/ui-card-anatomy   # the whole-board branch (draft #374)
# ... or branch off it / main for Phase 3 per Régis's call
cd frontend && npm run dev          # /design.html to review
# gate before commit:
npx tsc -b && npm run lint && npm run build
# PRs as the bot:
gh auth switch -u regisca-bot   # create/push;  gh auth switch -u RegisCA after
```

Memory to load: `feedback-validate-before-claiming`, `project-ui-refresh-workflow`
(has the whole-board rule + Paper & Ink context).
