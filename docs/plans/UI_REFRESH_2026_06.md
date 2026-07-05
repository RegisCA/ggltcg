# UI Refresh — Research & Redesign Plan

**Created**: June 30, 2026
**Updated**: July 4, 2026 — WP-3/WP-4 replaced with the harness-based approach (Claude Code session)
**Source**: Solo AI-vs-AI playtest (Claude playing via Chrome, live production site) + responsive-width check
**Status**: ✅ **COMPLETE (2026-07-05).** WP-1 ✅ · WP-2 ✅ · WP-3 ✅ (design harness, PR #353) · WP-4 Phase 0 ✅ (PRs #354-#355) · Phase 2 ✅ (PRs #356-#369, device-tested, 2026-07-04) · Phase 3 items 1-2 ✅ (log copy #370, victory badges #371) · Phase 3 items 3-6 ✅ **delivered as the "Paper & Ink" design system** (PRs #372-#386, 2026-07-05) — spec in `DESIGN_SYSTEM_PAPER_AND_INK.md`, status + deferred items in `PAPER_AND_INK_PHASE3_HANDOFF.md`. Follow-on UX tweaks are tracked there, not here.

**Context**: Repo is post-audit and stable. Card art was deliberately dropped (physical
game only) — the redesign is function-first, no illustration budget. An earlier pass
using Claude Design produced layouts that looked fine but didn't reflect how the game
is actually played (never played by the designer). This plan fixes that by grounding
redesign decisions in actual play data instead of generic TCG UI conventions.

**Reference point**: benchmark against Board Game Arena's UI, not art-heavy TCGs
(Hearthstone, MTG Arena) — BGA is a multi-game platform with little to no card art and
optimizes for clarity, which is the same constraint GGLTCG is under.

---

## WP-1: Solo AI playthrough (heuristic audit) ✅ COMPLETE

**Method**: Claude signed in as Régis at `https://ggltcg.vercel.app` (explicit permission
given in-session), played "vs AI" mode with a saved deck, through turn 3, at three
viewport widths (1440px desktop, 768px tablet, 390px phone). No code was read for this
pass — findings are purely from playing, matching how a real user experiences it.

### Findings

1. **Duplicate action representation (main friction point).** Every playable card
   appears twice on screen at once: once as a full card in the "Hand" row (art-style
   border, stats grid, effect text) and again as a compact numbered row in the
   "Available Actions" sidebar (name + cost only). Same decision, two visual
   languages, two places to scan before acting. The redesign should pick one
   representation — most likely the hand cards, since clicking a card directly
   already plays it (see finding 6) — and either drop the sidebar list or repurpose
   it as a pure log/summary rather than a second set of buttons.

2. **Break Zone card stacking bug.** Once a player has 2+ broken cards, they render
   absolutely-positioned and overlapping in the Break Zone panel — names and stats
   collide into unreadable text soup (confirmed with 3 stacked cards). Needs a fan-out,
   stacked-with-offset, or list/count+expand treatment. This is a rendering bug, not
   a taste issue, and should be an easy, high-value first fix independent of the
   broader redesign.

3. **No opponent-turn playback.** During the AI's turn, the only feedback is an
   "Opponent is thinking…" spinner in the Game Log; when it resolves, the board jumps
   directly to your next turn's end-state. In one observed AI turn, the opponent played
   a card, fixed a card, attacked twice, and ended — all invisible except as four lines
   of log text. This is the biggest gap for the "eye path" question you wanted to
   study: there's currently no animated path to trace for roughly half the game. Any
   redesign of visual flow should include some form of step-through or animated replay
   of the opponent's turn, even a lightweight one (highlight zones in sequence as log
   lines are read).

4. **Responsive layout breaks, doesn't just degrade.** At 390px (phone) and even
   768px (tablet portrait), the top header row does not reflow: the green turn-status
   banner overlaps the opponent's name/hand/charge text, producing garbled overlapping
   text. This reproduced at both widths tested, so it likely affects most non-desktop
   sessions, not just small phones. This is a functional bug worth fixing ahead of/
   independent of the visual redesign.

