# Paper & Ink — visual reference captures

Pixel references for the Paper & Ink build, captured from the final design
directions in `../GGLTCG Direction Boards.html`. That mockup is a Claude Design
**canvas export** (a compressed self-extracting bundle of absolutely-positioned
divs), so it renders in a browser but its markup can't be cleanly ported into
the React harness. These screenshots are the practical equivalent: the visual
target to match.

**Source of truth is still the written spec** — `../../DESIGN_SYSTEM_PAPER_AND_INK.md`
(exact tokens, px, radii, positions). These images show *how it reads*; the spec
says *what the numbers are*. Where they disagree, the spec wins (see the tag note
below). Verify live work in `/design.html` (the real GameBoard against fixtures).

| File | Direction | Shows |
|---|---|---|
| `ref-6a-your-turn.png` | 6a | The whole board on your turn: score chips (blue you / purple them, hand pip · cracked-card broken pip · ⚡charge), log strip, `YOU/GEMIKNIGHT · IN PLAY` zone headers, **paper (yours) vs ink (theirs) card materials**, corner brackets, colored cost boxes, Gochi-Hand names, SPD/STR/STA stat rails (gold-buffed / red-damaged / `current/max`), ready ⚡ bolt, slim break slots, hand target pills, gold turn bar + End Turn. |
| `ref-6b-opponent-turn-bar.png` | 6b | The opponent's-turn state: same bottom bar goes **passive purple** — dot + "Gemiknight's Turn · Turn N · waiting…", **no button**; hand keeps its color but loses the gold playable glow. |
| `ref-3c-target-modal.png` | 3c | Target modal: dark panel + gold hairline, action card header, valid targets in **owner materials** (paper/ink), selected target = gold outline + ✓, action-named confirm ("Break Ka"). |

## Spec override to apply (do NOT copy the mockup literally here)

3c renders `YOURS` / `THEIRS` corner tags on target cards. The spec **§7.4
supersedes this**: use the **player's name** (colored `--you` / `--them`) as the
tag instead. Keep "your side / their side / either side" wording only on
hand-card target pills (visible in 6a), where it describes targeting rules, not
identity.
