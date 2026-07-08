"""
Simulation orchestrator for managing batch AI vs AI simulations.

This module coordinates running multiple games across deck matchups,
tracks progress, persists results to database, and aggregates statistics.

Supports parallel game execution to speed up simulations.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
import threading
from typing import Optional

from sqlalchemy.orm import Session

from api.db_models import SimulationRunModel, SimulationGameModel
from api.database import get_db, SessionLocal

from .config import (
    GameOutcome,
    GameResult,
    SimulationConfig,
    SimulationResult,
    SimulationStatus,
    TurnCharge,
)
from .deck_loader import load_simulation_decks_dict, validate_deck_names, validate_deck
from .runner import SimulationRunner
from game_engine.ai.rate_limiter import (
    BudgetExhaustedError,
    NoopLimiter,
    RateBudgetLimiter,
)

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
    
    def __init__(self, db: Optional[Session] = None, rate_limiter_session_factory=None):
        """
        Initialize the orchestrator.

        Args:
            db: SQLAlchemy session for persistence. If None, will create per-operation.
            rate_limiter_session_factory: Optional SQLAlchemy sessionmaker forwarded to
                the RateBudgetLimiter this orchestrator builds. Defaults to the app's
                SessionLocal. Tests should inject an in-memory-SQLite-backed factory.
        """
        self._db = db
        self._current_run: Optional[SimulationRunModel] = None
        self._result: Optional[SimulationResult] = None
        self._rate_limiter_session_factory = rate_limiter_session_factory
        self._limiter: Optional[object] = None
        self._stop_event: Optional[threading.Event] = None
    
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
    
    def _rehydrate_result_from_db(
        self, run_id: int, config: SimulationConfig, status: SimulationStatus
    ) -> SimulationResult:
        """
        Rebuild a SimulationResult (including matchup_stats aggregation) from
        persisted SimulationGameModel rows.

        This is needed so that resuming a paused/budget-exhausted run in a
        fresh process (or a fresh SimulationOrchestrator instance) produces
        the exact same aggregates as if all games had run in one session --
        the in-memory SimulationResult otherwise only reflects games
        completed by the current process.
        """
        db = self._get_db()
        run = db.query(SimulationRunModel).filter(
            SimulationRunModel.id == run_id
        ).first()
        if run is None:
            raise ValueError(f"Simulation run {run_id} not found")

        games = db.query(SimulationGameModel).filter(
            SimulationGameModel.run_id == run_id
        ).order_by(SimulationGameModel.game_number).all()

        result = SimulationResult(
            run_id=run_id,
            config=config,
            status=status,
            total_games=run.total_games,
            completed_games=0,
        )

        for game in games:
            game_result = GameResult(
                game_number=game.game_number,
                deck1_name=game.deck1_name,
                deck2_name=game.deck2_name,
                player1_model=game.player1_model,
                player2_model=game.player2_model,
                outcome=GameOutcome(game.outcome),
                winner_deck=game.winner_deck,
                turn_count=game.turn_count,
                duration_ms=game.duration_ms,
                charge_tracking=[
                    TurnCharge(**charge) for charge in (game.charge_tracking or [])
                ],
                action_log=game.action_log or [],
                error_message=game.error_message,
            )
            result.add_game_result(game_result)

        return result

    def _build_rate_limiter(self, config: SimulationConfig):
        """Build a RateBudgetLimiter from config, or a NoopLimiter if unconfigured."""
        if config.rpm is None and config.daily_request_budget is None:
            return NoopLimiter()

        kwargs = {}
        if self._rate_limiter_session_factory is not None:
            kwargs["session_factory"] = self._rate_limiter_session_factory
        return RateBudgetLimiter(
            rpm=config.rpm,
            daily_budget=config.daily_request_budget,
            **kwargs,
        )

    def run_simulation(
        self, run_id: int, parallel_games: Optional[int] = None
    ) -> SimulationResult:
        """
        Execute a simulation run with parallel game execution.

        This runs synchronously (blocking) until all games complete, all
        already-persisted games are skipped, or the AI rate limiter's daily
        request budget is exhausted (in which case the run pauses cleanly --
        waiting for the budget to reset and calling resume_simulation() is
        the caller's responsibility, not the orchestrator's).

        Args:
            run_id: ID of the simulation run to execute
            parallel_games: Number of games to run in parallel. Defaults to
                config.parallel_games, falling back to DEFAULT_PARALLEL_GAMES.

        Returns:
            SimulationResult with all game outcomes so far
        """
        db = self._get_db()

        # ALWAYS load the run through this call's session. _get_db() returns a
        # fresh session when no session was injected (the CLI path), so a run
        # object cached by start_simulation() belongs to a different session --
        # mutating it and committing `db` silently persists nothing (status
        # stuck at "pending" while per-game threads, which use their own
        # sessions, persisted fine).
        run = db.query(SimulationRunModel).filter(
            SimulationRunModel.id == run_id
        ).first()
        if run is None:
            raise ValueError(f"Simulation run {run_id} not found")

        # Rebuild the in-memory result only when this orchestrator has no
        # context for the run (resume in a new process); a same-process
        # start->run flow keeps the tracker created by start_simulation().
        if self._current_run is None or self._current_run.id != run_id or self._result is None:
            # Reconstruct config (old rows without new keys keep working since
            # every new SimulationConfig field has a default).
            config = SimulationConfig(**run.config)
            self._result = self._rehydrate_result_from_db(
                run_id, config, SimulationStatus.RUNNING
            )
        self._current_run = run

        config = self._result.config

        if parallel_games is None:
            parallel_games = config.parallel_games or DEFAULT_PARALLEL_GAMES

        # Update status to running
        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()
        self._result.status = SimulationStatus.RUNNING

        # Games already persisted for this run (regardless of completion order)
        # must be skipped -- game_number > completed_games breaks with
        # out-of-order parallel completion.
        persisted_game_numbers = {
            row[0] for row in db.query(SimulationGameModel.game_number)
            .filter(SimulationGameModel.run_id == run_id)
            .all()
        }

        # Lock for thread-safe progress updates
        progress_lock = threading.Lock()
        completed_count = len(persisted_game_numbers)

        stop_event = threading.Event()
        self._stop_event = stop_event
        limiter = self._build_rate_limiter(config)
        self._limiter = limiter

        budget_exhausted = False
        resets_at = None
        paused_by_request = False

        try:
            # Load decks
            deck_dict = load_simulation_decks_dict()

            # Build list of all games to run
            games_to_run = []
            matchups = config.get_matchups()
            game_number = 1

            for deck1_name, deck2_name in matchups:
                for iteration in range(config.iterations_per_matchup):
                    if game_number not in persisted_game_numbers:  # Skip already completed
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

            def run_single_game(game_info: dict) -> Optional[tuple]:
                """Run a single game in a worker thread.

                Returns None (a "skip, don't persist" sentinel) if a pause
                was requested before this game started.
                """
                if stop_event.is_set():
                    return None
                # Each thread needs its own runner (has its own AI players)
                runner = SimulationRunner(
                    player1_model=config.player1_model,
                    player2_model=config.player2_model,
                    max_turns=config.max_turns,
                    rate_limiter=limiter,
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
                    charge_tracking=[charge.to_dict() for charge in result.charge_tracking],
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
                        outcome = future.result()
                    except BudgetExhaustedError as e:
                        budget_exhausted = True
                        resets_at = e.resets_at
                        stop_event.set()
                        # Best-effort cancel of not-yet-started futures.
                        for other_future in futures:
                            other_future.cancel()
                        continue
                    except Exception as e:
                        if stop_event.is_set():
                            # Cancelled/aborted because of a pause or budget
                            # exhaustion -- don't count or persist it.
                            continue
                        logger.error(
                            f"Game {game_info['game_number']} failed: {e}"
                        )
                        # Still count it as completed (with error)
                        with progress_lock:
                            completed_count += 1
                        continue

                    if outcome is None:
                        # Skipped due to a pause request before it started.
                        continue

                    _, result = outcome
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

            limiter.flush()

            if not budget_exhausted and stop_event.is_set():
                paused_by_request = True

            if budget_exhausted:
                run.status = "budget_exhausted"
                run.completed_games = completed_count
                run.results = {
                    **(run.results or {}),
                    "matchup_stats": {
                        k: v.to_dict()
                        for k, v in self._result.matchup_stats.items()
                    },
                    "resets_at": resets_at.isoformat() if resets_at else None,
                }
                db.commit()

                self._result.status = SimulationStatus.BUDGET_EXHAUSTED
                self._result.resets_at = resets_at

                logger.warning(
                    f"Simulation {run_id} paused: budget exhausted, resets at {resets_at}"
                )
            elif paused_by_request:
                run.status = "paused"
                run.completed_games = completed_count
                run.results = {
                    **(run.results or {}),
                    "matchup_stats": {
                        k: v.to_dict()
                        for k, v in self._result.matchup_stats.items()
                    },
                }
                db.commit()

                self._result.status = SimulationStatus.PAUSED

                logger.info(f"Simulation {run_id} paused: {completed_count} games done")
            else:
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
        finally:
            self._stop_event = None

        return self._result

    def resume_simulation(
        self, run_id: int, parallel_games: Optional[int] = None
    ) -> SimulationResult:
        """
        Resume a paused, budget-exhausted, failed, or stale-running run.

        Reconstructs config from the persisted run, rehydrates the in-memory
        SimulationResult (matchup stats etc.) from persisted game rows so
        pre-pause games are included in the final aggregates, then delegates
        to run_simulation() -- which skips any already-persisted games.

        Args:
            run_id: ID of the simulation run to resume
            parallel_games: Optional override for parallel worker count

        Returns:
            SimulationResult with all game outcomes (pre-pause and new)
        """
        db = self._get_db()
        run = db.query(SimulationRunModel).filter(
            SimulationRunModel.id == run_id
        ).first()
        if run is None:
            raise ValueError(f"Simulation run {run_id} not found")

        resumable_statuses = {"budget_exhausted", "paused", "failed", "running"}
        if run.status not in resumable_statuses:
            raise ValueError(
                f"Cannot resume simulation run {run_id} with status '{run.status}'; "
                f"must be one of {sorted(resumable_statuses)}"
            )

        config = SimulationConfig(**run.config)
        self._current_run = run
        self._result = self._rehydrate_result_from_db(
            run_id, config, SimulationStatus.RUNNING
        )

        return self.run_simulation(run_id, parallel_games=parallel_games)

    def pause_simulation(self, run_id: int) -> bool:
        """
        Best-effort pause of a running simulation.

        If this orchestrator instance is currently executing the given run,
        signals its stop event so queued (not-yet-started) games are skipped
        and in-flight games are allowed to finish; run_simulation() will set
        the run's status to "paused" once the executor drains. If no matching
        in-process run is found, marks the run "paused" directly (e.g. it was
        left "running" by a crashed process).

        Args:
            run_id: ID of the simulation run to pause

        Returns:
            True if a pause was requested/applied, False if not found or not
            in a pausable state.
        """
        db = self._get_db()

        run = db.query(SimulationRunModel).filter(
            SimulationRunModel.id == run_id
        ).first()
        if run is None:
            return False

        if run.status not in ("pending", "running"):
            return False

        if (
            self._current_run is not None
            and self._current_run.id == run_id
            and self._stop_event is not None
        ):
            self._stop_event.set()
            logger.info(f"Simulation {run_id} pause requested (in-process)")
            return True

        # No matching in-process run executing -- mark paused directly.
        run.status = "paused"
        db.commit()
        logger.info(f"Simulation {run_id} marked paused (no active in-process run)")
        return True
    
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
            "budget": self._get_budget_status(run, db),
        }

    def _get_budget_status(self, run: SimulationRunModel, db: Session) -> dict:
        """
        Return rate-limiter budget info for a run.

        Uses the live limiter's remaining() if this orchestrator instance is
        currently executing the run; otherwise falls back to reading the
        persisted ApiUsageModel row plus the run's own config.
        """
        if (
            self._current_run is not None
            and self._current_run.id == run.id
            and self._limiter is not None
        ):
            remaining = self._limiter.remaining()
            resets_at = remaining.get("resets_at")
            return {
                "used_today": remaining.get("used_today"),
                "daily_budget": remaining.get("daily_budget"),
                "rpm": remaining.get("rpm"),
                "resets_at": resets_at.isoformat() if resets_at else None,
            }

        cfg = run.config or {}
        rpm = cfg.get("rpm")
        daily_budget = cfg.get("daily_request_budget")
        used_today = None
        if daily_budget is not None:
            from api.db_models import ApiUsageModel

            usage_row = db.query(ApiUsageModel).filter(
                ApiUsageModel.provider == "gemini",
                ApiUsageModel.day == date.today(),
            ).first()
            used_today = usage_row.request_count if usage_row else 0

        return {
            "used_today": used_today,
            "daily_budget": daily_budget,
            "rpm": rpm,
            "resets_at": None,
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
        
        def avg(values: list[float]) -> float | None:
            return (sum(values) / len(values)) if values else None

        def compute_active_turn_charge_end_avgs(charge_tracking: list[dict]) -> tuple[float | None, float | None]:
            if not charge_tracking:
                return None, None
            p1_vals: list[float] = []
            p2_vals: list[float] = []
            for entry in charge_tracking:
                turn = entry.get("turn")
                pid = entry.get("player_id")
                if not isinstance(turn, int) or pid not in ("player1", "player2"):
                    continue
                is_active = (turn % 2 == 1 and pid == "player1") or (turn % 2 == 0 and pid == "player2")
                if not is_active:
                    continue
                charge_end = entry.get("charge_end")
                if isinstance(charge_end, (int, float)):
                    if pid == "player1":
                        p1_vals.append(float(charge_end))
                    else:
                        p2_vals.append(float(charge_end))
            return avg(p1_vals), avg(p2_vals)

        max_turns = 20
        if run.config and isinstance(run.config, dict):
            max_turns = int(run.config.get("max_turns", 20) or 20)

        game_results = []
        p1_game_avgs: list[float] = []
        p2_game_avgs: list[float] = []
        turn_counts: list[int] = []
        turn_limit_hits = 0
        for game in games:
            # Calculate Charge statistics per player from charge_tracking
            p1_charge_spent = 0
            p2_charge_spent = 0
            p1_charge_gained = 0
            p2_charge_gained = 0
            if game.charge_tracking:
                for entry in game.charge_tracking:
                    if entry.get('player_id') == 'player1':
                        p1_charge_spent += entry.get('charge_spent', 0)
                        p1_charge_gained += entry.get('charge_gained', 0)
                    elif entry.get('player_id') == 'player2':
                        p2_charge_spent += entry.get('charge_spent', 0)
                        p2_charge_gained += entry.get('charge_gained', 0)

            p1_avg_charge_end_active, p2_avg_charge_end_active = compute_active_turn_charge_end_avgs(game.charge_tracking or [])

            # Track aggregates for the run
            if isinstance(game.turn_count, int):
                turn_counts.append(game.turn_count)
            if p1_avg_charge_end_active is not None:
                p1_game_avgs.append(p1_avg_charge_end_active)
            if p2_avg_charge_end_active is not None:
                p2_game_avgs.append(p2_avg_charge_end_active)

            hit_turn_limit = bool(game.outcome == 'draw' and isinstance(game.turn_count, int) and game.turn_count == max_turns)
            if hit_turn_limit:
                turn_limit_hits += 1
            
            game_results.append({
                "game_number": game.game_number,
                "deck1_name": game.deck1_name,
                "deck2_name": game.deck2_name,
                "outcome": game.outcome,
                "winner_deck": game.winner_deck,
                "turn_count": game.turn_count,
                "duration_ms": game.duration_ms,
                "p1_charge_spent": p1_charge_spent,
                "p2_charge_spent": p2_charge_spent,
                "p1_charge_gained": p1_charge_gained,
                "p2_charge_gained": p2_charge_gained,
                "p1_avg_charge_end_active": p1_avg_charge_end_active,
                "p2_avg_charge_end_active": p2_avg_charge_end_active,
                "hit_turn_limit": hit_turn_limit,
                "error_message": game.error_message,
            })

        avg_turns = avg([float(t) for t in turn_counts])
        turn_limit_hit_pct = (turn_limit_hits / len(games) * 100.0) if games else 0.0
        
        return {
            "run_id": run.id,
            "status": run.status,
            "config": run.config,
            "total_games": run.total_games,
            "completed_games": run.completed_games,
            "matchup_stats": run.results.get("matchup_stats", {}) if run.results else {},
            "aggregate": {
                "max_turns": max_turns,
                "avg_turns": avg_turns,
                "turn_limit_hits": turn_limit_hits,
                "turn_limit_hit_pct": round(turn_limit_hit_pct, 1),
                "avg_p1_charge_end_active": avg(p1_game_avgs),
                "avg_p2_charge_end_active": avg(p2_game_avgs),
            },
            "games": game_results,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
    
    def get_game_details(self, run_id: int, game_number: int) -> dict:
        """
        Get detailed results for a specific game including Charge tracking.
        
        Args:
            run_id: ID of the simulation run
            game_number: Game number within the run
            
        Returns:
            Detailed game data including Charge tracking and action log
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
            "charge_tracking": game.charge_tracking,
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
