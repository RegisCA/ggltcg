# AI Prompt Update: Remove "Building" Mindset, Focus on Attack & Defense

**Date:** December 19, 2024  
**Prompts Version:** 2.4  
**Related Logs:** #6308  

## Problem

The AI was making poor strategic decisions based on a "building" mentality that doesn't match GGLTCG's aggressive game design.

### Examples from Game Logs

**AI Log #6308 Reasoning:**
> "The opponent has no toys in play, so I can attack directly to sleep a random card from their hand, which is the best way to progress towards winning."

**AI Log #6308 Actual Action:**
Despite that correct reasoning, the AI played Jumpscare (a free card with no target) instead of ending turn. Wasteful first turn.

**Other Examples:**
- Playing Jumpscare on own Knight "to prepare for future turns"
- Playing 2-3 toys on turn 1 "to build board presence" instead of just 1 defensive toy
- Focusing on "building hand" or "building board" rather than attacking

## Root Cause

The system prompt used "BUILD" language that created wrong mental model:
- Priority #4: "BUILD BOARD: You have no Toys in play? → Play a Toy so you can attack!"
- This made AI think it needed to accumulate toys for future value

**The Reality:**
GGLTCG is aggressive. You should:
1. **Attack when possible** (direct attacks or winning tussles)
2. **Play defense only when necessary** (block direct attacks on hand)
3. **Save cards** for when you can use them to attack

## The Fix

### Reframed Priority #4: BUILD → SETUP DEFENSE

**Before:**
```
4. BUILD BOARD: You have no Toys in play? → Play a Toy so you can attack!
```

**After:**
```
4. SETUP DEFENSE (ONLY if you have ZERO Toys in play):
   - You have no toys? → Opponent can direct attack YOUR hand next turn!
   - Play ONE defensive toy to block direct attacks: high SPD (hard to tussle) or high STA (hard to sleep)
   - DON'T play multiple toys "just because" - save cards for when you can attack!
```

### Key Changes

1. **Removed "BUILD" language** - No more "build board", "build hand", "build presence"
2. **Reframed as DEFENSE** - Playing toys is defensive, not offensive
3. **Emphasis on ONE toy** - Don't waste cards playing multiple toys when you can't attack
4. **Explicit reasoning** - "Opponent can direct attack YOUR hand next turn"

### Updated "Avoid These Mistakes" Section

**Added:**
- DON'T play multiple toys when you already have defense (save cards for attacks!)
- DON'T waste CC on cards that don't help you attack THIS TURN
- DON'T end turn with 0 Toys when opponent has toys (you'll be open to direct attacks next turn!)

**Removed:**
- References to "building" anything
- "afford to play one" (wrong framing - it's about strategy, not affordability)

### New Example Scenario

Added **Scenario E - Defense Setup (Turn 1):**
```
Turn 1, you have 2 CC, no toys in play yet, opponent also has no toys.
- OPTION A: Play 1 fast toy (Belchaletta 4 SPD) to block direct attacks next turn, END TURN
- OPTION B: Play 1 durable toy (Knight 4 STA) to block direct attacks next turn, END TURN
- WRONG: Play 2-3 toys "to build board" when you can't attack yet - waste of cards!
- WHY: Playing 1 defensive toy prevents opponent from direct attacking your hand. Save remaining cards for attacks!
```

## Expected Impact

### AI Should Now:

1. ✅ **Prioritize attacks** - If direct attack or winning tussle available, do it NOW
2. ✅ **Minimal defense** - Play 1 defensive toy only when needed
3. ✅ **Save cards** - Don't waste cards playing multiple toys when you can't attack
4. ✅ **End turn appropriately** - If you have defense and can't attack, END TURN

### AI Should NOT:

1. ❌ Play Jumpscare on own cards "to prepare for future"
2. ❌ Play 3 toys on turn 1 when opponent has no toys
3. ❌ Think about "building" anything
4. ❌ Play cards that don't help attack THIS TURN

## Testing

✅ All core game engine tests pass  
✅ All effect tests pass  
⏳ Needs live testing against AI to verify behavioral changes

## Files Modified

- `backend/src/game_engine/ai/prompts/system_prompt.py` - Major rewrite of priority #4 and mistake avoidance
- `backend/src/game_engine/ai/prompts/schemas.py` - Version 2.3 → 2.4

## Related Issues

- Target confusion bug (fixed in v2.2-2.3) - [BUG_AI_TARGET_CONFUSION.md](BUG_AI_TARGET_CONFUSION.md)
- PR #250: AI prompt improvements for aggressive tussling (merged)

## Next Steps

1. ⏳ Test AI behavior in live games
2. ⏳ Monitor AI logs for "build" language in reasoning
3. ⏳ Verify AI plays minimal defense (1 toy when needed, not 3)
4. ⏳ Investigate Jumpscare-without-target bug from log #6308

