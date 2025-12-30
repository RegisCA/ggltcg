# Copy Card Target Validation Fix

**Date:** December 19, 2024  
**Issue:** Copy card was able to target opponent's cards  
**Severity:** High - Security Vulnerability

## Problem Description

User reported that an AI player was able to copy one of their cards (human player's cards) when playing the Copy card. The Copy card's description states: "This card acts as an exact copy of a card **you have in play**" - meaning it should only copy the player's own cards, not opponent's cards.

## Root Cause Analysis

The issue was a **security vulnerability** in the action execution layer:

1. **Validation Layer (Correct):** The `ActionValidator` correctly filters valid targets to only include the player's own cards by calling `effect.get_valid_targets(game_state, player)`.

2. **Execution Layer (Vulnerable):** The `ActionExecutor` accepted arbitrary card IDs from the API request and passed them directly to the game engine without re-validating that the target was actually in the list of valid targets.

3. **Attack Vector:** An AI player (or malicious client) could bypass the validation by sending a POST request with an opponent's card ID in the `target_card_id` field.

### Code Flow

```
API Request → ActionExecutor.execute_play_card()
             → _handle_targets() [looks up card by ID, NO validation]
             → engine.play_card() [executes without checking if target is valid]
             → CopyEffect.apply() [copies whatever target was provided]
```

## Security Impact

This vulnerability affected **all targeting effects**, not just Copy:
- Copy (should only target own cards)
- Wake/Sun (should only target own sleep zone)
- Twist (should only target opponent's cards) - could have been used backwards
- Drop/Jumpscare/Sleep Target (target any card in play)

An AI or malicious client could:
- Copy opponent's best cards (Copy)
- Unsleep opponent's cards (Wake/Sun)
- Twist own cards to opponent (Twist used incorrectly)
- Target invalid cards for sleep/bounce effects

## Solution

Added target validation in `ActionExecutor.execute_play_card()`:

```python
# Handle targets
target_kwargs = self._handle_targets(target_card_id, target_card_ids)

# Validate targets are actually valid for this card's effect
if target_kwargs.get("target") or target_kwargs.get("targets"):
    validation_error = self._validate_effect_targets(card, player, target_kwargs)
    if validation_error:
        raise ValueError(validation_error)
```

### New Method: `_validate_effect_targets`

```python
def _validate_effect_targets(self, card: Card, player: Player, target_kwargs: Dict[str, Any]) -> Optional[str]:
    """
    Validate that the provided targets are actually valid for this card's effect.
    
    This prevents clients from bypassing target validation by sending arbitrary
    card IDs that weren't in the valid targets list.
    """
```

This method:
1. Gets all effects for the card being played
2. For each `PlayEffect` that requires targets:
   - Calls `effect.get_valid_targets(game_state, player)` to get the authoritative list
   - Checks that each provided target is in that list
3. Returns an error message if any target is invalid

## Testing

### New Tests (`test_copy_opponent_card_bug.py`)

1. **`test_copy_cannot_target_opponent_cards`**: Validation layer correctly excludes opponent cards
2. **`test_copy_only_targets_own_cards_when_both_have_cards`**: Validation shows only player's cards even when opponent has cards
3. **`test_execute_copy_with_opponent_card_raises_error`**: **Security test** - Execution layer rejects opponent card IDs

### Regression Testing

All existing tests pass:
- `test_copy_card_bug.py` (6 tests)
- `test_effects.py` (3 tests)
- `test_phase1_effects.py` (10 tests)
- `test_phase2_effects.py` (6 tests)
- Tests for Twist, Wake, Sun, etc. (12 tests)

## Files Modified

1. **`backend/src/game_engine/validation/action_executor.py`**:
   - Added `_validate_effect_targets()` method
   - Added validation call in `execute_play_card()`

2. **`backend/tests/test_copy_opponent_card_bug.py`** (New):
   - Comprehensive test suite for the bug and fix

## Deployment Considerations

This is a **critical security fix** that should be deployed as soon as possible:

1. **No Breaking Changes**: The fix only rejects invalid requests that should never have worked
2. **AI Impact**: Any AI that was exploiting this bug (intentionally or not) will now receive error responses
3. **Backwards Compatible**: Legitimate plays continue to work as before

## Recommendations

1. ✅ **Deploy to Production**: This fix is ready for main
2. **Monitor AI Behavior**: Watch for any AI execution errors after deployment (would indicate the AI was using invalid targets)
3. **Security Audit**: Consider auditing other action execution paths for similar vulnerabilities
4. **Rate Limiting**: Consider adding rate limiting to the action execution API

## Prevention

To prevent similar issues in the future:

1. **Defense in Depth**: Always validate inputs at multiple layers (API → Executor → Engine)
2. **Trust Nothing**: Never trust client-provided IDs without validation
3. **Whitelist Validation**: Always validate against an authoritative whitelist, not just existence checks
4. **Security Testing**: Add security-focused tests that attempt to bypass validation

## Related Issues

This fix also prevents potential exploits for:
- Issue #188 (Sun multi-target selection)
- Issue #141 (Wake/Sun edge cases)
- Any future targeting effects

## References

- Card Definition: `backend/data/cards.csv` (Copy card, line 11)
- Copy Effect: `backend/src/game_engine/rules/effects/action_effects.py:453-540`
- Game Rules: `docs/rules/GGLTCG Rules v1_1.md`
