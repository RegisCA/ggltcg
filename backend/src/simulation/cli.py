"""
CLI for running GGLTCG simulations.

Provides convenient commands for common simulation scenarios:
- baseline: standard decks, AI mirror match
- compare: cross-model comparison (e.g. flash-lite vs flash)
- test-deck: Test a custom deck against others
- quick: Fast test with reduced iterations
- resume: resume a paused/budget-exhausted run
- status: check on a run's progress and budget

Usage:
    python -m simulation.cli baseline --iterations 10
    python -m simulation.cli compare --model1 gemini-flash-lite-latest --model2 gemini-2.5-flash-lite

Multi-day throttled batch runs:
    python -m simulation.cli baseline --iterations 200 --rpm 30 --daily-budget 2000
    python -m simulation.cli resume 42 --rpm 30 --daily-budget 2000
See README.md for the long-lived-process and cron/launchd recommendations.
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import click

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulation.orchestrator import SimulationOrchestrator
from simulation.config import SimulationConfig, SimulationStatus
from simulation.deck_loader import load_simulation_decks_dict
from simulation.reporter import SimulationReporter

logger = logging.getLogger(__name__)

# Exit code used when a run pauses on budget exhaustion and --no-wait was
# passed. Distinct from a hard failure (1) so cron/launchd wrappers can
# tell "not done yet, try again later" apart from a real error. This is the
# BSD sysexits.h EX_TEMPFAIL value.
EX_TEMPFAIL = 75

# Extra slack (seconds) added on top of the limiter's reported resets_at, to
# absorb clock skew and the limiter's own rollover bookkeeping.
_RESET_SLACK_SECONDS = 120


# Preset deck configurations
PRESET_DECKS = {
    "baseline": ["Aggro_Rush", "Control_Ka", "Tempo_Charge", "Disruption"],
    "top2": ["Aggro_Rush", "Tempo_Charge"],
    "all": None,  # Will load all from CSV
}


def _throttle_options(f):
    """Shared --rpm / --daily-budget / --wait options for the run commands."""
    f = click.option(
        '--wait/--no-wait', default=True,
        help='Wait through budget-exhaustion pauses and auto-resume (default: --wait)'
    )(f)
    f = click.option(
        '--daily-budget', type=int, default=None,
        help='Daily API request budget; the run pauses (budget_exhausted) once reached'
    )(f)
    f = click.option(
        '--rpm', type=int, default=None,
        help='Requests-per-minute cap for the AI rate limiter'
    )(f)
    return f


@click.group()
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """GGLTCG Simulation CLI - Run AI vs AI simulations with ease."""
    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)


@cli.command()
@click.option('--iterations', '-i', default=10, help='Games per matchup (default: 10)')
@click.option('--parallel', '-p', default=10, help='Parallel workers (default: 10)')
@click.option('--model', '-m', default='gemini-2.5-flash-lite', help='AI model to use')
@click.option('--decks', '-d', default='baseline', help='Deck preset: baseline, top2, all')
@_throttle_options
def baseline(iterations, parallel, model, decks, rpm, daily_budget, wait):
    """
    Run a baseline AI mirror match with standard decks.

    This measures current AI performance against itself
    to establish a performance baseline.

    Example:
        python -m simulation.cli baseline --iterations 20
    """
    click.echo(f"🎮 Running baseline simulation")
    click.echo(f"   Model: {model}")
    click.echo(f"   Decks: {decks}")
    click.echo(f"   Iterations: {iterations} per matchup")
    click.echo()

    # Get deck names
    deck_names = _get_deck_names(decks)

    # Create configuration
    config = SimulationConfig(
        deck_names=deck_names,
        player1_model=model,
        player2_model=model,
        iterations_per_matchup=iterations,
        rpm=rpm,
        daily_request_budget=daily_budget,
    )

    # Run simulation
    _run_simulation_with_progress(config, parallel, wait=wait)


@cli.command()
@click.option('--model1', default='gemini-flash-lite-latest', help='Player 1 model')
@click.option('--model2', default='gemini-2.5-flash-lite', help='Player 2 model')
@click.option('--iterations', '-i', default=10, help='Games per matchup (default: 10)')
@click.option('--parallel', '-p', default=10, help='Parallel workers (default: 10)')
@click.option('--decks', '-d', default='baseline', help='Deck preset: baseline, top2, all')
@_throttle_options
def compare(model1, model2, iterations, parallel, decks, rpm, daily_budget, wait):
    """
    Run a cross-model comparison.

    Compares two Gemini models head-to-head to measure relative performance.
    Useful for evaluating a candidate model swap.

    Example:
        python -m simulation.cli compare --model1 gemini-flash-lite-latest --model2 gemini-2.5-flash-lite --iterations 20
    """
    click.echo(f"⚔️  Running comparison simulation")
    click.echo(f"   Player 1: {model1}")
    click.echo(f"   Player 2: {model2}")
    click.echo(f"   Decks: {decks}")
    click.echo(f"   Iterations: {iterations} per matchup")
    click.echo()

    # Get deck names
    deck_names = _get_deck_names(decks)

    # Create configuration
    config = SimulationConfig(
        deck_names=deck_names,
        player1_model=model1,
        player2_model=model2,
        iterations_per_matchup=iterations,
        rpm=rpm,
        daily_request_budget=daily_budget,
    )

    # Run simulation
    _run_simulation_with_progress(config, parallel, wait=wait)


@cli.command()
@click.argument('deck_names', nargs=-1, required=True)
@click.option('--against', '-a', default='baseline', help='Decks to test against (preset name)')
@click.option('--iterations', '-i', default=10, help='Games per matchup (default: 10)')
@click.option('--parallel', '-p', default=10, help='Parallel workers (default: 10)')
@click.option('--model', '-m', default='gemini-2.5-flash-lite', help='AI model to use')
@_throttle_options
def test_deck(deck_names, against, iterations, parallel, model, rpm, daily_budget, wait):
    """
    Test specific decks against a set of opponents.

    Useful for testing new deck configurations or strategies.

    Example:
        python -m simulation.cli test-deck Custom_Aggro --against baseline
        python -m simulation.cli test-deck Deck1 Deck2 --against top2
    """
    click.echo(f"🧪 Testing custom decks")
    click.echo(f"   Test decks: {', '.join(deck_names)}")
    click.echo(f"   Against: {against}")
    click.echo(f"   Iterations: {iterations} per matchup")
    click.echo()

    # Get opponent decks
    opponent_decks = _get_deck_names(against)

    # Combine test decks and opponents
    all_decks = list(deck_names) + opponent_decks

    # Create configuration
    config = SimulationConfig(
        deck_names=all_decks,
        player1_model=model,
        player2_model=model,
        iterations_per_matchup=iterations,
        rpm=rpm,
        daily_request_budget=daily_budget,
    )

    # Run simulation
    _run_simulation_with_progress(config, parallel, wait=wait)


@cli.command()
@click.argument('deck1')
@click.argument('deck2')
@click.option('--iterations', '-i', default=5, help='Number of games (default: 5)')
@click.option('--model', '-m', default='gemini-2.5-flash-lite', help='AI model to use')
@_throttle_options
def quick(deck1, deck2, iterations, model, rpm, daily_budget, wait):
    """
    Quick test between two specific decks.

    Runs a small number of games for fast iteration and debugging.

    Example:
        python -m simulation.cli quick Aggro_Rush Control_Ka --iterations 3
    """
    click.echo(f"⚡ Quick test")
    click.echo(f"   {deck1} vs {deck2}")
    click.echo(f"   Iterations: {iterations}")
    click.echo()

    # Create configuration
    config = SimulationConfig(
        deck_names=[deck1, deck2],
        player1_model=model,
        player2_model=model,
        iterations_per_matchup=iterations,
        rpm=rpm,
        daily_request_budget=daily_budget,
    )

    # Run simulation
    _run_simulation_with_progress(config, parallel_games=5, wait=wait)  # Fewer parallel workers for quick tests


@cli.command()
@click.argument('run_id', type=int)
@click.option('--parallel', '-p', default=None, type=int, help='Parallel workers override (default: config value)')
@_throttle_options
def resume(run_id, parallel, rpm, daily_budget, wait):
    """
    Resume a paused, budget-exhausted, or failed simulation run.

    Example:
        python -m simulation.cli resume 42
        python -m simulation.cli resume 42 --rpm 30 --daily-budget 2000 --no-wait
    """
    orchestrator = SimulationOrchestrator()

    try:
        current = orchestrator.get_status(run_id)
    except ValueError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)

    resumable_statuses = {"budget_exhausted", "paused", "failed", "running"}
    if current["status"] not in resumable_statuses:
        click.echo(
            f"❌ Cannot resume run {run_id} with status '{current['status']}'; "
            f"must be one of {sorted(resumable_statuses)}",
            err=True,
        )
        sys.exit(1)

    if rpm is not None or daily_budget is not None:
        _apply_config_overrides(orchestrator, run_id, rpm=rpm, daily_request_budget=daily_budget)

    click.echo(f"▶️  Resuming simulation run #{run_id}")
    click.echo(f"   Progress so far: {current['completed_games']}/{current['total_games']} games")
    click.echo()

    try:
        _execute_and_report(orchestrator, run_id, parallel, wait=wait, started=False)
    except ValueError as e:
        click.echo(f"❌ Validation error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Simulation failed: {e}", err=True)
        logger.exception("Simulation error")
        sys.exit(1)


@cli.command()
@click.argument('run_id', type=int)
def status(run_id):
    """
    Show status, progress, and budget info for a simulation run.

    Example:
        python -m simulation.cli status 42
    """
    orchestrator = SimulationOrchestrator()

    try:
        st = orchestrator.get_status(run_id)
    except ValueError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)

    click.echo(f"📊 Run #{run_id} - {st['status']}")
    click.echo(
        f"   Progress: {st['completed_games']}/{st['total_games']} games "
        f"({st['progress_pct']}%)"
    )
    if st.get('error_message'):
        click.echo(f"   Error: {st['error_message']}")

    budget = st.get('budget') or {}
    if budget.get('rpm') is not None or budget.get('daily_budget') is not None:
        click.echo("   Budget:")
        if budget.get('rpm') is not None:
            click.echo(f"     RPM: {budget['rpm']}")
        if budget.get('daily_budget') is not None:
            click.echo(f"     Daily: {budget.get('used_today')}/{budget['daily_budget']}")
        if budget.get('resets_at'):
            click.echo(f"     Resets at: {budget['resets_at']}")

    if st['status'] in ("completed", "budget_exhausted", "paused", "running"):
        try:
            results_data = orchestrator.get_results(run_id)
            matchup_stats = results_data.get('matchup_stats') or {}
            if matchup_stats:
                click.echo()
                click.echo("   Matchup summary:")
                for key, stats in sorted(matchup_stats.items()):
                    p1_rate = stats.get('deck1_win_rate', 0) * 100
                    p2_rate = stats.get('deck2_win_rate', 0) * 100
                    click.echo(
                        f"     {key}: {stats.get('games_played', 0)} games "
                        f"(P1 {p1_rate:.1f}% / P2 {p2_rate:.1f}%)"
                    )
        except Exception:
            logger.exception("Failed to load matchup summary for status command")


@cli.command()
@click.option('--limit', '-l', default=10, help='Number of recent runs to show')
def list_runs(limit):
    """
    List recent simulation runs.

    Shows the status and configuration of recent simulations.

    Example:
        python -m simulation.cli list-runs --limit 20
    """
    orchestrator = SimulationOrchestrator()
    runs = orchestrator.list_runs(limit=limit)

    if not runs:
        click.echo("No simulation runs found.")
        return

    click.echo(f"📊 Recent simulation runs (showing {len(runs)}):\n")

    for run in runs:
        status_icon = {
            'completed': '✅',
            'running': '🔄',
            'pending': '⏳',
            'failed': '❌',
            'cancelled': '🚫',
            'paused': '⏸️',
            'budget_exhausted': '⏸️',
        }.get(run['status'], '❓')

        click.echo(f"{status_icon} Run #{run['run_id']} - {run['status']}")
        click.echo(f"   Games: {run['completed_games']}/{run['total_games']}")
        click.echo(f"   Config: {run['config'].get('deck_names', [])}")
        click.echo(f"   Created: {run['created_at']}")
        click.echo()


@cli.command()
def list_decks():
    """
    List all available simulation decks.

    Shows deck names and card compositions from simulation_decks.csv.

    Example:
        python -m simulation.cli list-decks
    """
    try:
        decks = load_simulation_decks_dict()

        click.echo(f"🎴 Available simulation decks ({len(decks)} total):\n")

        for name, deck in sorted(decks.items()):
            click.echo(f"  {name}")
            click.echo(f"    Description: {deck.description or 'No description'}")
            click.echo(f"    Cards: {', '.join(deck.cards)}")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error loading decks: {e}", err=True)
        sys.exit(1)


# Helper functions

def _get_deck_names(preset: str) -> list[str]:
    """
    Get deck names from a preset or load all decks.

    Args:
        preset: Preset name (baseline, top2, all) or comma-separated deck names

    Returns:
        List of deck names
    """
    if preset in PRESET_DECKS:
        if PRESET_DECKS[preset] is None:
            # Load all decks
            decks = load_simulation_decks_dict()
            return list(decks.keys())
        else:
            return PRESET_DECKS[preset]

    # Treat as comma-separated deck names
    return [name.strip() for name in preset.split(',')]


def _apply_config_overrides(
    orchestrator: SimulationOrchestrator, run_id: int, rpm=None, daily_request_budget=None
) -> None:
    """
    Persist rpm/daily_request_budget overrides onto a run's stored config,
    so a resumed run picks up new throttle settings.
    """
    from api.db_models import SimulationRunModel  # local import: keeps CLI import light

    db = orchestrator._get_db()
    run = db.query(SimulationRunModel).filter(SimulationRunModel.id == run_id).first()
    if run is None:
        return
    cfg = dict(run.config or {})
    if rpm is not None:
        cfg["rpm"] = rpm
    if daily_request_budget is not None:
        cfg["daily_request_budget"] = daily_request_budget
    run.config = cfg
    db.commit()


def _run_simulation_with_progress(config: SimulationConfig, parallel_games: int = 10, wait: bool = True):
    """
    Start a new simulation and run it (through any budget-exhaustion pauses
    if `wait` is True) to completion, printing progress and a final report.

    Args:
        config: Simulation configuration
        parallel_games: Number of parallel workers
        wait: If True, sleep through budget-exhaustion pauses and
            auto-resume until the run completes/fails/cancels. If False,
            print the resume command and exit with EX_TEMPFAIL as soon as
            the run pauses on budget exhaustion.
    """
    orchestrator = SimulationOrchestrator()

    try:
        # Start simulation
        run_id = orchestrator.start_simulation(config)
        click.echo(f"✨ Started simulation run #{run_id}")
        click.echo(f"   Total games: {config.total_games()}")
        click.echo(f"   Parallel workers: {parallel_games}")
        click.echo()

        _execute_and_report(orchestrator, run_id, parallel_games, wait=wait, started=True)

    except ValueError as e:
        click.echo(f"❌ Validation error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Simulation failed: {e}", err=True)
        logger.exception("Simulation error")
        sys.exit(1)


def _execute_and_report(
    orchestrator: SimulationOrchestrator,
    run_id: int,
    parallel_games,
    wait: bool = True,
    started: bool = True,
) -> None:
    """
    Run (or resume) a simulation, looping through budget-exhaustion pauses
    while `wait` is True, then print the final summary/report.

    Args:
        orchestrator: The orchestrator instance to run against
        run_id: ID of the simulation run
        parallel_games: Parallel worker override (may be None)
        wait: Whether to sleep through budget-exhaustion pauses
        started: True if this run was just created (affects run vs. resume
            call for the first iteration)
    """
    click.echo("Running simulation...")
    start_time = time.time()

    if started:
        result = orchestrator.run_simulation(run_id, parallel_games=parallel_games)
    else:
        result = orchestrator.resume_simulation(run_id, parallel_games=parallel_games)

    while result.status == SimulationStatus.BUDGET_EXHAUSTED:
        budget = orchestrator.get_status(run_id).get("budget") or {}
        click.echo()
        click.echo(f"⏸️  Run #{run_id} paused: daily API budget exhausted.")
        click.echo(f"   Used: {budget.get('used_today')}/{budget.get('daily_budget')}")
        click.echo(f"   Resets at: {result.resets_at.isoformat() if result.resets_at else 'unknown'}")

        if not wait:
            click.echo()
            click.echo(f"   Resume later with: python -m simulation.cli resume {run_id}")
            sys.exit(EX_TEMPFAIL)

        sleep_seconds = _RESET_SLACK_SECONDS
        if result.resets_at is not None:
            resets_at = result.resets_at
            now = datetime.now(resets_at.tzinfo) if resets_at.tzinfo else datetime.now()
            sleep_seconds = max(0.0, (resets_at - now).total_seconds()) + _RESET_SLACK_SECONDS

        click.echo(f"   Waiting {sleep_seconds / 60:.1f} minutes for the budget to reset...")
        time.sleep(sleep_seconds)

        click.echo("Resuming simulation...")
        result = orchestrator.resume_simulation(run_id, parallel_games=parallel_games)

    elapsed = time.time() - start_time

    # Display results
    click.echo()
    click.echo("=" * 60)
    if result.status == SimulationStatus.COMPLETED:
        click.echo(f"✅ Simulation complete! (Run #{run_id})")
    elif result.status == SimulationStatus.PAUSED:
        click.echo(f"⏸️  Simulation paused. (Run #{run_id})")
        click.echo(f"   Resume later with: python -m simulation.cli resume {run_id}")
    elif result.status == SimulationStatus.FAILED:
        click.echo(f"❌ Simulation failed. (Run #{run_id})")
        if result.error_message:
            click.echo(f"   Error: {result.error_message}")
    else:
        click.echo(f"⏹️  Simulation ended with status '{result.status.value}'. (Run #{run_id})")

    click.echo(f"   Duration: {elapsed:.1f}s")
    click.echo(f"   Completed: {result.completed_games}/{result.total_games} games")
    click.echo()

    # Summary statistics
    results_data = orchestrator.get_results(run_id)
    _display_summary(results_data)

    # Auto-generate report
    click.echo()
    click.echo("📝 Generating report...")
    try:
        reporter = SimulationReporter(results_data)
        report_path = reporter.save_report()
        click.echo(f"   Report saved: {report_path}")
    except Exception as e:
        click.echo(f"   ⚠️  Report generation failed: {e}")
        logger.exception("Report generation error")

    click.echo()
    click.echo(f"💾 Full results available via API: GET /admin/simulation/runs/{run_id}/results")
    click.echo(f"📊 View in admin UI: http://localhost:8000/admin.html")

    if result.status == SimulationStatus.FAILED:
        sys.exit(1)


def _display_summary(results: dict):
    """Display a summary of simulation results."""
    games = results.get('games', [])
    if not games:
        return

    # Count outcomes
    p1_wins = sum(1 for g in games if g['outcome'] == 'player1_win')
    p2_wins = sum(1 for g in games if g['outcome'] == 'player2_win')
    draws = sum(1 for g in games if g['outcome'] == 'draw')
    errors = sum(1 for g in games if g.get('error_message'))

    total = len(games)

    click.echo("📈 Results Summary:")
    click.echo(f"   Player 1 Wins: {p1_wins} ({p1_wins/total*100:.1f}%)")
    click.echo(f"   Player 2 Wins: {p2_wins} ({p2_wins/total*100:.1f}%)")
    if draws > 0:
        click.echo(f"   Draws: {draws} ({draws/total*100:.1f}%)")
    if errors > 0:
        click.echo(f"   ⚠️  Errors: {errors}")

    # Average stats
    avg_turns = sum(g['turn_count'] for g in games) / total if games else 0
    click.echo(f"   Avg Turns: {avg_turns:.1f}")

    # Charge stats
    avg_p1_charge = sum(g.get('p1_charge_gained', 0) for g in games) / total if games else 0
    avg_p2_charge = sum(g.get('p2_charge_gained', 0) for g in games) / total if games else 0
    click.echo(f"   Avg Charge Generated: P1={avg_p1_charge:.1f}, P2={avg_p2_charge:.1f}")


if __name__ == '__main__':
    cli()
