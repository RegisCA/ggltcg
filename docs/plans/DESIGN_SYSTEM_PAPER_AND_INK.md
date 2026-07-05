# GGLTCG Design System — "Paper & Ink"

Visual refresh spec, July 2026. Successor to the Phase 1–2 UX work in `docs/plans/UI_REFRESH_2026_06.md`.
Reference mockups: `GGLTCG Direction Boards.dc.html` — final direction is **6a** (GameBoard, your turn), **6b** (opponent turn), **3c** (target modal, update tags to player names per §7.4).

## 1. Concept

The digital game inherits the physical game's DNA — white-paper cards with one marker color each, corner brackets, a left stat rail, hand-lettered names, the bear-head cutout logo — used lightly: structure and color logic, not imitation of the drawings. Everything else is a quiet dark tabletop. Clarity first, charm in the details.

Three pillars:

1. **Ownership materials.** A card's surface is bound to its **owner** (`Card.owner`, never `controller`): the local player's cards are always cream paper, the opponent's always dark ink — in play, in the break zone, in targeting modals, everywhere. Stolen cards keep the original owner's material; copies belong to the copier. This replaces most yours/theirs labeling.
2. **Four semantic colors, nothing else.** Gold = charge / can act / your turn. Blue = you. Purple = opponent. Red = broken / danger. Any other color on screen is card identity (§4) or neutral.
3. **One turn concept.** The bottom bar is the single turn control: gold + End Turn button when it's your turn; passive purple "waiting" strip when it isn't. No duplicate indicators.

## 2. Color tokens

### Surfaces
| Token | Value | Use |
|---|---|---|
| `--desk-top` | `#282018` | Board background gradient start |
| `--desk-bottom` | `#211a13` | Board background gradient end |
| `--paper` | `#EFE7D6` | Local player's card face; log strip |
| `--paper-ink-text` | `#2E2921` | Primary text on paper |
| `--paper-muted` | `#5A5347` | Effect text on paper |
| `--paper-faint` | `#8A8071` | Stat labels, metadata on paper |
| `--ink` | `#2E2A24` | Opponent's card face; opponent card backs |
| `--ink-text` | `#EDE8DE` | Primary text on ink and on desk |
| `--ink-muted` | `rgba(237,232,222,.65)` | Effect text on ink |
| `--ink-faint` | `rgba(237,232,222,.45)` | Stat labels on ink |
| `--bar` | `#171209` | Bottom turn bar |

### Semantic
| Token | Value | Use |
|---|---|---|
| `--gold` | `#F2C14E` | Charge, playable glow, your-turn state, active buttons, buffed stats on ink |
| `--gold-on-paper` | `#B08A1F` | Buffed stat numerals on paper (AA) |
| `--you` | `#7EA6E0` | Local player name, side markers |
| `--them` | `#B48EDE` | Opponent name, side markers, opponent-turn state |
| `--danger` | `#E0716B` | Broken pips/counts on dark surfaces |
| `--danger-on-paper` | `#C0392B` | Damaged stat / BROKEN stamp on paper (AA) |

### Crayon set (card identity — no rules meaning)
`#C74444` red · `#D98E1F` orange · `#4C9A57` green · `#4A7BB5` blue · `#8B5FA8` purple · `#D6559C` pink · `#6FA8C9` sky.
Map each card's backend `primary_color` to its nearest crayon. Identity colors appear only as: card frame border, cost box fill, stat-box borders, corner brackets. Never as text color, backgrounds, or state.

## 3. Typography

- **Lato** (400/700/900) — all UI: stats, effect text, labels, buttons. Numerals 900.
- **Gochi Hand** (Google Fonts) — card names only, echoing the hand-lettered physical cards. Never for UI copy, stats, or body text. If it proves too casual at small sizes, fallback candidate: Shantell Sans.
- **Bangers is retired.**
- Labels (zone headers, stat labels): 700–900, uppercase, letter-spacing `.05–.12em`, faint color.
- Minimum sizes at 390px: effect text 10.5px is the floor from the mockups — implement with a scale so it lands ≥12px on larger phones; hit targets ≥44px.

## 4. Card anatomy (Toy & Action share one skeleton)

From the physical card: frame, cost, name, stat rail, effect box, corner brackets.

- **Face**: `--paper` (yours) / `--ink` (theirs), radius 6px, border 2.5px solid [identity crayon].
- **Corner brackets**: top-left + bottom-right, 9×9px, 2px strokes in the identity color.
- **Cost box**: 20×20px square, radius 3px, filled identity color, cost numeral 900 in the face color.
- **Name**: Gochi Hand, ~17px, next to cost box.
- **Stat rail** (Toys only): vertical stack on the left — SPD / STR / STA boxes, 30px wide, 1.5px identity-color border, label 7px faint, value 13px 900. Modified values: buffed → gold (`--gold-on-paper` on paper), damaged/debuffed → danger red; STA shows `current/max` when damaged.
- **Effect text**: right of the stat rail (Toys) or full width (Actions), muted color.
- **Ready bolt** (Toys in play): small ⚡ top-right when the card can act this turn.
- **Target pill** (Actions in hand): bottom-left pill "🎯 your side / their side / either side" — relative semantics, keep wording (§7.4).
- **Shadows**: paper cards `0 3px 0 rgba(0,0,0,.4)` (object on desk). Ink cards: no drop shadow (they read as part of the dark board). Playable cards add glow (§6).

