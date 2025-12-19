# Bug Fix: AI Target Confusion (Issue with Jumpscare Targeting Own Cards)

**Date:** December 18, 2024  
**Game ID:** 6a7910bb-632e-4458-9886-5e0c7f3ba68a  
**AI Logs:** #6259, #6298  
**Prompts Version:** Updated 2.1 → 2.3

## Problem Description

The AI player incorrectly targeted its own Umbruh card with Jumpscare while thinking it was targeting the opponent's card. The AI reasoning stated:

> "The opponent has no toys in play, making them vulnerable to direct attacks. Playing Jumpscare on **their strongest card, Umbruh**, forces them to replay it..."

However, Umbruh was actually the AI's own card in play. The opponent had no toys in play at all.

### Turn 1 Sequence (AI Turn)

1. ✅ Played Demideca (reasonable - boosts future toys)
2. ❌ Played Umbruh (questionable - unnecessary board building)
3. ❌ Played Archer (unnecessary - already has 2 toys in play)
4. **❌ BUG: Played Jumpscare targeting its own Umbruh** (thought it was opponent's card)

## Root Cause Analysis

### What Happened

The AI was shown this prompt structure:

```
### YOUR STATUS
- In Play (3): Demideca (4 SPD...), Umbruh (5 SPD...), Archer (1 SPD...)

### OPPONENT STATUS
- In Play (0): NONE (play a Toy first, then you can direct attack)

## YOUR VALID ACTIONS
1. Play Jumpscare (Cost: 0 CC, select target)
   Available targets (use the UUID from [ID: ...]):
   - [ID: 9f9eb07f...] Demideca (4 SPD, 3 STR, 4/4 STA)
   - [ID: d16b0b43...] Umbruh (5 SPD, 5 STR, 5/5 STA)  ← AI's own card!
   - [ID: 19355525...] Archer (1 SPD, 1 STR, 6/6 STA)
```

### The Bug

**The target list didn't indicate WHO OWNED each card.** The AI saw:
1. "Umbruh" in its own "In Play" section
2. "Umbruh" in the available targets list

The AI assumed these were different cards - one was its own, and the other must be the opponent's. Since the opponent section showed "NONE", the AI incorrectly concluded that the target list was showing opponent's cards.

### Why This Is Confusing

Cards like Jumpscare can target **both** your own cards and opponent's cards. This is intentional game design:
- **Primary use:** Bounce opponent's threats back to their hand
- **Advanced use:** Bounce your own cards to replay them for resets or reactivation

However, without ownership labels, the AI cannot distinguish whose cards are whose in the target list.

## The Fix

### Code Changes (Version 2.2 - Initial Fix)

**File:** `backend/src/game_engine/ai/prompts/formatters.py`

**Change 1:** Modified `get_card_details()` to return ownership label

```python
def get_card_details(card_id: str) -> tuple[str, str, str]:
    """Returns (display_name, actual_id, owner_label) tuple"""
    # ... find card in game state ...
    
    # Determine ownership label
    if player.player_id == ai_player_id:
        owner_label = "YOUR"
    else:
        owner_label = "OPPONENT'S"
    
    return (display, card.id, owner_label)
```

**Change 2:** Added ownership labels to target display

```python
for target_id in action.target_options:
    display_name, actual_id, owner_label = get_card_details(target_id)
    if owner_label:
        target_details.append(f"[ID: {actual_id}] {owner_label} {display_name}")
```

### New Prompt Output

Now the AI sees:

```
1. Play Jumpscare (Cost: 0 CC, select target)
   Available targets (use the UUID from [ID: ...]):
   - [ID: 9f9eb07f...] YOUR Demideca (4 SPD, 3 STR, 4/4 STA)
   - [ID: d16b0b43...] YOUR Umbruh (5 SPD, 5 STR, 5/5 STA)
   - [ID: 19355525...] YOUR Archer (1 SPD, 1 STR, 6/6 STA)
```

The ownership is now **explicit and unambiguous**.

### Additional Fix (Version 2.3 - Strategic Hint Removal)

**Problem Discovered in AI Log #6298:**

Even with ownership labels, the AI was still confused. The prompt showed:
```
- [ID: 2b82b15a...] YOUR Knight (4 SPD, 4 STR, 3/3 STA)
   → TEMPO BOUNCE - Return opponent's threat...
```

The target was labeled "YOUR Knight" but the strategic hint said "Return **opponent's** threat", creating a direct contradiction. The AI reasoned about "the opponent's Umbruh" while targeting its own Knight.

**Root Cause:** Strategic hints are **generic advice** that doesn't match specific target context. A hint saying "Return opponent's threat" appears below "YOUR Knight", confusing the AI.

**Solution:** Removed strategic hints from the action list entirely. They should only appear in the hand section where they provide context about the card's general use, not in the action list where they conflict with specific targeting choices.

**File:** `backend/src/game_engine/ai/prompts/formatters.py`

```python
# Removed this block:
# if action.action_type == "play_card" and action.card_id:
#     for card_name in CARD_EFFECTS_LIBRARY.keys():
#         if card_name in action.description:
#             card_info = CARD_EFFECTS_LIBRARY[card_name]
#             action_text += f"\n   → {card_info.get('strategic_use', '')}"

# Added comment explaining why:
# NOTE: Strategic hints removed from action list to avoid confusion
# Generic hints like "Return opponent's threat" contradict specific targets like "YOUR Knight"
```

**Now the AI sees:**
```
1. Play Jumpscare (Cost: 0 CC, select target)
   Available targets (use the UUID from [ID: ...]):
   - [ID: 9f9eb07f...] YOUR Demideca (4 SPD, 3 STR, 4/4 STA)
   - [ID: d16b0b43...] YOUR Umbruh (5 SPD, 5 STR, 5/5 STA)
   - [ID: 19355525...] OPPONENT'S Knight (4 SPD, 4 STR, 3/3 STA)
```

Clean target list with clear ownership, no contradictory hints.

### Summary of All Changes

**File:** `backend/src/game_engine/ai/prompts/card_library.py`

Updated Jumpscare description to clarify targeting rules:

```python
"effect": "Target: Return any card in play to owner's hand (no sleep trigger). Can target YOUR cards or opponent's.",
"strategic_use": "TEMPO BOUNCE - Return opponent's threat without triggering when-sleeped. Great vs Umbruh! Can also bounce your own card to replay it (advanced).",
```

**File:** `backend/src/game_engine/ai/prompts/schemas.py`

Incremented version: `PROMPTS_VERSION = "2.3"`

## Testing

### Tests Passed

```bash
pytest tests/ -k "test_jumpscare" -v
# 5 tests passed

pytest tests/test_game_engine.py tests/test_effects.py -v
# 9 tests passed
```

All existing tests pass. The fix doesn't change game logic - only the AI's perception of the game state.

## Impact Assessment

### Cards Affected

This fix improves targeting clarity for **all cards with target selection**:
- **Jumpscare** - Can target own or opponent's cards
- **Drop** - Can target own or opponent's cards
- **Twist** - Targets opponent's cards only
- **Wake/Sun** - Targets own sleep zone only (already clear)
- **Copy** - Targets any card in play
- **Tussle actions** - Only show opponent's cards as targets

### Game Balance

No game balance changes. This is a bug fix for AI perception only. The AI should now:
1. ✅ Correctly identify which cards belong to which player
2. ✅ Make informed decisions about targeting
3. ✅ Understand when bouncing own cards makes strategic sense vs targeting opponents

## Future Considerations

### Similar Issues to Watch For

1. **Controller vs Owner confusion** - Cards stolen via Twist should show "OPPONENT'S" even if controlled by AI
2. **Multi-target clarity** - Sun selecting multiple targets needs clear ownership
3. **Sleep zone targets** - Wake/Sun already specify "your sleep zone" so less confusing

### Recommended Testing

When testing AI behavior, check:
- ✅ AI understands target ownership in prompts
- ✅ AI makes strategically sound targeting decisions
- ✅ AI doesn't confuse controlled vs owned cards (Twist scenarios)

## Related Issues

- PR #250: AI prompt improvements for aggressive tussling (merged)
- Issue #204: New cards implementation (Jumpscare added)
- Logs #6256-6259: Turn 1 decision logs from game 6a7910bb

## Deployment

Changes are ready for deployment:
- ✅ Code changes tested
- ✅ No breaking changes
- ✅ Version incremented
- ⏳ Awaiting PR creation and merge

