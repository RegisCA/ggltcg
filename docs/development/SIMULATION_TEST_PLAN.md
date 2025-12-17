# Simulation Test Plan

## Overview

This document outlines a structured approach to testing GGLTCG game balance using AI vs AI simulations.

## Testing Principles

### Statistical Significance

For reliable conclusions:
- **Minimum sample size**: 30 games per condition (n=30 is common threshold)
- **Ideal sample size**: 50-100 games for strong statistical power
- **Confidence intervals**: Report with 95% CI when possible

### Control Variables

Always control for:
1. **First-player effect**: P1 gets 2 CC on turn 1, P2 gets 4 CC
2. **Model consistency**: Use same model for both players unless testing models
3. **Deck composition**: Keep decks fixed within a test series

### Test Protocol Template

For each test, document:
- Test ID and date
- Hypothesis being tested
- Configuration (decks, models, iterations)
- Results (wins, losses, draws, avg turns)
- Conclusion and confidence level

---

## Phase 1: Baseline Establishment

### Test 1.1: Aggro Mirror Balance
**Hypothesis**: First-player advantage in Aggro_Rush mirror is ≤60%
- Deck: Aggro_Rush only
- Model: gemini-2.0-flash (both)
- Iterations: 50 games
- Success criteria: P1 win rate between 40-60%

### Test 1.2: Control Mirror Balance
**Hypothesis**: Establish baseline for Control_Ka mirror
- Deck: Control_Ka only
- Model: gemini-2.0-flash (both)
- Iterations: 50 games
- Note: Initial data suggests P2 advantage

### Test 1.3: Cross-Deck Matchup
**Hypothesis**: Understand Aggro vs Control dynamics
- Decks: Aggro_Rush, Control_Ka
- Model: gemini-2.0-flash (both)
- Iterations: 30 games per matchup (90 total)
- Analyze: Does deck choice matter more than turn order?

---

## Phase 2: Model Comparison

### Test 2.1: Model Quality Comparison
**Hypothesis**: Compare decision quality between models
- Deck: Aggro_Rush (mirror)
- Config A: P1=2.0-flash, P2=2.5-flash (30 games)
- Config B: P1=2.5-flash, P2=2.0-flash (30 games)
- Analysis: Combined win rate by model (controlling for position)

### Test 2.2: Model Consistency
**Hypothesis**: Measure variance in model decisions
- Run same mirror test 3 times (30 games each)
- Compare variance between runs
- Lower variance = more consistent/reliable model

---

## Phase 3: Deck Balance Analysis

### Test 3.1: New Deck Validation
When adding a new deck:
1. Mirror match (30 games) - establish baseline
2. Cross-match with each existing deck (30 games each)
3. Calculate matchup matrix

### Test 3.2: Card Impact Testing
To measure a specific card's impact:
1. Create deck variant with/without card
2. Run mirror matches for both variants
3. Run cross-match between variants
4. Analyze win rate delta

---

## Metrics to Track

### Per-Game Metrics
- Winner (P1/P2/Draw)
- Turn count
- Duration (ms)
- CC efficiency (total CC spent / turns)
- Final board state

### Per-Run Aggregate Metrics
- P1 win rate (with 95% CI)
- Average turns to completion
- Draw rate
- Games with errors

### Cross-Run Comparison
- Win rate stability across runs
- Turn distribution (histogram)
- Outlier detection (unusually long/short games)

---

## Best Practices

### Do
- ✅ Run large sample sizes (30+ games minimum)
- ✅ Control for first-player effect in model comparisons
- ✅ Document all test configurations
- ✅ Use consistent model versions
- ✅ Check for errors/draws that might indicate issues

### Don't
- ❌ Draw conclusions from <10 games
- ❌ Compare models without controlling for position
- ❌ Mix different model versions in same test
- ❌ Ignore high draw/error rates

---

## Reporting Template

```markdown
## Test Report: [Test ID]

**Date**: YYYY-MM-DD
**Hypothesis**: [What we're testing]

### Configuration
- Decks: [list]
- Models: P1=[model], P2=[model]
- Iterations: [N]

### Results
| Metric | Value | 95% CI |
|--------|-------|--------|
| P1 Win Rate | X% | [low, high] |
| Avg Turns | X.X | [low, high] |
| Draw Rate | X% | - |

### Conclusion
[Accept/Reject hypothesis, confidence level, next steps]
```

---

## Future Enhancements

1. **Automated reporting**: Generate test reports from simulation results
2. **Statistical analysis**: Built-in CI calculation and significance tests
3. **Visualization**: Turn distribution charts, win rate trends
4. **Regression testing**: Automated balance checks before releases
