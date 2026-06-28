# AI Standard Scenario Tests

This directory contains automated regression tests for the AI player (enum
enumerator + Gemini strategic selection — see
[AI_CURRENT_STATE.md](../../docs/development/ai/AI_CURRENT_STATE.md)).

## Purpose

Replace the manual "play 2 turns, check if AI is reasonable" workflow with
automated tests that:

- Validate Charge efficiency (waste ≤1 Charge per turn)
- Validate damage output (break ≥1 card per turn)
- Catch prompt/enumerator regressions automatically

## Running Tests

```bash
cd backend
pytest tests/test_ai_enum_scenario.py -v -s
```

**Note**: These tests require a valid `GOOGLE_API_KEY` in `backend/.env`
(the strategic-selection call hits Gemini). Without it, tests are skipped
(not failed).

> `scripts/run_standard_scenario.py` predates the enum architecture and is
> currently broken (it constructs `TurnPlanner` with the removed `ai_version`
> param). Use the pytest suite above for manual verification instead.

## Understanding Test Results

### ✅ Tests Pass

The AI is performing at or above baseline expectations. This doesn't mean
perfect play, just that it meets minimum quality gates.

### ❌ Tests Fail

The AI is underperforming. Common causes:

- Prompt regression (check recent changes to `strategic_selector.py`)
- Enumerator regression (check `enumerator.py::enumerate_sequences`)
- LLM variability (same prompt can produce different results)
- Model change (different Gemini model may behave differently)

## LLM Variability

**Important**: These tests involve one Gemini call per turn (strategic
selection), which is non-deterministic — the candidate sequences themselves
are deterministic (computed by the enumerator), but which one gets picked can
vary slightly across runs. Tests are designed to:

1. Pass when the AI meets minimum quality gates
2. Fail when the AI underperforms (catching regressions)
3. Provide detailed metrics to understand why

## Metrics Used

Tests use `TurnMetrics` from `game_engine.ai.quality_metrics`:

- `charge_wasted`: Charge remaining at end of turn (target: ≤1)
- `cards_broken`: Opponent cards put to break (target: ≥1 per turn)
- `efficiency_rating`: optimal / acceptable / wasteful
- `meets_expectations()`: Boolean + reason string
