# CRITICAL BUG: Tussle Action Parsing Failure [FIXED]

## Issue

**Game**: 133e16a7-2a41-44f5-b6be-e5caca39e73d, Turn 2
**Status**: ✅ FIXED - Parser now handles name+ID format
**Fixed in**: PR #TBD

## Root Cause

The Sequence Generator (Request 1) generates tussle actions in this format:
```
tussle Knight [a94c6c17-0b54-4862-b1b5-c9f827a04df6]->Umbruh [f6e15fbd-5223-4c12-96da-0e83ad0dd10c]
```

But the `_parse_action_string()` function in `sequence_generator.py` only recognized these formats:
- `tussle Knight->Umbruh` (names only)
- `tussle uuid1->uuid2` (UUIDs only)  
- `tussle k1->u1` (short IDs only)

**The parser did NOT handle the format `tussle NAME [ID]->NAME [ID]`** that the LLM was generating.

## Evidence

From game 133e16a7-2a41-44f5-b6be-e5caca39e73d, Turn 2:

**Sequence 0** (selected by Strategic Selector):
```
play Surge [c5d99553-9d2c-4da0-8e01-a1a3ed2e791e] -> play Knight [a94c6c17-0b54-4862-b1b5-c9f827a04df6] -> tussle Knight [a94c6c17-0b54-4862-b1b5-c9f827a04df6]->Umbruh [f6e15fbd-5223-4c12-96da-0e83ad0dd10c] -> end_turn | CC: 4/4 spent | Sleeps: 1
```

**Resulting action_sequence (BEFORE FIX)**:
```json
[
  {"action_type": "play_card", "card_name": "Surge"},
  {"action_type": "play_card", "card_name": "Knight"},
  {"action_type": "end_turn"}
]
```

The tussle action was silently dropped during parsing because it didn't match any regex pattern.

## Impact

1. **Execution failures**: AI plans tussles but cannot execute them
2. **Appears passive**: AI plays cards but doesn't attack (Turn 2 wasted 0 CC instead of tussling)
3. **Misleading UI**: Admin viewer shows 3 green checkmarks even though wrong action was executed
4. **Undermines all prompt improvements**: We've improved planning but execution layer was broken

## Fix

Updated `_parse_action_string()` in `backend/src/game_engine/ai/prompts/sequence_generator.py` to handle the format:
- `tussle CardName [uuid]->TargetName [uuid]`
- `direct_attack CardName [uuid]`
- `activate CardName [uuid]->TargetName [uuid]`

The parser now tries the name+ID format FIRST, then falls back to legacy formats.

### Changes Made

1. **Added new regex patterns** (lines 407-445):
   - `tussle NAME [UUID]->NAME [UUID]`
   - `direct_attack NAME [UUID]`
   - `activate NAME [UUID]->NAME [UUID]`

2. **Added comprehensive tests** in `test_ai_v4_components.py`:
   - `test_tussle_with_name_and_id` - Verifies tussle parsing
   - `test_direct_attack_with_name_and_id` - Verifies direct attack parsing
   - `test_activate_with_name_and_id` - Verifies activate parsing
   - `test_full_sequence_parsing` - Tests full sequence from game 133e16a7

All tests pass ✅

## Related Files

- `backend/src/game_engine/ai/prompts/sequence_generator.py` - Fixed `_parse_action_string()`
- `backend/tests/test_ai_v4_components.py` - Added parsing tests
- `backend/src/game_engine/ai/prompts/strategic_selector.py` - `convert_sequence_to_turn_plan()` (consumes parsed actions)
- `backend/src/game_engine/ai/turn_planner.py` - Calls conversion function

## Follow-up Questions

1. **Did 160-game simulation miss this?** Should audit simulation logs for execution failures.
2. **Was this always broken?** Need to check if older games had the same issue.
3. **Why did validation not catch this?** The tussle action was silently dropped, so validation saw a 2-action sequence (play, play) instead of 4-action sequence (play, play, tussle, end_turn).
