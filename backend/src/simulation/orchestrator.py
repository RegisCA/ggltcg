"""
Simulation orchestrator for managing batch AI vs AI simulations.

This module coordinates running multiple games across deck matchups,
tracks progress, persists results to database, and aggregates statistics.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from api.db_models import SimulationRunModel, SimulationGameModel
from api.database import get_db

from .config import (
    SimulationConfig,
    SimulationResult,
    SimulationStatus,
)
from .deck_loader import load_simulation_decks_dict
from .runner import SimulationRunner

logger = logging.getLogger(__name__)


class SimulationOrchestrator:
    """
    Orchestrates batch simulation runs.
    
    Manages:
    - Loading deck configurations
    - Creating all matchup combinations
    - Running games via SimulationRunner
    - Persisting results to database
    - Progress tracking and status updates
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the orchestrator.
        
        Args:
            db: SQLAlchemy session for persistence. If None, will create per-operation.
        """
        self._db = db
        self._current_run: Optional[SimulationRunModel] = None
        self._result: Optional[SimulationResult] = None
    
    def _get_db(self) -> Session:
        """Get database session."""
        if self._db:
            return self._db
        return next(get_db())
    
    def start_simulation(self, config: SimulationConfig) -> int:
        """
        Start a new simulation run.
        
        Args:
            config: Simulation configuration
            
        Returns:
            Run ID for tracking
        """
        db = self._get_db()
        
        # Load deck configs
        deck_dict = load_simulation_decks_dict()
        
        # Validate deck names
        for deck_name in config.deck_names:
            if deck_name not in deck_dict:
                available = list(deck_dict.keys())
                raise ValueError(
                    f"Deck '{deck_name}' not found. Available: {available}"
                )
        
        # Create database record
        run = SimulationRunModel(
            status="pending",
            config=config.to_dict(),
            total_games=config.total_games(),
            completed_games=0,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        
        self._current_run = run
        
        # Initialize result tracker
        self._result = SimulationResult(
            run_id=run.id,
            config=config,
            status=SimulationStatus.PENDING,
            total_games=config.total_games(),
            completed_games=0,
        )
        
        logger.info(
            f"Created simulation run {run.id}: {config.total_games()} games across "
            f"{len(config.get_matchups())} matchups"
        )
        
        return run.id
    
    def run_simulation(self, run_id: int) -> SimulationResult:
        """
        Execute a simulation run.
        
        This runs synchronously (blocking) until all games complete.
        
        Args:
            run_id: ID of the simulation run to execute
            
        Returns:
            SimulationResult with all game outcomes
        """
        db = self._get_db()
        
        # Load run from database if needed
        if self._current_run is None or self._current_run.id != run_id:
            run = db.query(SimulationRunModel).filter(
                SimulationRunModel.id == run_id
            ).first()
            if run is None:
                raise ValueError(f"Simulation run {run_id} not found")
            self._current_run = run
            
            # Reconstruct config
            config = SimulationConfig(**run.config)
            self._result = SimulationResult(
                run_id=run_id,
                config=config,
                status=SimulationStatus.RUNNING,
                total_games=run.total_games,
                completed_games=run.completed_games,
            )
        
        run = self._current_run
        config = self._result.config
        
        # Update status to running
        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()
        self._result.status = SimulationStatus.RUNNING
        
        try:
            # Load decks
            deck_dict = load_simulation_decks_dict()
            
            # Create runner
            runner = SimulationRunner(
                player1_model=config.player1_model,
                player2_model=config.player2_model,
                max_turns=config.max_turns,
            )
            
            # Get all matchups
            matchups = config.get_matchups()
            game_number = run.completed_games + 1  # Resume from where we left off
            
            for deck1_name, deck2_name in matchups:
                deck1 = deck_dict[deck1_name]
                deck2 = deck_dict[deck2_name]
                
                logger.info(
                    f"Running matchup: {deck1_name} vs {deck2_name} "
                    f"({config.iterations_per_matchup} games)"
                )
                
                for iteration in range(config.iterations_per_matchup):
                    # Check if we should skip (resume support)
                    expected_game = (
                        matchups.index((deck1_name, deck2_name)) * 
                        config.iterations_per_matchup + iteration + 1
                    )
                    if expected_game <= run.completed_games:
                        continue
                    
                    # Run game
                    result = runner.run_game(deck1, deck2, game_number)
                    
                    # Persist game result
                    game_record = SimulationGameModel(
                        run_id=run_id,
                        game_number=game_number,
                        deck1_name=deck1_name,
                        deck2_name=deck2_name,
                        player1_model=config.player1_model,
                        player2_model=config.player2_model,
                        outcome=result.outcome.value,
                        winner_deck=result.winner_deck,
                        turn_count=result.turn_count,
                        duration_ms=result.duration_ms,
                        cc_tracking=[cc.to_dict() for cc in result.cc_tracking],
                        action_log=result.action_log,
                        error_message=result.error_message,
                    )
                    db.add(game_record)
                    
                    # Update run progress
                    run.completed_games = game_number
                    db.commit()
                    
                    # Update in-memory result
                    self._result.add_game_result(result)
                    
                    game_number += 1
            
            # Mark as completed
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.results = {
                "matchup_stats": {
                    k: v.to_dict() 
                    for k, v in self._result.matchup_stats.items()
                }
            }
            db.commit()
            
            self._result.status = SimulationStatus.COMPLETED
            
            logger.info(
                f"Simulation {run_id} completed: {run.completed_games} games"
            )
            
        except Exception as e:
            logger.exception(f"Simulation {run_id} failed: {e}")
            
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            db.commit()
            
            self._result.status = SimulationStatus.FAILED
            self._result.error_message = str(e)
        
        return self._result
    
    def get_status(self, run_id: int) -> dict:
        """
        Get current status of a simulation run.
        
        Args:
            run_id: ID of the simulation run
            
        Returns:
            Status dictionary with progress info
        """
        db = self._get_db()
        
        run = db.query(SimulationRunModel).filter(
            SimulationRunModel.id == run_id
        ).first()
        
        if run is None:
            raise ValueError(f"Simulation run {run_id} not found")
        
        return {
            "run_id": run.id,
            "status": run.status,
            "total_games": run.total_games,
            "completed_games": run.completed_games,
            "progress_pct": round(
                (run.completed_games / run.total_games * 100)
                if run.total_games > 0 else 0,
                1
            ),
            "config": run.config,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "error_message": run.error_message,
        }
    
    def get_results(self, run_id: int) -> dict:
        """
        Get results for a completed simulation run.
        
        Args:
            run_id: ID of the simulation run
            
        Returns:
            Results dictionary with matchup stats and game details
        """
        db = self._get_db()
        
        run = db.query(SimulationRunModel).filter(
            SimulationRunModel.id == run_id
        ).first()
        
        if run is None:
            raise ValueError(f"Simulation run {run_id} not found")
        
        # Get all games for this run
        games = db.query(SimulationGameModel).filter(
            SimulationGameModel.run_id == run_id
        ).order_by(SimulationGameModel.game_number).all()
        
        game_results = []
        for game in games:
            # Calculate total CC spent per player from cc_tracking
            p1_cc_spent = 0
            p2_cc_spent = 0
            if game.cc_tracking:
                for entry in game.cc_tracking:
                    if entry.get('player_id') == 'player1':
                        p1_cc_spent += entry.get('cc_spent', 0)
                    elif entry.get('player_id') == 'player2':
                        p2_cc_spent += entry.get('cc_spent', 0)
            
            game_results.append({
                "game_number": game.game_number,
                "deck1_name": game.deck1_name,
                "deck2_name": game.deck2_name,
                "outcome": game.outcome,
                "winner_deck": game.winner_deck,
                "turn_count": game.turn_count,
                "duration_ms": game.duration_ms,
                "p1_cc_spent": p1_cc_spent,
                "p2_cc_spent": p2_cc_spent,
                "error_message": game.error_message,
            })
        
        return {
            "run_id": run.id,
            "status": run.status,
            "config": run.config,
            "total_games": run.total_games,
            "completed_games": run.completed_games,
            "matchup_stats": run.results.get("matchup_stats", {}) if run.results else {},
            "games": game_results,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
    
    def get_game_details(self, run_id: int, game_number: int) -> dict:
        """
        Get detailed results for a specific game including CC tracking.
        
        Args:
            run_id: ID of the simulation run
            game_number: Game number within the run
            
        Returns:
            Detailed game data including CC tracking and action log
        """
        db = self._get_db()
        
        game = db.query(SimulationGameModel).filter(
            SimulationGameModel.run_id == run_id,
            SimulationGameModel.game_number == game_number,
        ).first()
        
        if game is None:
            raise ValueError(
                f"Game {game_number} not found in run {run_id}"
            )
        
        return {
            "run_id": game.run_id,
            "game_number": game.game_number,
            "deck1_name": game.deck1_name,
            "deck2_name": game.deck2_name,
            "player1_model": game.player1_model,
            "player2_model": game.player2_model,
            "outcome": game.outcome,
            "winner_deck": game.winner_deck,
            "turn_count": game.turn_count,
            "duration_ms": game.duration_ms,
            "cc_tracking": game.cc_tracking,
            "action_log": game.action_log,
            "error_message": game.error_message,
            "created_at": game.created_at.isoformat() if game.created_at else None,
        }
    
    def list_runs(self, limit: int = 20) -> list[dict]:
        """
        List recent simulation runs.
        
        Args:
            limit: Maximum number of runs to return
            
        Returns:
            List of run summaries
        """
        db = self._get_db()
        
        runs = db.query(SimulationRunModel).order_by(
            SimulationRunModel.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "run_id": run.id,
                "status": run.status,
                "total_games": run.total_games,
                "completed_games": run.completed_games,
                "config": run.config,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            }
            for run in runs
        ]
    
    def cancel_simulation(self, run_id: int) -> bool:
        """
        Cancel a running simulation.
        
        Note: This only marks the simulation as cancelled. The current game
        will complete before the cancellation takes effect.
        
        Args:
            run_id: ID of the simulation run to cancel
            
        Returns:
            True if cancelled, False if not found or not running
        """
        db = self._get_db()
        
        run = db.query(SimulationRunModel).filter(
            SimulationRunModel.id == run_id
        ).first()
        
        if run is None:
            return False
        
        if run.status not in ("pending", "running"):
            return False
        
        run.status = "cancelled"
        run.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Simulation {run_id} cancelled")
        return True
