"""
Simulation orchestrator for managing batch AI vs AI simulations.

This module coordinates running multiple games across deck matchups,
tracks progress, persists results to database, and aggregates statistics.

Supports parallel game execution to speed up simulations.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import threading
from typing import Optional

from sqlalchemy.orm import Session

from api.db_models import SimulationRunModel, SimulationGameModel
from api.database import get_db, SessionLocal

from .config import (
    SimulationConfig,
    SimulationResult,
    SimulationStatus,
)
from .deck_loader import load_simulation_decks_dict, validate_deck_names, validate_deck
from .runner import SimulationRunner

logger = logging.getLogger(__name__)

# Default number of parallel games
# Note: gemini-2.5-flash-lite has 4K RPM limit - can safely run 10+ parallel
DEFAULT_PARALLEL_GAMES = 10


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
            
        Raises:
            ValueError: If deck validation fails
        """
        db = self._get_db()
        
        # Load deck configs
        deck_dict = load_simulation_decks_dict()
        
        # Validate deck names first (fail fast)
        deck_name_errors = validate_deck_names(config.deck_names, deck_dict)
        if deck_name_errors:
            error_msg = "Deck validation failed:\n" + "\n".join(deck_name_errors)
            raise ValueError(error_msg)
        
        # Validate each deck's card composition
        for deck_name in config.deck_names:
            deck = deck_dict[deck_name]
            deck_errors = validate_deck(deck)
            if deck_errors:
                error_msg = f"Invalid deck '{deck_name}':\n" + "\n".join(deck_errors)
                raise ValueError(error_msg)
        
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
    
    def run_simulation(self, run_id: int, parallel_games: int = DEFAULT_PARALLEL_GAMES) -> SimulationResult:
        """
        Execute a simulation run with parallel game execution.
        
        This runs synchronously (blocking) until all games complete,
        but executes multiple games in parallel for speed.
        
        Args:
            run_id: ID of the simulation run to execute
            parallel_games: Number of games to run in parallel (default: 5)
            
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
        
        # Lock for thread-safe progress updates
        progress_lock = threading.Lock()
        completed_count = run.completed_games
        
        try:
            # Load decks
            deck_dict = load_simulation_decks_dict()
            
            # Build list of all games to run
            games_to_run = []
            matchups = config.get_matchups()
            game_number = 1
            
            for deck1_name, deck2_name in matchups:
                for iteration in range(config.iterations_per_matchup):
                    if game_number > run.completed_games:  # Skip already completed
                        games_to_run.append({
                            "game_number": game_number,
                            "deck1_name": deck1_name,
                            "deck2_name": deck2_name,
                            "deck1": deck_dict[deck1_name],
                            "deck2": deck_dict[deck2_name],
                        })
                    game_number += 1
            
            logger.info(
                f"Running {len(games_to_run)} games with {parallel_games} parallel workers"
            )
            
            def run_single_game(game_info: dict) -> tuple:
                """Run a single game in a worker thread."""
                # Each thread needs its own runner (has its own AI players)
                runner = SimulationRunner(
                    player1_model=config.player1_model,
                    player2_model=config.player2_model,
                    player1_ai_version=config.player1_ai_version,
                    player2_ai_version=config.player2_ai_version,
                    max_turns=config.max_turns,
                )
                result = runner.run_game(
                    game_info["deck1"],
                    game_info["deck2"],
                    game_info["game_number"],
                )
                return (game_info, result)
            
            def persist_result(game_info: dict, result, db_session: Session):
                """Persist a game result to the database."""
                nonlocal completed_count
                
                game_record = SimulationGameModel(
                    run_id=run_id,
                    game_number=game_info["game_number"],
                    deck1_name=game_info["deck1_name"],
                    deck2_name=game_info["deck2_name"],
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
                db_session.add(game_record)
                
                with progress_lock:
                    completed_count += 1
                    # Update run progress
                    run_record = db_session.query(SimulationRunModel).filter(
                        SimulationRunModel.id == run_id
                    ).first()
                    if run_record:
                        run_record.completed_games = completed_count
                    db_session.commit()
                
                # Update in-memory result (thread-safe via lock)
                with progress_lock:
                    self._result.add_game_result(result)
            
            # Run games in parallel
            with ThreadPoolExecutor(max_workers=parallel_games) as executor:
                # Submit all games
                futures = {
                    executor.submit(run_single_game, game_info): game_info
                    for game_info in games_to_run
                }
                
                # Process results as they complete
                for future in as_completed(futures):
                    game_info = futures[future]
                    try:
                        _, result = future.result()
                        # Use a fresh DB session for each persist (thread safety)
                        if SessionLocal is not None:
                            thread_db = SessionLocal()
                            try:
                                persist_result(game_info, result, thread_db)
                            finally:
                                thread_db.close()
                        else:
                            persist_result(game_info, result, db)
                        
                        logger.debug(
                            f"Game {game_info['game_number']} completed: "
                            f"{game_info['deck1_name']} vs {game_info['deck2_name']} "
                            f"-> {result.outcome.value}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Game {game_info['game_number']} failed: {e}"
                        )
                        # Still count it as completed (with error)
                        with progress_lock:
                            completed_count += 1
            
            # Mark as completed
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.completed_games = completed_count
            run.results = {
                "matchup_stats": {
                    k: v.to_dict() 
                    for k, v in self._result.matchup_stats.items()
                }
            }
            db.commit()
            
            self._result.status = SimulationStatus.COMPLETED
            
            logger.info(
                f"Simulation {run_id} completed: {completed_count} games"
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
            # Calculate CC statistics per player from cc_tracking
            p1_cc_spent = 0
            p2_cc_spent = 0
            p1_cc_gained = 0
            p2_cc_gained = 0
            if game.cc_tracking:
                for entry in game.cc_tracking:
                    if entry.get('player_id') == 'player1':
                        p1_cc_spent += entry.get('cc_spent', 0)
                        p1_cc_gained += entry.get('cc_gained', 0)
                    elif entry.get('player_id') == 'player2':
                        p2_cc_spent += entry.get('cc_spent', 0)
                        p2_cc_gained += entry.get('cc_gained', 0)
            
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
                "p1_cc_gained": p1_cc_gained,
                "p2_cc_gained": p2_cc_gained,
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
