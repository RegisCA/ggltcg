# AI V4 Standard Scenario Tests

This directory contains automated regression tests for AI V4 (Phase 2 of the remediation plan).

## Purpose

Replace the manual "play 2 turns, check if AI is reasonable" workflow with automated tests that:
- Validate CC efficiency (waste ≤1 CC per turn)
- Validate damage output (sleep ≥1 card per turn)
- Catch prompt regressions automatically

## Running Tests

### Quick Manual Verification

```bash
cd backend
python scripts/run_standard_scenario.py
```

This provides detailed output for each turn and is useful for:
- Quick smoke testing after prompt changes
- Debugging AI behavior
- Understanding what the AI is doing

### Automated Test Suite

```bash
cd backend
pytest tests/test_ai_standard_scenario.py -v -s
```

This runs 3 tests:
1. `test_turn1_with_surge_knight` - Turn 1 (P1) opening
2. `test_turn2_aggressive_play` - Turn 2 (P2) response
3. `test_full_scenario_turn1_and_turn2` - Both turns in sequence

**Note**: Tests require a valid `GOOGLE_API_KEY` in `backend/.env`. Without it, tests are skipped (not failed).

## Expected Behavior

### Turn 1 (Player 1)
- **Setup**: 2 CC, Hand=[Surge, Knight, Umbruh, Wake]
- **Expected**: Surge (0 CC) → Knight (1 CC) → direct_attack (2 CC)
- **Result**: 3 CC used, 1 card slept, 0 CC wasted
- **Acceptance**: cc_wasted ≤ 1, cards_slept ≥ 1

### Turn 2 (Player 2)
- **Setup**: 4 CC, Knight in play vs opponent Knight
- **Expected**: Tussle (2 CC) + play toys or direct_attack
- **Result**: 4-5 CC used, 1-2 cards slept, 0-1 CC wasted
- **Acceptance**: cc_wasted ≤ 1, cards_slept ≥ 1

### Full Scenario
- **Acceptance**: total_cc_wasted ≤ 2, total_sleeps ≥ 2

## Understanding Test Results

### ✅ Tests Pass
The AI is performing at or above baseline expectations. This doesn't mean perfect play, just that it meets minimum quality gates.

### ❌ Tests Fail
The AI is underperforming. Common causes:
- Prompt regression (check recent changes to sequence_generator.py)
- LLM variability (same prompt can produce different results)
- Model change (different Gemini model may behave differently)

**Action**: Run the manual script to see detailed output, then investigate the prompt or model configuration.

## LLM Variability

**Important**: These tests involve LLM calls, which are non-deterministic. The same scenario can produce different results across runs:
- One run: Surge→Knight→direct_attack (optimal)
- Next run: Surge→Knight only (suboptimal)

This is expected behavior with LLMs. The tests are designed to:
1. Pass when AI meets minimum quality gates
2. Fail when AI underperforms (catching regressions)
3. Provide detailed metrics to understand why

If tests fail occasionally but pass most of the time, the AI is functioning correctly but may need prompt tuning to increase consistency (see Phase 3+).

## Metrics Used

Tests use `TurnMetrics` from `game_engine.ai.quality_metrics`:
- `cc_wasted`: CC remaining at end of turn (target: ≤1)
- `cards_slept`: Opponent cards put to sleep (target: ≥1 per turn)
- `efficiency_rating`: optimal / acceptable / wasteful
- `meets_expectations()`: Boolean + reason string

## What This Replaces

Before Phase 2:
```bash
# Start backend
cd backend && python run_server.py

# Start frontend
cd frontend && npm run dev

# Manually play 2 turns
# Observe AI behavior
# Check if it's reasonable
```

After Phase 2:
```bash
# Run automated test
cd backend && python scripts/run_standard_scenario.py
```

Time saved: ~5 minutes per test → ~2 seconds per test

## Next Steps

See [AI_V4_REMEDIATION_PLAN.md](../../docs/plans/AI_V4_REMEDIATION_PLAN.md) for:
- Phase 3: Prompt content regression tests
- Phase 4: Card metadata centralization
- Phase 5+: Future improvements
