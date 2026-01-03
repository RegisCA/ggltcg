"""
Auto-report generator for simulation results.

Generates markdown reports with:
- Overall statistics (win rates, draws, errors)
- Matchup matrix (deck vs deck)
- CC efficiency analysis
- Notable games (fastest wins, longest games)
- First-player advantage analysis
"""

import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SimulationReporter:
    """Generates formatted reports from simulation results."""
    
    def __init__(self, results: dict):
        """
        Initialize reporter with simulation results.
        
        Args:
            results: Results dictionary from SimulationOrchestrator.get_results()
        """
        self.results = results
        self.run_id = results['run_id']
        self.config = results['config']
        self.games = results['games']
    
    def generate_markdown_report(self) -> str:
        """
        Generate a comprehensive markdown report.
        
        Returns:
            Markdown formatted report string
        """
        sections = [
            self._header(),
            self._configuration(),
            self._overall_statistics(),
            self._matchup_matrix(),
            self._cc_analysis(),
            self._first_player_advantage(),
            self._notable_games(),
            self._footer(),
        ]
        
        return "\n\n".join(sections)
    
    def generate_summary_json(self) -> dict:
        """
        Generate a summary JSON for programmatic consumption.
        
        Returns:
            Dictionary with key statistics
        """
        games = self.games
        total = len(games)
        
        return {
            "run_id": self.run_id,
            "total_games": total,
            "completed_games": self.results['completed_games'],
            "status": self.results['status'],
            "config": self.config,
            "overall_stats": self._calculate_overall_stats(),
            "matchup_stats": self._calculate_matchup_stats(),
            "cc_stats": self._calculate_cc_stats(),
            "first_player_advantage": self._calculate_first_player_advantage(),
        }
    
    def save_report(self, output_dir: str = "reports") -> str:
        """
        Save markdown report to file.
        
        Args:
            output_dir: Directory to save report (default: "reports")
            
        Returns:
            Path to saved report file
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"simulation_run_{self.run_id}_{timestamp}.md"
        filepath = Path(output_dir) / filename
        
        report = self.generate_markdown_report()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Saved simulation report to {filepath}")
        return str(filepath)
    
    # Report sections
    
    def _header(self) -> str:
        """Generate report header."""
        return f"""# Simulation Run #{self.run_id} Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Status**: {self.results['status']}  
