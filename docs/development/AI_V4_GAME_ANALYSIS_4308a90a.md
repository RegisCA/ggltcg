# AI V4 Game Analysis: 4308a90a-f14f-4273-98b2-214c47e09ce6

**Date**: Jan 3, 2026
**Game ID**: `4308a90a-f14f-4273-98b2-214c47e09ce6`
**AI Version**: 4
**Opponent**: Human

## Summary
This game exhibits a specific type of **CC Hallucination** where the AI correctly calculates potential CC in early turns but fails in later turns, possibly due to "Header Pollution" or arithmetic errors involving potential CC sources.

## Turn Analysis

### Turn 1: Correct Potential CC Calculation
- **State**: 2 CC available.
- **Hand**: Contains `Surge` (+1 CC).
- **Prompt Header**: `## CC: 2 (Surge adds +1, Rush adds +2 when played)`
- **AI Claim**: 3 CC.
- **Analysis**: The AI correctly identified that playing Surge would result in 3 available CC.
- **Verdict**: ✅ Correct Behavior (Potential CC recognized).

### Turn 3: Correct Base CC
- **State**: 3 CC available.
- **Hand**: No CC modifiers.
- **AI Claim**: 3 CC.
- **Verdict**: ✅ Correct Behavior.

### Turn 5: CC Hallucination (+2 Unaccounted)
- **State**: 6 CC available.
- **Hand**: Contains `Surge` (+1 CC).
- **Prompt Header**: `## CC: 6 (Surge adds +1, Rush adds +2 when played)`
- **AI Claim**: **9 CC**.
- **Actual Potential**: 6 (Base) + 1 (Surge) = 7 CC.
- **Discrepancy**: +2 CC.
- **Hypothesis**:
    1.  **Phantom Rush**: The prompt header mentions "Rush adds +2". The AI might have hallucinated that it had a Rush card, or simply added the +2 from the text description to its total, despite Rush not being in the hand.
    2.  **Arithmetic Error**: 6 + 1 = 9? Unlikely for a model of this class, but possible.
    3.  **Double Counting**: Did it count Surge twice? 6 + 1 + 1 = 8. Still not 9.
    4.  **Surge + Rush**: 6 + 1 (Surge) + 2 (Rush text) = 9. This fits the math exactly.

## Root Cause Analysis: "Header Pollution"

The prompt header statically includes rules for Surge and Rush:
```
## CC: {cc_available} (Surge adds +1, Rush adds +2 when played)
```

In Turn 5, the AI likely read "Rush adds +2" and conflated the *rule existence* with *card possession*, adding it to the total.

**Why Turn 1 worked?**
In Turn 1, the base CC was 2.
2 + 1 (Surge) = 3.
If it added Rush (2), it would be 5.
It claimed 3.
So in Turn 1, it *did not* hallucinate Rush.

**Why Turn 5 failed?**
Base 6.
Maybe at higher CC counts, or with different hand context, the attention mechanism drifts?
Turn 5 Hand was very small: Only `Surge`.
Turn 1 Hand was large: `Surge`, `Wake`, `Knight`, `Umbruh`, `Paper Plane`, `Archer`.

**Theory**: In Turn 5, with a sparse hand, the AI might have paid more attention to the Header text to find "options", leading to the hallucination of the Rush bonus.

## Action Items for Improvement

1.  **Dynamic Header**: Only mention "Surge adds +1" or "Rush adds +2" in the header *if those cards are actually in the hand*.
    - *Current*: Static text.
    - *Proposed*: Calculate potential modifiers in Python and only inject relevant text.
2.  **Explicit Potential Calculation**: Instead of asking the AI to do the math, provide the potential total in the prompt.
    - *Proposed*: `## CC: 6 (Potential: 7 via Surge)`

## Diagnostic Tool Updates
- The `diagnose_ai_game.py` script was updated to calculate "Potential CC" by scanning the prompt for Surge/Rush entries in the Hand section. This successfully differentiated Turn 1 (Valid Potential) from Turn 5 (Invalid Hallucination).

