# Paper & Ink — Implementation Plan

**Created**: July 5, 2026
**Spec**: `docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md` (the source of truth — every task
below cites a `§`)
**Predecessor**: `docs/plans/UI_REFRESH_2026_06.md` — Phase 2 (layout/gameplay) is
**settled; do not reopen it**. This plan is Phase 3's design-language core (its items 3–6),
now inheriting a real system instead of inventing one.
**Goal**: apply the Paper & Ink visual language to every frontend component and close the
UI refresh.

## How this is executed (tool/model split)

- **Foundation (Phase F) is built by Opus** in one careful PR, because every downstream
  task depends on the tokens/fonts/crayon map — a mistake there cascades into every
  component. It is a branch PR, so nothing deploys until merge.
- **Everything after F fans out to Sonnet agents**, one PR-sized component slice each,
  against the *settled* foundation and the *settled* `CardDisplay`. Each Sonnet task is a
  self-contained brief: the exact `§` of the spec, the harness reference state to match,
  and the one component file it owns.
- **Verification loop is unchanged** (WP-4): harness at 390/768/1280px, then Vercel
  preview link checked on real device before merge. PRs where the **backend feeds new
  strings** to the UI additionally get a real E2E game (the #369 dead-code lesson —
  fixtures can't validate backend-produced data).
- **PR hygiene**: bot-authored (`regisca-bot`), reviewed/merged as `RegisCA`, branch
  `feat/ui-<topic>`. Never push to `main` directly (auto-deploys).

## Blast-radius facts (measured July 5, grounds the sequencing)

- Legacy Tailwind tokens (`--color-ggltcg-*`, `text-primary/secondary/muted`) are
  referenced by only **~5 files**. Most component color is **hardcoded hex inline**
  (e.g. `CardDisplay.tsx:89` `card.primary_color || '#C74444'`). So the migration is
  "replace inline hex with tokens, per component" — not a risky global find/replace.
- **Additive token strategy**: Phase F *adds* the Paper & Ink tokens alongside the legacy
  ones (does not delete them). Each component PR migrates its file onto the new tokens.
  A final cleanup PR (Phase 4) removes the legacy tokens once nothing references them.
  This keeps every intermediate merge deployable.
- `CardDisplay` is imported by **5 components** — it is the atom; it lands right after F
  and blocks every card-rendering zone.
- Backend `primary_color` has **10 distinct values** →
  `#C74444 #CC5500 #8B5FA8 #4A0E4E #87CEEB #FFB6C1 #d8c7fa #e612d0 #eb9113 #ffeb99`.
  The crayon map (§4, 7 crayons) is a nearest-color snap over these — deterministic,
  unit-testable.
- Harness entry is `frontend/src/design.tsx` + `frontend/src/fixtures/designFixtures.ts`,
  built as `design.html` (`vite.config.ts`). It currently mounts **only `GameBoard`**.

---

## Phase F — Foundation (Opus, 1 PR) — `feat/ui-paper-ink-foundation`

Load-bearing. No visual component changes here beyond wiring; the point is that after F,
a Sonnet agent can build any component purely from tokens + helpers.

1. **Tokens (§2).** Add the Paper & Ink surface / semantic / crayon tokens to
   `index.css` `@theme` (and `:root` as needed). **Keep the spacing scale.** Do **not**
   delete legacy `--color-ggltcg-*` / `--color-game-*` yet.
2. **Fonts (§3).** Add **Gochi Hand** and **Lato weight 900** to
   `frontend/index.html` Google Fonts link (currently Lato 400/700 only). Add a
   `--font-card-name: 'Gochi Hand', cursive` token. Note Bangers retirement (nothing
   loads it today — confirm and record).
3. **Crayon map helper.** New `frontend/src/theme/crayon.ts`:
   `crayonForColor(primary_color: string): string` — nearest-crayon snap over the §4 set,
   plus `MaterialForOwner` helpers deriving cream/ink surface + text tokens from
   `card.owner` vs the local player id (**owner, never controller** — §1). Ship with a
   unit test covering all 10 backend values → expected crayon.
4. **Fixture correctness (§10 last row).** Fix `designFixtures.ts` so each player has
   **exactly 6 cards** (mid-game fixture currently implies 7); this is the win-condition
   denominator and the score-chip source. Keeps existing fixture ids/deep-links.
5. **`prefers-reduced-motion` scaffolding (§9).** Add the media-query block that later
   phases hook the glow/pulse transitions into.

**Exit check**: harness renders unchanged (tokens additive), crayon unit test green,
`tsc`+lint clean, 6-card fixtures verified at all three widths.

## Phase H — Harness reference states (Opus or first Sonnet, 1 PR) — `feat/ui-harness-references`

**Dependency**: needs the mockup source. Drop `GGLTCG Direction Boards.dc.html` where it
can be read (e.g. `docs/plans/wireframes/`); I port **6a / 6b / 3c** into `/design.html`
as static, deep-linkable reference panes (`/design.html#ref-6a`) so every subsequent
Sonnet agent diffs its live component against the target on the same screen. If the file
can't be produced, fall back to building the references from the written spec.

Also stubs the **later-phase harness gap**: deep-linkable fixtures for VictoryScreen
(needs a canned `aiLogs` payload), lobby, and deck-select — so Phase 3 screens keep the
phone-preview-before-merge loop. These can be added lazily when each screen phase starts.

---

## Phase 1 — CardDisplay, the atom (Sonnet, 1 PR) — `feat/ui-card-anatomy`

Rebuild `CardDisplay.tsx` to the new anatomy (**§4**): paper/ink face from
`card.owner` via the material helper; identity crayon from `crayonForColor`; corner
brackets, cost box, Gochi-Hand name, left stat rail (Toys), effect box, ready bolt,
target pill; shadows per §4; states per §6 (playable glow, selected outline+✓, broken
stamp+grayscale, disabled opacity). Verify in the harness (GameBoard already renders it)
against `#ref-6a`/`#ref-6b` and the target-modal card in `#ref-3c`. **Blocks all of
Phase 2.**

## Phase 2 — Board surfaces (Sonnet) — depends on Phase 1

Each is one PR against the settled card. **Sequence the three that touch
`GameBoard.tsx`/the grid** to avoid merge collisions; the rest are self-contained and can
run in parallel.

| # | Task | Spec | Owns | Notes |
|---|---|---|---|---|
| 2a | **Score chip** — `PlayerInfoBar` → §7.1 chip (name, hand pip, cracked-card broken pip, ⚡). Delete the old "Régis N hand" header line. | §7.1, §10 | `PlayerInfoBar.tsx` + GameBoard header slot | *touches GameBoard* |
| 2b | **Turn bar** — `ActionBar` → §7.2 (gold "Your Turn · N" + End Turn / passive purple waiting strip). Absorbs the turn indicator; charge already moved here. | §7.2, §10 | `ActionBar.tsx` | *touches GameBoard bottom* |
| 2c | **Board layout pass** — apply §5 surfaces (desk gradient, zone headers = dot + `NAME · IN PLAY`), reconcile with 2a/2b. | §5, §10 | `GameBoard.tsx`, `InPlayZone.tsx`, `index.css` grid | *do after 2a+2b* |
| 2d | **Break zone** — §7.3 slim dashed slot, owner-material name, `+n · view`. | §7.3 | `BreakZoneDisplay.tsx` | parallel-safe |
| 2e | **Log strip** — §5.2 paper surface, colored actor tick. | §5.2, §8 | `GameMessages.tsx` | parallel-safe; keep per-actor colors |
| 2f | **Target modal** — §7.4 dark panel, owner-material cards, **player-name tags** (replace YOURS/THEIRS), "Break Ka" confirm. | §7.4 | `TargetSelectionModal.tsx` | parallel-safe; player-name tags supersede #366's Yours/Theirs |

## Phase 3 — Screen sweep (Sonnet) — one PR each

Apply tokens + Gochi-Hand headers + iconography (§8) + Story-Mode tone (Phase-3 item 4)
to the non-board surfaces. Each needs its harness fixture from Phase H.

- **DeckSelection** — reuse the shared `CardDisplay`/grid tokens (WP-1 #6 tail: last
  surface with its own card styling).
- **VictoryScreen** — content-strong already; mostly apply the language (§8; keep the
  #371 nickname/Improvised copy).
- **Lobby flow** (`LobbyHome/Create/Join/Waiting` + `lobby/*`), **LoginPage**,
  **Leaderboard**, **LoadingScreen**, **UserMenu**, **HowToPlay** — tokens + iconography;
  check HowToPlay copy doesn't contradict the new target-hint/ownership cues.

## Phase 4 — Cleanup (Sonnet, 1 PR) — `chore/ui-token-cleanup`

Remove legacy `--color-ggltcg-*` / `--color-game-*` tokens and stray `text-primary`
classes once grep shows zero references; strip one-off emoji not in §8 (💭📋); confirm
Bangers fully gone. `tsc`+lint clean; harness + one real game as the final gate.

---

## Dependency graph

```
F (Opus) ── H (references) ── 1 CardDisplay ──┬─ 2a score chip ─┐
                                              ├─ 2b turn bar ───┤─ 2c layout ─→ Phase 3 screens ─→ Phase 4 cleanup
                                              ├─ 2d break zone  │
                                              ├─ 2e log strip   │
                                              └─ 2f target modal┘
```

## Open decisions carried in (not blockers)

- **Iconography voice (Phase-3 item 3 / §8):** keep toybox emoji vs. single-color SVG set.
  Spec leans "⚡ → gold SVG bolt when convenient"; decide during 2e/2f, apply in Phase 4.
- **Gochi Hand at small sizes (§3):** if too casual on stat-size text, fall back to
  Shantell Sans — a one-token swap in Phase F, judged during Phase 1 on device.
