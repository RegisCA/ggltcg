# AI Strategy Analysis: Human Play Patterns

**Date**: 2026-01-04
**Purpose**: Analyze high-level human strategies to inform AI V4 improvements.
**Source**: Game logs `47d074c9` (Kyle vs Gemiknight) and `d5f1e7d1` (Régis vs Gemiknight).

## 1. The "Engine" Pattern (Resource Generation)

**Observed in**: Game `47d074c9` (Kyle, Turn 1)
**Key Card**: `Hind Leg Kicker` (1 CC, 3/3/1)
**Effect**: "When you play a card (not this one), gain 1 charge."

**The Play**:
1.  Start with 2 CC.
2.  Play `Hind Leg Kicker` (Cost 1, Remaining 1).
3.  Play `Drum` (Cost 1, Remaining 0). **Trigger**: Gain 1 CC (Remaining 1).
4.  Play `Belchaletta` (Cost 1, Remaining 0). **Trigger**: Gain 1 CC (Remaining 1).
5.  ...Repeat for 3 more cards.

**Strategic Insight**:
- **Mana Cheating**: The player effectively played 5 cards for "free" after the initial investment.
- **Sequencing Matters**: `Hind Leg Kicker` MUST be played first.
- **AI Gap**: The AI currently sees cards as independent costs. It doesn't calculate "net cost" after triggers. It likely sees a hand of 6 cards costing 1 CC each and thinks "I can only play 2 of these".

**AI Improvement**:
- **Dynamic Cost Calculation**: The sequence generator needs to simulate the *gain* from effects like `Hind Leg Kicker` to realize it has more budget than it thinks.
- **Priority Heuristic**: "Engine" cards (resource generators) should be prioritized in sequencing.

## 2. The "Recycle" Pattern (Wake -> Re-play)

**Observed in**: Game `d5f1e7d1` (Régis, Turn 4)
**Key Card**: `Wake` (1 CC)
**Effect**: "Unsleep 1 of your cards." (Moves card from Sleep Zone -> Hand)

**The Play**:
1.  Play `Wake` (1 CC). Target `Beary` (in Sleep Zone).
2.  `Beary` moves to Hand.
3.  Play `Beary` (1 CC).
4.  Total Cost: 2 CC.

**Strategic Insight**:
- **Board Presence**: This turns a dead card into an active threat.
- **Cost Awareness**: The true cost of this line is `Cost(Wake) + Cost(Target)`.
- **AI Gap**: The AI likely sees `Wake` as just "unsleeping" and might not factor in the cost to re-play the card, or conversely, might not realize that re-playing is a valid option to regain board presence.
- **Correction**: My previous assumption that `Wake` puts cards directly into play was wrong. The AI needs to understand the `Sleep -> Hand -> Play` pipeline.

## 3. The "Steal & Strike" Pattern (Twist)

**Observed in**: Game `d5f1e7d1` (Régis, Turn 6)
**Key Card**: `Twist` (3 CC)
**Effect**: "Put a card your opponent has in play in play, but under your control."

**The Play**:
1.  Play `Twist` (3 CC). Target `Raggy` (Opponent's board).
2.  `Raggy` enters play under Régis's control.
3.  `Raggy` tussles immediately (Cost 0 due to effect).

**Strategic Insight**:
- **Immediate Value**: Stealing a card removes a threat AND adds an attacker.
- **Summoning Sickness Exception?**: The log shows `Raggy` tussling immediately.
    - *Hypothesis A*: `Twist` grants implicit haste.
    - *Hypothesis B*: Stealing doesn't reset "time in play" (unlikely if it's a new object).
    - *Hypothesis C*: The game rules allow tussling immediately? (Contradicts "First Turn Exception" implying sickness exists, but maybe only for Turn 1?).
    - *Fact Check Needed*: Does the game actually have summoning sickness for Tussling?
        - Rule: "Toys... remain there until sleeped. They can participate in tussles."
        - Rule: "First Turn Exception: ...may not tussle on the first turn of the game." (Raggy's text).
        - **Crucial**: If there is NO general summoning sickness, then `Wake -> Play -> Tussle` is valid immediately!

## 4. General Summoning Sickness Check

**Investigation**:
- If `Raggy` could tussle immediately after being stolen/played via Twist...
- And if `Beary` could tussle immediately after being re-played via Wake...
- Then **Toys might not have summoning sickness** in this game (except for specific card restrictions like Raggy/Rush or the global Turn 1 rule).

**Evidence**:
- Game `d5f1e7d1` Turn 2: Régis plays `Beary`, then `Beary` tussles `Beary`. **Immediate Tussle!**
- Game `47d074c9` Turn 2: Gemiknight plays `Hind Leg Kicker`, then it tussles. **Immediate Tussle!**

**Conclusion**:
- **THERE IS NO SUMMONING SICKNESS.** (Except for Turn 1 or specific card text).
- **Impact**: The AI is likely assuming it can't attack with played cards, leading to passive play.
- **Fix**: The AI prompt must explicitly state: "Toys can tussle the SAME TURN they are played (unless it's Turn 1)!"

## Summary of Required Fixes

1.  **Prompt Rule Update**: Explicitly state "NO SUMMONING SICKNESS - Toys can tussle immediately!".
2.  **Engine Logic**: The sequence generator must account for CC gained *during* the sequence (e.g., `Hind Leg Kicker`).
3.  **Combo Logic**: `Wake` -> `Play` is a valid chain. `Twist` -> `Tussle` is a valid chain.