**Games**: {self.results['completed_games']}/{self.results['total_games']}
"""
    
    def _configuration(self) -> str:
        """Generate configuration section."""
        config = self.config
        
        lines = [
            "## Configuration",
            "",
            f"- **Player 1**: AI v{config.get('player1_ai_version', '?')} ({config.get('player1_model', '?')})",
            f"- **Player 2**: AI v{config.get('player2_ai_version', '?')} ({config.get('player2_model', '?')})",
            f"- **Iterations per matchup**: {config.get('iterations_per_matchup', '?')}",
            f"- **Max turns**: {config.get('max_turns', '?')}",
            f"- **Decks**: {', '.join(config.get('deck_names', []))}",
        ]
        
        return "\n".join(lines)
    
    def _overall_statistics(self) -> str:
        """Generate overall statistics section."""
        stats = self._calculate_overall_stats()
        
        lines = [
            "## Overall Statistics",
            "",
            f"- **Player 1 Wins**: {stats['p1_wins']} ({stats['p1_win_rate']:.1%})",
            f"- **Player 2 Wins**: {stats['p2_wins']} ({stats['p2_win_rate']:.1%})",
            f"- **Draws**: {stats['draws']} ({stats['draw_rate']:.1%})",
        ]
        
        if stats['errors'] > 0:
            lines.append(f"- **⚠️ Errors**: {stats['errors']}")
        
        lines.extend([
            "",
            f"**Average Game Length**: {stats['avg_turns']:.1f} turns  ",
            f"**Average Duration**: {stats['avg_duration_ms']/1000:.1f}s",
        ])
        
        return "\n".join(lines)
    
    def _matchup_matrix(self) -> str:
        """Generate matchup matrix section."""
        matchups = self._calculate_matchup_stats()
        
        lines = [
            "## Matchup Matrix",
            "",
            "Player 1 win rates by deck matchup:",
            "",
            "| Player 1 Deck | Player 2 Deck | P1 Wins | P2 Wins | Draws | P1 Win Rate |",
            "|---------------|---------------|---------|---------|-------|-------------|",
        ]
        
        for matchup_key, stats in sorted(matchups.items()):
            lines.append(
                f"| {stats['deck1']} | {stats['deck2']} | "
                f"{stats['p1_wins']} | {stats['p2_wins']} | {stats['draws']} | "
                f"{stats['p1_win_rate']:.1%} |"
            )
        
        return "\n".join(lines)
    
    def _cc_analysis(self) -> str:
        """Generate CC efficiency analysis section."""
        stats = self._calculate_cc_stats()
        
        lines = [
            "## CC (Charge Counter) Analysis",
            "",
            "**Note**: CC gained represents total resources generated (higher in longer games).  ",
            "CC efficiency should be evaluated in context of game length and outcomes.",
            "",
            f"- **Avg CC Generated (Player 1)**: {stats['avg_p1_cc_gained']:.1f}",
            f"- **Avg CC Generated (Player 2)**: {stats['avg_p2_cc_gained']:.1f}",
            f"- **Avg CC Spent (Player 1)**: {stats['avg_p1_cc_spent']:.1f}",
            f"- **Avg CC Spent (Player 2)**: {stats['avg_p2_cc_spent']:.1f}",
        ]
        
        if stats.get('winner_cc_avg') and stats.get('loser_cc_avg'):
            lines.extend([
                "",
                "### Winners vs Losers",
                f"- **Winners avg CC generated**: {stats['winner_cc_avg']:.1f}",
                f"- **Losers avg CC generated**: {stats['loser_cc_avg']:.1f}",
                "",
                "*Winners often generate more CC due to playing longer games.*",
            ])
        
        return "\n".join(lines)
    
    def _first_player_advantage(self) -> str:
        """Generate first-player advantage analysis."""
        stats = self._calculate_first_player_advantage()
        
        lines = [
            "## First Player Advantage",
            "",
            f"- **Player 1 (always goes first) win rate**: {stats['p1_win_rate']:.1%}",
            f"- **Expected rate (no advantage)**: 50.0%",
            f"- **Advantage**: {stats['advantage']:.1f} percentage points",
        ]
        
        if abs(stats['advantage']) > 5:
            lines.append("")
            if stats['advantage'] > 0:
                lines.append("⚠️ Significant first-player advantage detected (>5%).")
            else:
                lines.append("⚠️ Significant second-player advantage detected (>5%).")
        
        return "\n".join(lines)
    
    def _notable_games(self) -> str:
        """Generate notable games section."""
        games = self.games
        
        if not games:
            return "## Notable Games\n\n*No games completed.*"
        
        # Find notable games
        fastest = min(games, key=lambda g: g['turn_count'])
        longest = max(games, key=lambda g: g['turn_count'])
        
        lines = [
            "## Notable Games",
            "",
            f"**Fastest Game**: #{fastest['game_number']} - {fastest['deck1_name']} vs {fastest['deck2_name']}  ",
            f"  Winner: {fastest['winner_deck'] or 'Draw'}, Turns: {fastest['turn_count']}",
            "",
            f"**Longest Game**: #{longest['game_number']} - {longest['deck1_name']} vs {longest['deck2_name']}  ",
            f"  Winner: {longest['winner_deck'] or 'Draw'}, Turns: {longest['turn_count']}",
        ]
        
        # Errors
        error_games = [g for g in games if g.get('error_message')]
        if error_games:
            lines.extend([
                "",
                f"**Games with Errors**: {len(error_games)}",
            ])
            for game in error_games[:3]:  # Show first 3 errors
                lines.append(f"  - Game #{game['game_number']}: {game['error_message'][:80]}...")
        
        return "\n".join(lines)
    
    def _footer(self) -> str:
        """Generate report footer."""
        return f"""---

