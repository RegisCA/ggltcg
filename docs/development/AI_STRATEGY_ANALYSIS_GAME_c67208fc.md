# AI Strategy Analysis: Game c67208fc (Root Cause Investigation)

**Game ID**: c67208fc-dd62-4868-8314-982b8d60a510  
**Winner**: Régis (7 turns)  
**AI Player**: Gemiknight (AI V4)

## Turn 2: Missed Optimal Line

**CC Available**: 4  
**AI Action**: Knight → Umbruh → Knight tussle Umbruh (2 CC spent, 2 CC floated)  
**Optimal Line**: Surge → Umbruh → Knight tussle Umbruh → Direct Attack  

### Problem Analysis
- **Surge** (0 CC) was in hand and not played. This gave +1 CC, enabling a 5 CC budget.
- **Direct Attack** (2 CC) was legal after clearing the board, but not included in the sequence.
- AI left 2 CC unused instead of capitalizing on the aggressive opening.

### Root Cause: Example Bias
The current prompt example is:
> `Example: Surge→Knight→tussle(sleeps last toy)→direct_attack→end_turn`

But the AI saw:
- Surge: 0 CC
- Knight: 1 CC  
- Umbruh: 1 CC
- Tussle: 2 CC

And chose `Knight → Umbruh → tussle`, skipping Surge entirely.

**Hypothesis**: The example shows Surge **before** Knight, suggesting Surge is an "enabler" for Knight. But the AI may not understand that Surge is *always* optimal to play first (free CC).

**Deeper Issue**: The AI's sequence generator doesn't have a **priority system** for resource cards. It treats all cards equally.

---

## Turn 4: Ended with 3 CC (Critical Waste)

**CC Available**: 5  
**AI Action**: Paper Plane + Archer + Wake (2 CC spent, 3 CC floated)  
**What Should Have Happened**: Wake → Knight (unsleep from hand, re-play), then use Knight to tussle

### Problem Analysis
- **Wake** was played but the target wasn't re-deployed. Wake returns a card to **hand**, requiring re-play.
- Knight was in the sleep zone. The optimal line is: `play Wake (1 CC) → target Knight → play Knight (1 CC) → tussle with Knight (2 CC)`. Total: 4 CC.
- Instead, AI just played Wake and left the turn with no board presence and 3 CC wasted.

### Root Cause: Wake Mechanic Misunderstanding
The current prompt says:
> `Wake moves card to HAND (must pay cost to play it again) → then it can tussle immediately!`

But the AI didn't chain the actions. It played Wake as an isolated action.

**Hypothesis**: The AI sees Wake as "complete" once the unsleep happens. It doesn't realize it should immediately consider *playing* the awakened card from hand.

**Deeper Issue**: The sequence generator doesn't model **state transitions mid-sequence**. After `play Wake`, the game state changes (Knight moves to hand), but the AI isn't re-evaluating the hand's playable cards.

---

## Turn 6: Knight in Play, CC Available, No Tussle

**CC Available**: 7  
**AI Action**: play Knight → Knight tussles Archer (3 CC spent, 4 CC floated)  
**What Should Have Happened**: Knight was ALREADY in play from Turn 5, should have used it to tussle immediately

### Problem Analysis
Looking at the Play-by-Play:
- Turn 5: Régis played Knight (for Régis, not AI)
- Turn 6: AI played Knight (their own), then tussled

Wait, let me re-check the sequence from the diagnostic output. The diagnostic says:
> `Sample Sequences: play Knight [31545a92...] -> tussle 31545a92->8...`

This means the AI **did** tussle, but used a freshly played Knight.

**Hypothesis**: The AI had a Knight in hand and played it, instead of using existing board state to tussle.

But the real question: **Why float 4 CC?** After playing Knight (1 CC) and tussling (2 CC), there were 4 CC left. What else was available?

---

## Root Cause Patterns (Cross-Game)

### 1. No Priority System for "Always Play First" Cards
Cards like **Surge** (free CC), **Rush** (cheap CC), and **Hind Leg Kicker** (CC engine) should be prioritized at the start of sequences. The AI treats them as "options" rather than "enablers."

### 2. State Transitions Aren't Re-Evaluated Mid-Sequence
After `play Wake → Knight moves to hand`, the AI should realize Knight is now playable. Instead, it ends the sequence without considering the new state.

### 3. "Board Already Exists" Isn't Considered Efficiently
When a toy is already in play, the AI sometimes prefers to play a new one (wasting CC) instead of using what's available. This suggests the sequence generator over-focuses on "play" actions.

### 4. CC Waste Is Not Penalized
The AI doesn't seem to understand that floating >1 CC is suboptimal unless it's a strategic choice (saving for next turn). The Rule: **If ending with 4+ CC, you're capped at 7 next turn, so you lose potential CC gain**.

---

## Proposed Fixes (Sustainable, Not Card-Specific)

### Fix 1: Add "Resource Priority" Heuristic
Modify the sequence generator prompt to include:
```
## RESOURCE PRIORITY (play these first if available):
- Surge (0 CC, +1 CC): Play immediately at start of turn
- Rush (0 CC, +2 CC): Play immediately at start of turn  
- Hind Leg Kicker (1 CC, +1 CC per subsequent card): Play first, then chain other cards
```

### Fix 2: Clarify "CC Waste" Threshold
Add to the prompt:
```
## CC EFFICIENCY:
- Ending turn with 0-1 CC: Optimal (maximized usage)
- Ending turn with 2-3 CC: Acceptable (possible strategic save)
- Ending turn with 4+ CC: WASTEFUL (you'll cap at 7 CC next turn, losing potential gain)
- Rule: If you have 4+ CC left, look for more plays!
```

### Fix 3: State Transition Examples
Replace the static example with multi-step examples showing state changes:
```
Example 1 (Resource First): Surge→Knight→tussle→direct_attack (5 CC spent, Surge gave +1)
Example 2 (Wake Chain): Wake [target: Knight]→play Knight→tussle (4 CC spent, Knight back in play)
Example 3 (Engine): Hind Leg Kicker→Drum→Violin (3 spent, gained 2 back, net 1 CC)
```

### Fix 4: Re-Evaluate Hand After Action Cards
This is a code change, not a prompt change. After parsing `play Wake`, the sequence generator should:
1. Simulate the state change (Knight moves to hand)
2. Re-generate the "hand listing" with Knight now available
3. Continue generating the sequence with the updated hand

This requires modifying the sequence generation logic to be **iterative** rather than **static**.

---

## Summary: The Real Problem

The AI is treating sequence generation as a **static planning** problem:
- Hand = Fixed at start of turn
- Board = Fixed at start of turn

But GGLTCG is a **dynamic planning** problem:
- Hand changes mid-sequence (Wake, Toynado)
- Board changes mid-sequence (play toy, tussle sleeps toy)
- CC changes mid-sequence (Surge, Hind Leg Kicker)

The prompt can help with **heuristics** (priority, efficiency thresholds), but the fundamental fix requires **code changes** to make the sequence generator simulate state as it builds sequences.

**Short-Term (Prompt Only)**: Add heuristics for resource priority and CC waste.  
**Long-Term (Code)**: Implement iterative sequence generation with state simulation.
