"""
CLI for running GGLTCG simulations.

Provides convenient commands for common simulation scenarios:
- baseline: V4 vs V4 with standard decks
- compare: Cross-version comparison (V4 vs V3)
- test-deck: Test a custom deck against others
- quick: Fast test with reduced iterations

Usage:
    python -m simulation.cli baseline --iterations 10
    python -m simulation.cli compare --v1 4 --v2 3
"""

import logging
import sys
import time
from pathlib import Path

import click

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulation.orchestrator import SimulationOrchestrator
from simulation.config import SimulationConfig
from simulation.deck_loader import load_simulation_decks_dict
from simulation.reporter import SimulationReporter

logger = logging.getLogger(__name__)


# Preset deck configurations
PRESET_DECKS = {
    "baseline": ["Aggro_Rush", "Control_Ka", "Tempo_Charge", "Disruption"],
    "top2": ["Aggro_Rush", "Tempo_Charge"],
    "all": None,  # Will load all from CSV
}


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
def baseline(iterations, parallel, model, decks):
    """
    Run baseline V4 vs V4 test with standard decks.
    
    This measures current V4 AI performance against itself
    to establish a performance baseline.
    
    Example:
        python -m simulation.cli baseline --iterations 20
    """
    click.echo(f"🎮 Running baseline simulation (V4 vs V4)")
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
        player1_ai_version=4,
        player2_ai_version=4,
        iterations_per_matchup=iterations,
    )
    
    # Run simulation
    _run_simulation_with_progress(config, parallel)


@cli.command()
@click.option('--v1', default=4, type=int, help='Player 1 AI version (default: 4)')
@click.option('--v2', default=3, type=int, help='Player 2 AI version (default: 3)')
@click.option('--model1', default='gemini-2.5-flash-lite', help='Player 1 model')
@click.option('--model2', default='gemini-2.5-flash-lite', help='Player 2 model')
@click.option('--iterations', '-i', default=10, help='Games per matchup (default: 10)')
@click.option('--parallel', '-p', default=10, help='Parallel workers (default: 10)')
@click.option('--decks', '-d', default='baseline', help='Deck preset: baseline, top2, all')
def compare(v1, v2, model1, model2, iterations, parallel, decks):
    """
    Run cross-version AI comparison.
    
    Compares two AI versions or models to measure relative performance.
    Useful for evaluating improvements or testing new models.
    
    Example:
        python -m simulation.cli compare --v1 4 --v2 3 --iterations 20
    """
    click.echo(f"⚔️  Running comparison simulation")
    click.echo(f"   Player 1: V{v1} ({model1})")
    click.echo(f"   Player 2: V{v2} ({model2})")
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
        player1_ai_version=v1,
        player2_ai_version=v2,
        iterations_per_matchup=iterations,
    )
    
    # Run simulation
    _run_simulation_with_progress(config, parallel)


@cli.command()
@click.argument('deck_names', nargs=-1, required=True)
@click.option('--against', '-a', default='baseline', help='Decks to test against (preset name)')
@click.option('--iterations', '-i', default=10, help='Games per matchup (default: 10)')
@click.option('--parallel', '-p', default=10, help='Parallel workers (default: 10)')
@click.option('--model', '-m', default='gemini-2.5-flash-lite', help='AI model to use')
@click.option('--ai-version', '-v', default=4, type=int, help='AI version (default: 4)')
def test_deck(deck_names, against, iterations, parallel, model, ai_version):
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
        player1_ai_version=ai_version,
        player2_ai_version=ai_version,
        iterations_per_matchup=iterations,
    )
    
    # Run simulation
    _run_simulation_with_progress(config, parallel)


@cli.command()
@click.argument('deck1')
@click.argument('deck2')
@click.option('--iterations', '-i', default=5, help='Number of games (default: 5)')
@click.option('--model', '-m', default='gemini-2.5-flash-lite', help='AI model to use')
@click.option('--ai-version', '-v', default=4, type=int, help='AI version (default: 4)')
def quick(deck1, deck2, iterations, model, ai_version):
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
        player1_ai_version=ai_version,
        player2_ai_version=ai_version,
        iterations_per_matchup=iterations,
    )
    
    # Run simulation
    _run_simulation_with_progress(config, parallel_games=5)  # Fewer parallel workers for quick tests


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
    runs = orchestrator.list_simulations(limit=limit)
    
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


def _run_simulation_with_progress(config: SimulationConfig, parallel_games: int = 10):
    """
    Run a simulation and display progress.
    
    Args:
        config: Simulation configuration
        parallel_games: Number of parallel workers
    """
    orchestrator = SimulationOrchestrator()
    
    try:
        # Start simulation
        run_id = orchestrator.start_simulation(config)
        click.echo(f"✨ Started simulation run #{run_id}")
        click.echo(f"   Total games: {config.total_games()}")
        click.echo(f"   Parallel workers: {parallel_games}")
        click.echo()
        
        # Run with progress updates
        click.echo("Running simulation...")
        start_time = time.time()
        
        result = orchestrator.run_simulation(run_id, parallel_games=parallel_games)
        
        elapsed = time.time() - start_time
        
        # Display results
        click.echo()
        click.echo("=" * 60)
        click.echo(f"✅ Simulation complete! (Run #{run_id})")
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
        
    except ValueError as e:
        click.echo(f"❌ Validation error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Simulation failed: {e}", err=True)
        logger.exception("Simulation error")
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
    
    # CC stats
    avg_p1_cc = sum(g.get('p1_cc_gained', 0) for g in games) / total if games else 0
    avg_p2_cc = sum(g.get('p2_cc_gained', 0) for g in games) / total if games else 0
    click.echo(f"   Avg CC Generated: P1={avg_p1_cc:.1f}, P2={avg_p2_cc:.1f}")


if __name__ == '__main__':
    cli()
