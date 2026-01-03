# Simulation System Improvements Handoff

**Date**: January 3, 2026  
**For**: Next session implementation  
**Priority**: Medium (quality of life improvements)

---

## Overview

The current simulation system works well but has some friction points that slow down analysis and debugging. This document outlines 5 concrete improvements that would make the simulation workflow significantly easier.

---

## 1. Fix Archer `activate_ability` Edge Case

### Current Issue

During V4 vs V3 simulation testing (Run #12), games with Archer in custom decks resulted in ~55% draws with error: `'GameEngine' object has no attribute 'activate_ability'`.

However, testing shows Archer works correctly in:
- ✅ Production gameplay (via `/activate-ability` endpoint)
- ✅ V4 vs V4 simulations
- ✅ Spot testing with simulation runner

### Root Cause (Suspected)

The error may be:
1. **Transient race condition** in parallel execution
2. **V3-specific issue** (V3 AI might call a non-existent method)
3. **Already fixed** (code has changed since Run #12)

### Investigation Steps

1. Check `LLMPlayerV3` to see if it tries to call `game_engine.activate_ability()` directly
2. Review `TurnPlanner` V3 code paths for activate_ability handling
3. Add defensive checks in simulation runner's `_execute_action` method
4. Run a 40-game V4 vs V3 simulation with Archer to reproduce

### Implementation

```python
# In simulation/runner.py _execute_action method (around line 476)
elif action.action_type == "activate_ability":
    # Current implementation already handles this correctly
    # via EffectRegistry.get_effects() and activated_effect.apply()
    
    # Potential fix: Add try/except with better error reporting
    try:
        # ... existing code ...
        activated_effect.apply(
            game_state,
            target=target_card,
            amount=amount,
            game_engine=engine
        )
    except AttributeError as e:
        logger.error(
            f"Activate ability failed for {card.name}: {e}\n"
            f"Card ID: {card.id}, Effect: {activated_effect}\n"
            f"This might be a V3-specific issue."
        )
        raise
```

**Files to Check**:
- [backend/src/simulation/runner.py](../../backend/src/simulation/runner.py) lines 476-519
- [backend/src/game_engine/ai/turn_planner.py](../../backend/src/game_engine/ai/turn_planner.py)
- [backend/src/game_engine/ai/llm_player.py](../../backend/src/game_engine/ai/llm_player.py) lines 448-460

**Priority**: Low (may already be fixed, hard to reproduce)

---

## 2. Add Simulation CLI with Presets

### Current Workflow (Tedious)

To run a simulation, you must:
1. Write Python code or use curl commands
2. Manually construct `SimulationConfig` objects
3. Poll for completion status
4. Fetch and analyze results separately

### Proposed Improvement

Create a CLI tool for common simulation scenarios:

```bash
# Baseline test (current default decks, V4 vs V4)
python -m simulation.cli baseline --iterations 10

# Cross-version comparison
python -m simulation.cli compare --v1 4 --v2 3 --decks baseline

# Custom deck test against top 2
python -m simulation.cli test-deck --deck-file my_deck.csv --against top2

# Quick test (5 games, fast iteration)
python -m simulation.cli quick --deck1 Aggro_Rush --deck2 Control_Ka
```

### Implementation Outline

**New File**: `backend/src/simulation/cli.py`

```python
"""
CLI for running common simulation scenarios.
"""

import click
from simulation.orchestrator import SimulationOrchestrator
from simulation.config import SimulationConfig

PRESET_DECKS = {
    "baseline": ["Aggro_Rush", "Control_Ka", "Tempo_Charge", "Disruption"],
    "top2": ["Aggro_Rush", "Tempo_Charge"],
    "all": None,  # Load all from CSV
}

@click.group()
def cli():
    """GGLTCG Simulation CLI"""
    pass

@cli.command()
@click.option("--iterations", default=10, help="Games per matchup")
@click.option("--parallel", default=10, help="Parallel workers")
def baseline(iterations, parallel):
    """Run baseline V4 vs V4 test with standard decks."""
    config = SimulationConfig(
        deck_names=PRESET_DECKS["baseline"],
        player1_ai_version=4,
        player2_ai_version=4,
        iterations_per_matchup=iterations,
    )
    
    orchestrator = SimulationOrchestrator()
    run_id = orchestrator.start_simulation(config)
    
    click.echo(f"Starting baseline simulation (Run ID: {run_id})")
    result = orchestrator.run_simulation(run_id, parallel_games=parallel)
    
    # Auto-generate report
    click.echo(f"\n✅ Completed: {result.completed_games} games")
    # ... print summary stats ...

@cli.command()
@click.option("--v1", default=4, help="Player 1 AI version")
@click.option("--v2", default=3, help="Player 2 AI version")
@click.option("--decks", default="baseline", help="Deck preset")
@click.option("--iterations", default=10)
def compare(v1, v2, decks, iterations):
    """Run cross-version AI comparison."""
    # ... implementation ...

if __name__ == "__main__":
    cli()
```

**Benefits**:
- ✅ Common scenarios are 1-line commands
- ✅ Auto-generates reports
- ✅ Easier for non-Python users
- ✅ Can be called from shell scripts

**Priority**: High (saves time on every session)

---

## 3. Auto-Generate Analysis Reports

### Current Workflow

After a simulation completes:
1. Manually query API for results
2. Write Python scripts to analyze data
3. Calculate win rates, matchup matrices, etc.
4. Format for readability

### Proposed Improvement

Automatically generate markdown reports on completion:

```bash
# After simulation completes
$ ls reports/
simulation_run_39_report.md
simulation_run_39_summary.json
```

**Report Contents**:
- Overall win rates (P1/P2/Draw)
- Deck performance table
- Matchup matrix
- CC efficiency stats
- Notable games (shortest, longest, errors)
- V4 metrics (if V4 was used)

### Implementation

**New File**: `backend/src/simulation/reporter.py`

```python
"""
Auto-generate simulation reports.
"""

def generate_report(run_id: int) -> str:
    """Generate markdown report for a completed run."""
    orchestrator = SimulationOrchestrator()
    results = orchestrator.get_results(run_id)
    
    report = [
        f"# Simulation Run {run_id} Report\n",
        f"**Status**: {results['status']}",
        f"**Total Games**: {results['completed_games']}/{results['total_games']}",
        # ... rest of report ...
    ]
    
    return "\n".join(report)

def save_report(run_id: int, output_dir: str = "reports"):
    """Save report to file."""
    report = generate_report(run_id)
    Path(output_dir).mkdir(exist_ok=True)
    with open(f"{output_dir}/simulation_run_{run_id}_report.md", "w") as f:
        f.write(report)
```

**Integration**: Call `save_report()` automatically when `run_simulation()` completes.

**Priority**: Medium (nice to have, saves manual analysis time)

---

## 4. Better Logging Control at Simulation Level

### Current Issue

Logging is controlled at the server level (`LOG_LEVEL=WARNING`), but during simulations we still get verbose DEBUG logs from:
- Game engine internals
- Effect triggers
- AI decision logs

Workaround: Redirect stderr to `/dev/null`, but this hides useful error messages.

### Proposed Improvement

Add simulation-specific logging context:

```python
# In simulation/runner.py __init__
def __init__(self, ..., log_level: str = "WARNING"):
    self.log_level = log_level
    
    # Set logging for simulation-specific loggers
    for logger_name in [
        "game_engine",
        "game_engine.ai",
        "simulation",
    ]:
        logging.getLogger(logger_name).setLevel(log_level)
```

Or use a context manager:

```python
with silence_debug_logs():
    result = runner.run_game(deck1, deck2)
```

### Implementation

**Option A**: Pass `log_level` to `SimulationRunner` constructor  
**Option B**: Use `logging.disable(logging.DEBUG)` in orchestrator  
**Option C**: Redirect logs to a file per simulation run

**Priority**: Medium (current workaround is functional but hacky)

---

## 5. Deck Validation Before Simulation

### Current Issue

If you typo a card name in a custom deck, the simulation starts and then crashes 5 minutes later with `Card not found in templates: "Arcer"` (typo for "Archer").

### Proposed Improvement

Validate all decks before starting simulation:

```python
def validate_deck(deck: DeckConfig, card_templates: dict) -> List[str]:
    """
    Validate a deck configuration.
    
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    # Check deck size
    if len(deck.cards) != 6:
        errors.append(f"Deck must have 6 cards, has {len(deck.cards)}")
    
    # Check all cards exist
    for card_name in deck.cards:
        if card_name not in card_templates:
            errors.append(f"Card not found: '{card_name}'")
            # Suggest similar names
            similar = [c for c in card_templates if card_name.lower() in c.lower()]
            if similar:
                errors.append(f"  Did you mean: {', '.join(similar[:3])}?")
    
    # Check for duplicates
    duplicates = [c for c in deck.cards if deck.cards.count(c) > 1]
    if duplicates:
        errors.append(f"Duplicate cards: {set(duplicates)}")
    
    return errors
```

Call this in `start_simulation()` before creating the database record:

```python
# In orchestrator.py start_simulation()
deck_dict = load_simulation_decks_dict()

for deck_name in config.deck_names:
    if deck_name not in deck_dict:
        raise ValueError(f"Deck '{deck_name}' not found")
    
    # NEW: Validate deck
    deck = deck_dict[deck_name]
    card_templates = load_cards_dict()
    errors = validate_deck(deck, card_templates)
    if errors:
        raise ValueError(
            f"Deck '{deck_name}' validation failed:\n" + "\n".join(errors)
        )
```

**Benefits**:
- ✅ Fail fast (before running 160 games)
- ✅ Better error messages with suggestions
- ✅ Catches typos, missing cards, wrong deck sizes

**Priority**: High (prevents wasted time on invalid simulations)

---

## Summary Priority Matrix

| # | Improvement | Priority | Effort | Impact |
|---|-------------|----------|--------|--------|
| 2 | Simulation CLI | **High** | Medium | High (saves time every session) |
| 5 | Deck Validation | **High** | Low | High (prevents errors early) |
| 3 | Auto Reports | Medium | Medium | Medium (nice to have) |
| 4 | Logging Control | Medium | Low | Medium (cleaner output) |
| 1 | Archer Bug | Low | Low | Low (may already be fixed) |

---

## Recommended Implementation Order

1. **Deck Validation** (30 min) - Quick win, prevents common errors
2. **Simulation CLI** (2 hours) - Most impactful for workflow
3. **Logging Control** (30 min) - Easy improvement
4. **Auto Reports** (1 hour) - Nice polish
5. **Archer Bug** (1 hour) - Only if reproducible

**Total Estimated Time**: 4-5 hours for all improvements

---

## Testing Checklist

After implementing:
- [ ] Run baseline simulation via CLI
- [ ] Test deck validation with typo
- [ ] Verify auto-report generation
- [ ] Check logging levels during simulation
- [ ] Run Archer deck simulation (if bug fix implemented)

---

## Related Files

**To Modify**:
- `backend/src/simulation/orchestrator.py` - Add validation, report generation
- `backend/src/simulation/runner.py` - Add logging control
- `backend/src/simulation/cli.py` - NEW FILE
- `backend/src/simulation/reporter.py` - NEW FILE

**To Reference**:
- `backend/scripts/analyze_simulation_results.py` - Existing analysis logic
- `docs/development/AI_V4_BASELINE.md` - Example report format