**Report generated by GGLTCG Simulation System**  
Run ID: {self.run_id}  
Full results available via API: `GET /admin/simulation/runs/{self.run_id}/results`
"""
    
    # Calculation methods
    
    def _calculate_overall_stats(self) -> dict:
        """Calculate overall statistics."""
        games = self.games
        total = len(games)
        
        if total == 0:
            return {
                'p1_wins': 0, 'p2_wins': 0, 'draws': 0, 'errors': 0,
                'p1_win_rate': 0, 'p2_win_rate': 0, 'draw_rate': 0,
                'avg_turns': 0, 'avg_duration_ms': 0,
            }
        
        p1_wins = sum(1 for g in games if g['outcome'] == 'player1_win')
        p2_wins = sum(1 for g in games if g['outcome'] == 'player2_win')
        draws = sum(1 for g in games if g['outcome'] == 'draw')
        errors = sum(1 for g in games if g.get('error_message'))
        
        return {
            'p1_wins': p1_wins,
            'p2_wins': p2_wins,
            'draws': draws,
            'errors': errors,
            'p1_win_rate': p1_wins / total,
            'p2_win_rate': p2_wins / total,
            'draw_rate': draws / total,
            'avg_turns': sum(g['turn_count'] for g in games) / total,
            'avg_duration_ms': sum(g['duration_ms'] for g in games) / total,
        }
    
    def _calculate_matchup_stats(self) -> dict:
        """Calculate matchup-specific statistics."""
        matchups = defaultdict(lambda: {
            'deck1': '', 'deck2': '',
            'p1_wins': 0, 'p2_wins': 0, 'draws': 0, 'total': 0
        })
        
        for game in self.games:
            key = f"{game['deck1_name']}_vs_{game['deck2_name']}"
            
            matchups[key]['deck1'] = game['deck1_name']
            matchups[key]['deck2'] = game['deck2_name']
            matchups[key]['total'] += 1
            
            if game['outcome'] == 'player1_win':
                matchups[key]['p1_wins'] += 1
            elif game['outcome'] == 'player2_win':
                matchups[key]['p2_wins'] += 1
            else:
                matchups[key]['draws'] += 1
        
        # Calculate win rates
        for key in matchups:
            total = matchups[key]['total']
            if total > 0:
                matchups[key]['p1_win_rate'] = matchups[key]['p1_wins'] / total
            else:
                matchups[key]['p1_win_rate'] = 0
        
        return dict(matchups)
    
    def _calculate_cc_stats(self) -> dict:
        """Calculate CC-related statistics."""
        games = self.games
        total = len(games)
        
        if total == 0:
            return {}
        
        stats = {
            'avg_p1_cc_gained': sum(g.get('p1_cc_gained', 0) for g in games) / total,
            'avg_p2_cc_gained': sum(g.get('p2_cc_gained', 0) for g in games) / total,
            'avg_p1_cc_spent': sum(g.get('p1_cc_spent', 0) for g in games) / total,
            'avg_p2_cc_spent': sum(g.get('p2_cc_spent', 0) for g in games) / total,
        }
        
        # Winners vs losers
        winner_cc = []
        loser_cc = []
        
        for game in games:
            if game['outcome'] == 'player1_win':
                winner_cc.append(game.get('p1_cc_gained', 0))
                loser_cc.append(game.get('p2_cc_gained', 0))
            elif game['outcome'] == 'player2_win':
                winner_cc.append(game.get('p2_cc_gained', 0))
                loser_cc.append(game.get('p1_cc_gained', 0))
        
        if winner_cc:
            stats['winner_cc_avg'] = sum(winner_cc) / len(winner_cc)
            stats['loser_cc_avg'] = sum(loser_cc) / len(loser_cc)
        
        return stats
    
    def _calculate_first_player_advantage(self) -> dict:
        """Calculate first-player advantage."""
        games = self.games
        total = len(games)
        
        if total == 0:
            return {'p1_win_rate': 0, 'advantage': 0}
        
        p1_wins = sum(1 for g in games if g['outcome'] == 'player1_win')
        p1_win_rate = p1_wins / total
        advantage = (p1_win_rate - 0.5) * 100  # Percentage points from 50%
        
        return {
            'p1_win_rate': p1_win_rate,
            'advantage': advantage,
        }


def generate_report(run_id: int, orchestrator=None) -> str:
    """
    Convenience function to generate a report for a simulation run.
    
    Args:
        run_id: ID of the simulation run
        orchestrator: Optional SimulationOrchestrator instance
        
    Returns:
        Markdown report string
    """
    if orchestrator is None:
        from simulation.orchestrator import SimulationOrchestrator
        orchestrator = SimulationOrchestrator()
    
    results = orchestrator.get_results(run_id)
    reporter = SimulationReporter(results)
    
    return reporter.generate_markdown_report()


def save_report(run_id: int, output_dir: str = "../../reports", orchestrator=None) -> str:
    """
    Convenience function to generate and save a report.
    
    Args:
        run_id: ID of the simulation run
        output_dir: Directory to save report
        orchestrator: Optional SimulationOrchestrator instance
        
    Returns:
        Path to saved report file
    """
    if orchestrator is None:
        from simulation.orchestrator import SimulationOrchestrator
        orchestrator = SimulationOrchestrator()
    
    results = orchestrator.get_results(run_id)
    reporter = SimulationReporter(results)
    
    return reporter.save_report(output_dir)