## 5. Board layout (GameBoard, 390px reference)

Top → bottom:
1. **Scoreboard** — two chips side by side (§7.1).
2. **Log strip** — paper surface, latest event one-liner, expandable (`▾ log`). Actor tick colored `--you`/`--them`.
3. **In-play zones** — 2 columns (You | Opponent), zone header = 8px color dot + `NAME · IN PLAY` label. Cards in a `grid-auto-rows:1fr` grid so rows are equal height.
4. **Break zones** — slim dashed slots per player (§7.3).
5. **Your hand** — 2-col grid, equal heights.
6. **Turn bar** — fixed bottom (§7.2).

## 6. States

- **Playable / can act**: gold glow `0 4px 10px rgba(242,193,78,.25)` added to the card shadow. Glow means "you can use this now" — nothing glows on the opponent's turn.
- **Selected (targeting)**: 3px gold outline, offset 2px, plus a gold ✓ badge.
- **Broken**: card keeps its owner material, desaturated (`filter: grayscale(35%)` on paper) with a rotated red `BROKEN` stamp.
- **Disabled/passive**: reduce opacity, never change material.

## 7. Components

### 7.1 Score chip (one per player, side by side under the notch)
`[Name] [hand pip ×n] [broken pip ×n] [⚡n]` — order fixed: hand, broken, charge.
- Container: radius 8px, 1px border + tint of the player color (`rgba(126,166,224,.3)` / `rgba(180,142,222,.28)`).
- **Hand pip**: 11×15px rounded rect in the player's material (cream fill for you, ink fill + faint border for them) + count.
- **Broken pip**: 11×15px card outline in `--danger` with a diagonal crack (45° gradient slash) + count in `--danger`. This is the score — win = all 6 of theirs broken.
- **Charge**: `⚡n` in gold.
Both players get the identical chip; no separate hand-count line anywhere else (the old "Régis 4 hand" header line is deleted).

### 7.2 Turn bar (bottom, fixed)
- **Your turn**: `--bar` background, gold top border, "Your Turn · Turn N" in gold 900 + gold `End Turn` button (radius 6px, `0 3px 0` pressed shadow).
- **Opponent's turn**: same bar, purple accent — pulsing purple dot + "Gemiknight's Turn · Turn N" + "waiting…", **no button**.

### 7.3 Break zone
Slim dashed slot per player: `BREAK` label, latest broken card's name (Gochi Hand, owner-material colors), `+n · view` when stacked; tapping opens the pile. Counts live in the score chips, so the zone stays quiet.

### 7.4 Target modal
Dark panel (`#241E17`, gold hairline border). Target cards render in the **owner's material** — that alone separates yours/theirs even when both decks contain the same card. Corner tag on each target: the **player's name** (colored `--you`/`--them`) — replace the current YOURS/THEIRS wording; keep "your side / their side / either side" only on hand-card target pills, where it describes targeting rules rather than identity. Selected target: gold outline + ✓. Confirm button names the action: "Break Ka".

### 7.5 Opponent hand (if shown outside the score chip)
Face-down mini card backs: ink surface with the bear-head cutout logo in cream. The logo is the only ornament; never invent other decorations.

## 8. Iconography

- **⚡ charge**: keep the emoji short-term; replace with a single-color SVG bolt (gold) when convenient — one visual voice.
- **Broken**: the cracked-card pip (§7.1) everywhere a broken count appears. Never ✕ (reads as "times").
- **🎯 target**: keep on hand pills only.
- **Bear-head logo**: card backs, app chrome, empty states. It is the brand mark; use the cutout style from the physical game.
- Remove 💭📋 and other one-off emoji; anything not listed here should be text.

## 9. Accessibility

- Maintain WCAG AA. Verified pairs: `--paper-ink-text` on `--paper`; `--ink-text` on `--ink`; `#211a13` on `--gold`; `--danger` on `--bar`/desk; use `--gold-on-paper`/`--danger-on-paper` variants for text on paper.
- Ownership is encoded twice (material + name color); state twice (glow + position). Don't rely on color alone for broken (stamp + pip shape).
- `prefers-reduced-motion`: disable the passive-bar pulse and glow transitions.

## 10. Migration map (existing frontend)

| Existing | Change |
|---|---|
| `index.css` tokens | Replace palette with §2; keep spacing scale |
| `CardDisplay.tsx` | New anatomy (§4); material from `card.owner`; identity color from crayon map |
| `GameBoard.tsx` | Layout §5; delete old header player line |
| `PlayerInfoBar.tsx` | Becomes the score chip (§7.1) |
| `ActionBar.tsx` | Becomes the turn bar (§7.2), absorbs turn indicator; charge count moves to score chip |
| Target modal | §7.4 — player-name tags, owner materials |
| `designFixtures.ts` | Fix card totals to 6 per player (mid-game fixture currently implies 7) |