5. **Card name truncation.** Card names ellipsize ("Bubble Bloc…", "Hind Leg Kic…")
   even in reasonably wide containers on desktop. Forces the player to already know
   the card or click in to confirm identity — friction against the "read board at a
   glance" goal.

6. **Three visual treatments for the same object.** The deck-builder screen, the
   in-game hand, and the Available Actions sidebar each render "a card" differently
   (full grid card with colored type border → same card style in-hand → dense text
   row in the sidebar). Worth converging on one card component reused everywhere,
   sized differently by context rather than restyled.

7. **What's working — keep these.** Clicking a card plays it immediately with no
   confirmation modal, which keeps turns to the 2-3 clicks you described. The Game
   Log panel with per-actor color coding is a reasonable base for after-the-fact
   traceability and should probably be promoted (see finding 3), not replaced.

**Not yet observed**: mid/late-game board states with cards on both sides
simultaneously, combat resolution UI when both players have blockers, and the
win/loss screen. Worth covering in WP-2 or a second solo pass if needed.

---

## WP-2: Observed live session with Régis ✅ COMPLETE

**Method**: Régis played a full quick-play game vs AI (starting from "who goes first,
what's my opening hand" — his actual default entry point, not deck-select) via Chrome,
granted at view-only tier (Claude could see the screen but not click/type — an
accidental but ideal enforcement of "watch, don't play"). Claude asked 1-2 short
questions at natural breakpoints instead of asking for continuous narration.

### Findings

1. **Confirms WP-1 finding 1, more specifically.** Régis never reads the "Available
   Actions" sidebar to decide what to play — he goes straight to the hand cards' effect
   text, because he's planning 2-3 actions ahead and looking for combos, with cost as a
   secondary check. This is a stronger case for cutting the sidebar's card-choice
   duplication than WP-1 alone suggested — for at least this experienced player it's
   pure dead weight for hand decisions (it may still earn its keep for the "attack"
   option, which has no card-in-hand equivalent).

2. **Charge readout: right info, wrong distance.** When self-checking Charge, Régis
   reads it from the "Available Actions for N Charge" panel header near the hand — not
   the top-of-screen per-player Charge counter — because the top corner is "too far"
   from where his attention already is. He does use the top-right corner for the
   *opponent's* charge/hand count, since there's no closer alternative there. Takeaway:
   don't add a new close-by readout, de-duplicate — the top-left "your charge" counter
   is redundant with the one next to the actions and arguably the wrong one to keep.

3. **Hand order is deliberately unsorted, and that's wanted.** Régis prefers the
   "randomness" of draw order in his 6-card hand and never thought to want it sorted.
   The deck-builder's 2-column sorted grid makes sense there (comparing many cards) but
   should **not** be copied into the in-game hand — different task, different layout.

4. **The opponent-turn recovery path, observed directly (this is the "eye path" data
   you didn't want to write down by hand — got it live instead).** In order:
   noticing cards moved/broken (peripheral) → **Game Log** to reconstruct what
   happened → opponent's hand count + charge spent (top-right, the one place that
   readout is actually needed) → opponent's in-play card (immediate threat) → own
   in-play card (can it answer) → own hand (plan a response, sometimes including
   fixing a broken card). Right now these five checkpoints are spatially scattered
   (log in a right-hand sidebar, board zones stacked in a left column) — a redesign
   should consider laying zones out in this actual sequence rather than the current
   grid-by-zone-type arrangement.

5. **Discoverability gap: self-targeting effects.** Régis forgot that an action card
   (Stomp) could target his *own* board, not just the opponent's — despite it being
   "by design." Nothing on the hand card hints that its effect can go either way;
   that only becomes visible once you're already in the target-select modal.

6. **Target-select modal — good pattern, one gap.** Full-screen dim, the 1-2 valid
   targets shown side by side as mini cards, explicit Confirm/Cancel. Works well and
   Régis reads "yours vs. theirs" correctly from border color (orange/green, matching
   the in-play zone convention) — but that's implicit knowledge with no text label.
   Fine for an experienced player, likely a stumble for a new one.

7. **One-click plays vs. confirm-required plays is an intentional, working split** —
   simple plays are instant, targeted/consequential effects get an explicit confirm
   step. Régis considers this "pretty well balanced." Preserve this distinction; don't
   flatten everything to one interaction pattern in the redesign.

8. **Break Zone stacking bug reconfirmed live**, this time with 5 overlapping broken
   cards in one zone during a real game (not just solo testing) — same bug as WP-1
   finding 2, now with a second, independent repro. Priority stays high.

9. **The post-game "Factual" summary already solves WP-1 finding 3, just too late.**
   It's a turn-by-turn recap including the AI's stated plan per turn, and Régis
   confirmed players actually use it. The redesign opportunity isn't building
   opponent-turn visibility from scratch — it's surfacing a lighter version of this
   existing, working feature *during* play instead of only at game-over.

10. **"Story Mode" is a real asset for the "no card art" constraint.** Same recap,
    reframed as a whimsical narrative using the game's toy characters — genuinely
    charming, on-brand, and gives personality without any illustration budget. Worth
    treating as a design cue (tone, typography, flourish) for the broader refresh, not
    just an easter egg on the end screen.

11. **Debug info leaking into a player-facing screen.** The post-game summary tags
    each AI turn with an "enum" badge (current AI player-version alias — Régis says
    this is intentionally player-facing, a signal that "something changed with the
    AI") and, on one turn, a "Fallback" badge (internal error-handling state, per
    Régis "troubleshooting info basically," not meant for players). The signal behind
    "enum" is fine to keep surfacing; the label and the "Fallback" badge read as raw
    developer terminology and should either be reworded for a player audience or
    moved behind a debug-only view.

12. **Out of scope, flagged for awareness only:** an intermittent turn where the AI
    didn't act, forcing Régis to skip/retry — a known backend/AI issue he's seen
    before and already knows requires local admin-log access to diagnose. Not a UI
    problem; not part of this plan.

---

## WP-3: Synthesis + design harness (replaces low-fi wireframes)

**Approach change (July 4, 2026):** the gray-box wireframe at
`docs/plans/wireframes/board-layout-wp3.html` couldn't answer the real question —
how a layout feels on an actual phone/tablet with real cards in a real game state.
It's kept for the numbered fix-list mapping below but is superseded as a design
tool by the **design-preview harness** (PR #353):

- **`/design.html`** renders the real `GameBoard` against four canned fixture
  states (opening hand, mid-game, break-zone pileup, opponent's turn) — no
  backend, no auth, deep-linkable (`/design.html#midgame`), viewport readout in
  the header. Fixtures live in `frontend/src/fixtures/designFixtures.ts`;
  `gameService` intercepts `fixture-` game IDs (lazy-imported, not in the main
  bundle).
- Every layout candidate for the redesign gets implemented behind the harness
  first, reviewed at 390/768/1280px **and on real devices via Vercel preview
  deploys**, and only then merged.
- The harness already surfaced one sharper version of a WP-2 finding: in the
  target-select modal, when cards on both sides share faction colors (e.g.
  Knight/Ka both red), there is **no ownership cue at all** — WP-2 #6's
  border-color reading only works when factions happen to differ. The
  "yours/theirs" text label is not just a nice-to-have for new players.

**Code root causes identified for the WP-1/WP-2 findings** (from reading the
frontend, July 4 session):

- WP-1 #4 (responsive breakage): `useResponsive` classified ≥360px as "tablet",
  so 390px phones got the 3-column header + 280px-sidebar tablet body. Fixed in
  PR #355 by adding an `isPhone` (<768px) breakpoint and routing phones to the
  stacked header + single-column body. `GameMessages` also ran its own
  `matchMedia(768px)` — breakpoints now have a single source of truth.
- WP-1 #2 (break-zone soup): by-design absolute-position stack at 22–28px
  offsets — inherently unreadable at 2+ cards. Fixed in PR #354 (wrap grid on
  desktop; newest card + "view all" modal in compact columns).
- WP-1 #6 (three card treatments): hand/board/break/target-modal already share
  `CardDisplay`; the real divergences are the ActionPanel text rows (being
  removed anyway) and the deck builder. Cheaper than the finding implied.
- WP-1 #5 (truncation): `CardDisplay` uses fixed px widths (120/165/330), so
  cards never flex into available space. Fix belongs to the Phase-2 layout
  re-architecture (fluid card widths within min/max bounds).
- New (not observable in black-box play): `GameBoard` maintains **three
  hand-written JSX layout trees** (desktop/mobile/tablet). Phase 2 should
  collapse them into one CSS grid with named template areas so reflow is
  by-construction and future changes cost 1× instead of 3×. Also: on <360px
  screens, tapping a card opens a detail modal instead of playing it — a
  per-device interaction fork to treat as a first-class design decision.

Prioritized fix list combining WP-1 + WP-2, grouped by effort:

- **Bugs** (fix regardless of redesign, no design decisions needed): Break Zone card
  stacking — wireframe badge **4** (WP-1 #2, WP-2 #8, confirmed twice independently);
  responsive header overlap at 768px and 390px (WP-1 #4).
- **Information architecture**: collapse the "Available Actions" sidebar's duplicate
  card-choice list, merged into a compact charge/end-turn bar at the hand — wireframe
  badge **3** (WP-1 #1, WP-2 #1-2 — real play data says it's not used for hand
  decisions); de-duplicate the player's own Charge readout, dropped from the top
  header — wireframe badge **1** (WP-2 #2); unify the card component across
  deck-builder/hand/sidebar (WP-1 #6); do **not** auto-sort the hand (WP-2 #3 —
  confirmed unwanted).
- **Flow / layout**: promote the Game Log from a tall side panel to a slim top ticker,
  right after the opponent header — wireframe badge **2** — matching the observed
  post-opponent-turn reading path (log → opponent status → opponent board → own
  board → own hand, WP-2 #4); surface a lightweight, live version of the existing
  post-game "Factual" summary during the opponent's turn instead of only after
  game-over (WP-1 #3, WP-2 #9 — deferred, see below); add a "yours/theirs" text cue
  to the target-select modal alongside the existing color coding (WP-2 #6 — deferred);
  hint on hand cards when an effect can target either side of the board — wireframe
  badge **5** (WP-2 #5).
- **Preserve, don't touch**: one-click instant plays vs. explicit-confirm targeted
  plays (WP-1 #7, WP-2 #7); the Game Log's per-actor color coding; Story Mode's
  narrative tone as a design cue for the whole refresh, given no card art budget
  (WP-2 #10).
- **Polish / copy**: card name truncation (WP-1 #5); reword or hide the "enum"/
  "Fallback" debug badges on the player-facing game summary (WP-2 #11).

Then produce quick wireframes per game phase (draw/main/combat/end) — no art, layout
and hierarchy only — validated against the above before any component code changes.

## WP-4: Implementation (in progress)

Component-by-component, one PR-sized unit per finding where possible (mirrors the
`AUDIT_2026_06_REMEDIATION.md` work-package style). Branch as `feat/ui-<topic>` /
`fix/<topic>`, created as `regisca-bot`, reviewed and merged as `RegisCA`. Every
board-affecting PR is verified in the harness at 390/768/1280px before merge.

**Phase 0 — confirmed bugs (✅ all merged July 4, 2026):**
- PR #353 — design-preview harness (`/design.html`), the tool the rest of the
  refresh iterates in (review fixes: modal scroll clip, bounded fixture AI
  mutation, query-cache pre-seed to kill the cold-load flash)
- PR #354 — break-zone stacking fix (WP-1 #2, WP-2 #8)
- PR #355 — phone-width layout fix: `isPhone` breakpoint, stacked header,
  single-column body, compact `PlayerInfoBar`, unified breakpoints (WP-1 #4)

**Phase 2 — board redesign (in progress, iterate in the harness):**
1. Structural (✅ merged July 4): PR #356 — one CSS grid with named template
   areas replaces GameBoard's three per-device JSX trees; PR #357 — fluid card
   widths via auto-fill grids + 2-line name wrap (killed WP-1 #5 truncation)
2. IA changes from the fix list, one PR each:
   - PR #358 (✅ merged) — badges 1/3: ActionPanel deleted, charge + End Turn
     bar docked at the hand, own charge dropped from the header. Keyboard
     shortcuts 1-9 removed with the list they indexed ('0' End Turn kept) —
     signed off by Régis ("0 gets used, others don't; better use of space")
   - PR #359 (open) — badge 2, the full wireframe-proposed layout: game log
     promoted to a full-width collapsible ticker under the header (latest
     event or AI-thinking spinner inline when collapsed); sidebar removed;
     zones paired by type (opponent in-play | yours, then break zones) per
     the WP-2 #4 eye path; InPlayZone gains horizontal owner headers. Zone
     pairing is a one-block CSS revert if it doesn't survive device review.
     The ticker is the mounting point for future live opponent-turn playback
     (WP-1 #3, WP-2 #9)
   - PR #360 (✅ merged) — action bar pinned sticky to the viewport bottom
     (own Charge had moved there in #358 and scrolled below the fold in real
     games; caught by Régis in prod). Verification lesson: check what's
     visible at scroll 0 at realistic board heights, not just that elements
     render.
   - Device-review batch (July 4, Régis on laptop + iPhone 15, PRs open):
     - PR #361 — board mirrored (your side left, matching the header);
       break zones newest-first
     - PR #362 — content-driven card heights (no art = fixed 225px frames
       were dead space; mid-game desktop board ~1300px → ~854px tall) +
       150px fluid-grid minimum so phone hands render 2-up (~5 cards/screen
       on iPhone 15 vs ~2.5)
     - PR #363 — log expanded by default (choice persisted via
       localStorage), per-actor colors (you=blue, opponent=purple,
       system=gray, left accents), content-fit height up to a cap
   - **iOS Safari "everything tiny" — SOLVED (no code change):** Régis's
     /design.html screenshot showed the harness readout at 786×1390 —
     exactly 2× the iPhone 15's 393pt width — meaning Safari had a per-site
     **Page Zoom of 50%** (aA menu → Page Zoom → reset to 100%). Chrome was
     unaffected because the zoom setting is Safari-per-site.
   - PRs #361/#362/#363 merged (July 4). Follow-up from fresh screenshots:
     PR #364 (open) — log density: slim single-line chips, labeled "TURN N"
     separators, 220px cap. Remaining log verbosity ("Spent 2 Charge for
     Block to tussle Violin") is backend copy → Phase 3 language pass.
   - Régis: layout is "a good path" — less noise, but eyes still bounce and
     desktop still scrolls some; re-judge after #362/#364 settle in play.
   - PR #365 (open, 2026-07-04) — log height frozen during the AI turn
     (per-entry board bounce reported by Régis after #364 settled in play);
     opponent-turn fixture gained a scripted 4-entry log drip, which is
     also the staging ground for live playback below (✅ merged)
   - PR #366 (open, 2026-07-04) — "Yours"/"Theirs" ownership tags on
     target-modal cards (WP-2 #6 + WP-3 harness note: faction colors gave
     no cue when both sides matched); reuses the log's blue/purple
     per-actor colors
   - PR #367 (open, 2026-07-04) — targeting-side hints on playable hand
     cards (badge 5, WP-2 #5): "your side"/"their side"/"either side"
     pill derived from valid-action target_options (current-board
     semantics, no card knowledge in frontend). Found in passing:
     hand renders 1-up (not #362's 2-up) at exactly 390px — 3px grid
     shortfall, pre-existing on main → fixed in PR #368 (open):
     medium card pairs may squeeze to 140px (new squeeze token +
     shared cardGridTracks helper for HandZone/InPlayZone); desktop
     150px floor untouched
   - PR #369 (✅ merged 2026-07-04, device-tested desktop/mobile/tablet) —
     live opponent-turn playback (WP-1 #3, WP-2 #9), shaped per Régis to
     the V4 architecture: backend emits a once-per-turn "strategy"
     play_by_play entry (💭 commentary in the log; VictoryScreen filters
     it, its recap already shows the plan from ai_decision_logs). Spinner
     is phase-scoped: "Opponent is thinking" only until the turn's first
     entry lands, then the streaming entries are the feedback. During the
     opponent's whole turn the log holds the full cap height (220/150px)
     so the board never moves and the playback always has room; re-fits
     when your turn starts. AI games only get the spinner (PvP humans
     aren't "thinking"); PvP turns still get held height + streamed
     entries. Plan chip scrolling up with the drip reviewed and approved
     (pinning idea shelved unless live play changes the verdict).
     Review lesson (Sonnet caught it): the first backend implementation
     was dead code — guard read the plan's current_action index, which
     select_action advances before returning; the harness fixture masked
     it by hardcoding the entry. Fixed with a play_by_play-based guard +
     an HTTP-level regression test. **Harness blind spot to remember:
     fixtures can't validate backend-produced data — pair fixture demos
     with a real E2E game when the backend contributes new entries.**

**Phase 2 status: ✅ complete (2026-07-04).** The 2026-07-04 session queue
(log stability, yours/theirs modal tags #366, hand target hints #367,
live playback #369, plus drive-by phone-hand density fix #368) all
merged and device-verified. Régis on the workflow: harness + Vercel
preview link from the GitHub mobile app before merging is "a game
changer for UX work".

**Open items to re-judge in live play (carry into Phase 3 session):**
- Strategy text quality/length at log-chip width with real Gemini plans —
  first live game after #369 is the first real test; if plans run long,
  the fix is prompt-side (bound selected_strategy length) not CSS.
- Régis's standing "eyes still bounce, desktop still scrolls some" —
  re-assess now that the log holds still during AI turns.
- Early-game opponent turns show a 220px log slot with empty space that
  fills as the playback streams; if it reads as dead air on device, the
  fallback is a grow-only ratchet (small downward shift per entry).

**Session handoff note (2026-07-04, end of second Claude Code session):**
this plan file + the memory entries (`project-ui-refresh-workflow`,
`project-next-session-candidates`) are the continuity mechanism — a fresh
session should read both, `git fetch`, and start Phase 3 below. All work
so far: PRs #353-#369, all bot-authored, harness-verified at 390/768/1280,
final batch device-tested by Régis.

## Phase 3 — design language + whole-experience sweep (✅ complete 2026-07-05)

> **Resolution:** items 3-6 below were delivered as the **Paper & Ink design
> system** (PRs #372-#386): tokens/fonts foundation (#372), whole board +
> target modal (#374), selection primitive + Vitest/RTL test infra (#375,
> #380), every remaining screen (#376-#385), Phase 4 legacy-token cleanup
> (#386). Spec: `DESIGN_SYSTEM_PAPER_AND_INK.md`. Final status and the
> deliberately-deferred list (AdminDataViewer, charge visibility, SVG bolt):
> `PAPER_AND_INK_PHASE3_HANDOFF.md`. This plan file is now historical.

Phase 2 fixed *what's on screen and where*; Phase 3 is *how it reads and
feels*. Layout/gameplay are settled — do not reopen them. Suggested
sequencing (small→large so the language exists before the screens use it).

**Progress:** items 1-2 done (copy polish, #370/#371). Items 3-6 are the
design-language core (typography, iconography, Story-Mode tone, screen
sweep) and are **parked pending the parallel Claude Design system session** —
they should inherit that system rather than invent one here. Resume at item 3
once the design language lands.

1. **Log copy pass (backend `description` strings).** ✅ **DONE — PR #370
   (merged 2026-07-04).** All `add_play_by_play` call sites reshaped to
   subject-verb-object with cost in trailing parens ("Block tussled Violin
   (2 Charge)", "Played Drop, broke Knight (2 Charge)", "Archer used its
   ability on Knight"); rules vocabulary (tussle/Charge/break/fix) kept;
   "Ended turn" + victory line already clean, untouched. The tussle string
   was duplicated (human route inline vs AI executor) — extracted
   `build_tussle_description` so the two can't drift (the drift class behind
   WP-2 #11's stale badge). All harness fixture play-by-play (play-card +
   tussle drip) aligned to the real backend output. Coverage:
   `test_play_by_play_copy.py` (executor + helper) **plus route-level
   assertions in `test_route_coverage_audit.py`** that pin the copy through
   the real FastAPI handlers — the #369 lesson (fixtures can't validate
   backend strings, HTTP route tests can). 405 backend tests pass; front
   tsc+lint clean. Review follow-up (Sonnet, commit `de11f8e`): caught five
   tussle fixture lines still in a legacy `— X broken` shape the backend
   never emits, and removed a redundant target-label branch in
   `execute_tussle` (its success `message` is read by no caller, so it now
   mirrors `description`). Subjective chip-width read is the post-deploy
   real-game check (Vercel previews use prod backend, so a backend copy
   change can't be previewed pre-merge). `selected_strategy` length bound
   still deferred until live plan chips are seen to run long.
2. **Player-facing badge copy (WP-2 #11).** ✅ **DONE — PR #371 (merged
   2026-07-04).** `enum` badge → player-facing AI nickname "🤖 Mastermind"
   (nickname style chosen by Régis; one-line swap in `PLANNER_NICKNAMES`);
   the "changed persona = changed architecture" signal is preserved and the
   raw `enum` stays in the admin viewer via the untouched `plannerModeLabel`
   (new `plannerDisplayName` remaps only the player surface). "⚠️ Fallback"
   → "✨ Improvised" (reword-to-player-language chosen over hide-behind-debug),
   and the raw `fallback_reason` dropped from the player view (still in admin).
   Frontend-only; tsc+lint clean. Visual review needs a completed AI game —
   `/design.html` doesn't mount VictoryScreen yet (see harness gap below),
   so eyeball on the next real game or a follow-up that adds the victory
   fixture.
3. **Typography + iconography.** Currently Lato everywhere + ad-hoc emoji
   (⚡🎯💭📋) that accumulated PR by PR — they work, but they're three
   different visual voices. Decide once: lean into the toybox emoji voice
   (free, on-brand with Story Mode) or swap to a small icon set. Possible
   display font for card names/headers to give the no-art cards some
   character. Iterate in the harness; this is the "design language" PR
   the later screens inherit.
4. **Story-Mode tone as the design cue (WP-2 #10).** The whimsical
   narrator voice is the brand asset. Apply it to chrome copy (empty
   states, victory headline, "Opponent is thinking…" could become
   flavor), not to rules-critical text. Cheap, high-charm.
5. **Screen sweep, one PR each: lobby flow → deck selection → victory
   screen.** Victory screen last — it's already content-strong (Factual +
   Story modes); it mostly needs the Phase-3 language applied. Deck
   builder should reuse the shared CardDisplay/grid tokens from Phase 2
   (WP-1 #6 tail end — it's the last surface with its own card styling).
6. **HowToPlay / first-run** if budget remains: target-hint pills and
   yours/theirs tags (badges 5/#366) now teach mechanics silently —
   check the tutorial text isn't contradicting the new UI.

**Harness gap to close early in Phase 3:** `/design.html` only mounts
`GameBoard`. Items 3-6 need fixtures (or at least deep-linkable variants)
for lobby, deck-select, and victory screens — extend the harness first,
same pattern (canned props, no backend), so the phone-preview-before-merge
loop keeps working. For the victory screen a canned `aiLogs` payload is
also needed (its recap merges ai_decision_logs client-side).

**Process reminders for the Phase-3 session:** fixtures can't validate
backend-produced data (the #369 dead-code lesson) — any PR where the
backend feeds new strings to the UI gets a real E2E game as the gate,
per the standing testing preference. Copy changes ripple into Story
Mode's narrative prompts (`prompts/narrative.py` consumes play_by_play)
— check the narrator still reads well after the log copy pass.

**Preserve, don't touch** (validated by play data): one-click instant plays vs.
explicit-confirm targeted plays; unsorted hand; log's per-actor color coding.
