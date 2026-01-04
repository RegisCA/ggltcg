# AI V4 Game Analysis: 5c54f1b8-2471-4e93-a12a-1369a43bc01b (CC Hallucination)

**Date**: Jan 3, 2026
**Game ID**: `5c54f1b8-2471-4e93-a12a-1369a43bc01b`
**AI Version**: 4

## Summary
This analysis focuses specifically on the **CC Hallucination** observed in Turn 4, providing further evidence for the "Header Pollution" hypothesis.

## Turn Analysis

### Turn 2: Correct Behavior
- **State**: 4 CC.
- **Hand**: Likely contained Surge (based on sequence `play Surge...`).
- **Claimed**: 4 CC.
- **Sequence**: `play Surge -> play Knight -> tussle`. Cost: 0 + 1 + 2 = 3 CC.
- **Observation**: The AI stayed within the base budget (4) even though it had potential for 5. It did not hallucinate extra CC.

### Turn 4: CC Hallucination (+3 Unaccounted)
- **State**: 6 CC.
- **Hand**: Likely **NO** Surge/Rush (sequences started with `play Umbruh`, not Surge).
- **Claimed**: **9 CC**.
- **Actual**: 6 CC.
- **Potential**: 6 CC (assuming no Surge/Rush).
- **Delta**: +3 CC.
- **Hypothesis**:
    - The prompt header likely contained the static text: `## CC: 6 (Surge adds +1, Rush adds +2 when played)`.
    - The AI saw "6", "+1", "+2".
    - Sum: 6 + 1 + 2 = 9.
    - It claimed 9 CC despite not having the cards to generate that CC.

## Pattern Confirmation
This matches the findings from Game `4308a90a` (Turn 5):
- Base CC: 6.
- Claimed CC: 9.
- Delta: +3.

In both cases, the AI appears to be parsing the **rules text** in the header as **active bonuses**, adding +3 (Surge + Rush) to its budget even when it doesn't hold those cards.

## Conclusion
The static inclusion of "Surge adds +1, Rush adds +2" in the prompt header is a **critical prompt engineering flaw**. It causes the model to hallucinate resources it doesn't have, leading to the generation of illegal sequences (e.g., spending 9 CC when only 6 are available).

## Recommendation
Implement **Dynamic Header Generation**:
1.  Calculate `potential_cc` based on actual hand contents.
2.  Only include text about Surge/Rush bonuses if `potential_cc > cc_available`.
3.  Remove the static rule text from the header entirely.
