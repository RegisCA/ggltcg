# URGENT: Execution Failure - AI Cannot Execute Planned Actions

**Game ID**: 133e16a7-2a41-44f5-b6be-e5caca39e73d  
**Turn**: 2  
**Date**: 2026-01-05

## What Happened

The AI **correctly planned** an aggressive sequence:
```
Surge -> Knight -> tussle Knight->Umbruh -> end_turn | CC: 4/4 spent
```

But **failed to execute** it:
```
Actual: Surge -> Knight -> end_turn
```

## Execution Log

```
Action 0: play_card Surge
  Method: heuristic
  Status: success ✅

Action 1: play_card Knight  
  Method: heuristic
  Status: success ✅

Action 2: end_turn (WAS SUPPOSED TO BE: tussle Knight->Umbruh)
  Method: llm (fallback because heuristic failed)
  Status: success ❌ (wrong action!)
  Reason: "Action not available (heuristic match failed)"
```

## Root Cause

The **heuristic matcher** couldn't find the tussle action in the available actions. This suggests:

1. **The tussle action wasn't available** (Knight had summoning sickness? But the rules say toys can tussle same turn!)
2. **The action format mismatch** (planned format doesn't match available action format)
3. **The action validator rejected it** (Knight was played but not yet "awake" in the state?)

## Why This Is Critical

**The prompt improvements ARE working**:
- ✅ Surge is prioritized (Sequence 0 starts with Surge)
- ✅ Tussle is included (5 out of 9 sequences have tussles)
- ✅ Strategic selector chose the aggressive option

**But execution is broken**:
- ❌ Planned actions can't be matched to available actions
- ❌ LLM fallback chooses `end_turn` instead of retrying or adapting

## Impact

This is **worse than bad planning**. The AI is:
1. Generating good plans
2. Choosing good plans
3. **Failing to execute them**

From the user's perspective, the AI looks passive and stupid. But the real problem is that the execution layer is silently failing and substituting `end_turn`.

## Investigation Needed

1. **Check game state after Knight is played**: Was Knight actually in play? Was it marked as "can tussle"?
2. **Check available actions**: What actions were available at Action 2? Was `tussle Knight->Umbruh` in the list?
3. **Check heuristic matching logic**: Why did the matcher fail? Format mismatch? ID mismatch?

## Hypothesis

The game engine might still be enforcing "summoning sickness" (toys can't act the turn they're played), even though the rules say they can tussle immediately. This would explain why:
- Knight was successfully played
- But `tussle Knight->...` wasn't available immediately after

## Next Steps

1. **Don't merge PR #289 yet** - the problem isn't with the prompts
2. **Investigate the execution layer** - specifically `get_available_actions()` and heuristic matching
3. **Check if Knight gains "can tussle" status immediately** after being played
