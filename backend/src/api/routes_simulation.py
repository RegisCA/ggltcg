"""
Simulation API routes.

Endpoints for configuring, running, and viewing AI vs AI simulations.

Architecture:
- POST /start creates a DB record and spawns a background thread
- Background thread runs games and updates DB after each game
- GET /runs/{id} returns current progress from DB
- Frontend polls /runs/{id} every 5 seconds for live updates
"""

import logging
import threading
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import SessionLocal
from simulation.config import SimulationConfig, SUPPORTED_MODELS, is_valid_model_name
from simulation.orchestrator import SimulationOrchestrator
from simulation.deck_loader import load_simulation_decks
from simulation.reporter import SimulationReporter

logger = logging.getLogger(__name__)

# Track active simulation threads (run_id -> thread)
_active_simulations: dict[int, threading.Thread] = {}
_simulations_lock = threading.Lock()  # Protect concurrent access to _active_simulations

router = APIRouter(prefix="/admin/simulation", tags=["simulation"])


def get_db():
    """Database session dependency."""
    if SessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail="Database not configured"
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _run_simulation_background(run_id: int):
    """
    Background worker to execute simulation.

    Creates its own DB session and runs games, updating DB after each game.
    This runs in a separate thread to not block the HTTP response.
    """
    logger.info(f"[Background] Starting simulation run {run_id}")

    if SessionLocal is None:
        logger.error(f"[Background] Database not configured for run {run_id}")
        return

    # Create new session for this thread
    db = SessionLocal()
    try:
        orchestrator = SimulationOrchestrator(db)
        orchestrator.run_simulation(run_id)
        logger.info(f"[Background] Simulation run {run_id} completed")
    except Exception as e:
        logger.exception(f"[Background] Simulation run {run_id} failed: {e}")
    finally:
        db.close()
        # Clean up thread tracking
        with _simulations_lock:
            _active_simulations.pop(run_id, None)


def _resume_simulation_background(run_id: int):
    """
    Background worker to resume a paused/budget_exhausted/failed simulation.

    Mirrors _run_simulation_background but calls resume_simulation(), which
    reconstructs config + in-memory aggregates from persisted rows before
    delegating to run_simulation() (which skips already-persisted games).
    """
    logger.info(f"[Background] Resuming simulation run {run_id}")

    if SessionLocal is None:
        logger.error(f"[Background] Database not configured for run {run_id}")
        return

    db = SessionLocal()
    try:
        orchestrator = SimulationOrchestrator(db)
        orchestrator.resume_simulation(run_id)
        logger.info(f"[Background] Simulation run {run_id} resume completed")
    except Exception as e:
        logger.exception(f"[Background] Simulation run {run_id} resume failed: {e}")
    finally:
        db.close()
        with _simulations_lock:
            _active_simulations.pop(run_id, None)


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class StartSimulationRequest(BaseModel):
    """Request to start a new simulation."""
    deck_names: List[str] = Field(
        ...,
        description="List of deck names to use (will run all combinations including mirrors). Use 1 deck for mirror-only test.",
        min_length=1
    )
    player1_model: str = Field(
        default="gemini-flash-lite-latest",
        description="Model identifier for player 1"
    )
    player2_model: str = Field(
        default="gemini-flash-lite-latest",
        description="Model identifier for player 2"
    )
    iterations_per_matchup: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of games per deck matchup"
    )
    max_turns: int = Field(
        default=20,
        ge=10,
        le=100,
        description="Maximum turns before declaring draw"
    )
    rpm: int | None = Field(
        default=None,
        ge=1,
        description="Optional AI request-per-minute cap for this run's rate limiter"
    )
    daily_request_budget: int | None = Field(
        default=None,
        ge=1,
        description="Optional daily AI request budget; the run pauses (budget_exhausted) when exceeded"
    )
    parallel_games: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Number of games to run concurrently"
    )


class DeckInfo(BaseModel):
    """Information about an available simulation deck."""
    name: str
    description: str
    cards: List[str]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/decks")
async def list_available_decks() -> List[DeckInfo]:
    """
    Get list of available simulation decks.
    
    Returns:
        List of deck configurations from simulation_decks.csv
    """
    try:
        decks = load_simulation_decks()
        return [
            DeckInfo(
                name=deck.name,
                description=deck.description,
                cards=deck.cards,
            )
            for deck in decks
        ]
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Simulation decks file not found: {e}"
        )


@router.get("/models")
async def list_supported_models() -> List[str]:
    """
    Get a list of suggested models for simulations.
    
    Returns:
        List of model identifiers
    """
    return SUPPORTED_MODELS


@router.post("/start")
async def start_simulation(
    request: StartSimulationRequest,
    db: Session = Depends(get_db)
):
    """
    Start a new simulation run.
    
    Creates a simulation run record in the database and spawns a background
    thread to execute the games. Returns immediately with the run_id.
    
    Use GET /runs/{run_id} to poll for progress.

    Note: this is a server-hosted run. If a daily request budget is
    configured (via `daily_request_budget`) and gets exhausted, the run
    parks in "budget_exhausted" status until POST /runs/{run_id}/resume
    is called (or the CLI resumes it) -- the route layer never sleeps
    across budget windows waiting for a reset. Multi-day sleep-wait mode
    is a CLI-only feature.

    Args:
        request: Simulation configuration
        db: Database session

    Returns:
        run_id and initial status (status will be "pending" or "running")
    """
    # Validate model names
    if not is_valid_model_name(request.player1_model):
        raise HTTPException(
            status_code=400,
            detail="player1_model must be a non-empty string"
        )
    if not is_valid_model_name(request.player2_model):
        raise HTTPException(
            status_code=400,
            detail="player2_model must be a non-empty string"
        )
    
    # Create config
    # Safety cap: simulations should not run beyond 20 turns.
    # This protects against older clients (e.g., admin UI) sending 40.
    max_turns = min(request.max_turns, 20)
    config = SimulationConfig(
        deck_names=request.deck_names,
        player1_model=request.player1_model,
        player2_model=request.player2_model,
        iterations_per_matchup=request.iterations_per_matchup,
        max_turns=max_turns,
        rpm=request.rpm,
        daily_request_budget=request.daily_request_budget,
        parallel_games=request.parallel_games,
    )
    
    total_games = config.total_games()
    if total_games == 0:
        raise HTTPException(
            status_code=400,
            detail="Configuration results in 0 games. Check deck selection."
        )
    
    # Enforce maximum game limit to prevent resource exhaustion
    MAX_TOTAL_GAMES = 500
    if total_games > MAX_TOTAL_GAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Total games ({total_games}) exceeds maximum ({MAX_TOTAL_GAMES}). Reduce iterations or deck count."
        )
    
    logger.info(
        f"Starting simulation: {config.deck_names} with {total_games} games"
    )
    
    try:
        # Create DB record (this is fast)
        orchestrator = SimulationOrchestrator(db)
        run_id = orchestrator.start_simulation(config)
        
        # Spawn background thread to run simulation
        thread = threading.Thread(
            target=_run_simulation_background,
            args=(run_id,),
            name=f"simulation-{run_id}",
            daemon=False,  # Allow in-progress simulations to finish cleanly on shutdown
        )
        with _simulations_lock:
            _active_simulations[run_id] = thread
        thread.start()
        
        logger.info(f"Spawned background thread for simulation {run_id}")
        
        # Return immediately with run_id
        return {
            "run_id": run_id,
            "status": "pending",
            "total_games": total_games,
            "completed_games": 0,
            "message": f"Simulation started. Poll GET /admin/simulation/runs/{run_id} for progress.",
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to start simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs")
async def list_simulation_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List recent simulation runs.
    
    Args:
        limit: Maximum number of runs to return
        db: Database session
        
    Returns:
        List of simulation run summaries
    """
    orchestrator = SimulationOrchestrator(db)
    return orchestrator.list_runs(limit=limit)


@router.get("/runs/{run_id}")
async def get_simulation_status(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Get status of a simulation run.
    
    Args:
        run_id: Simulation run ID
        db: Database session
        
    Returns:
        Status information including progress
    """
    try:
        orchestrator = SimulationOrchestrator(db)
        return orchestrator.get_status(run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/results")
async def get_simulation_results(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Get complete results for a simulation run.
    
    Includes matchup statistics and individual game summaries.
    
    Args:
        run_id: Simulation run ID
        db: Database session
        
    Returns:
        Complete results with matchup stats and game list
    """
    try:
        orchestrator = SimulationOrchestrator(db)
        return orchestrator.get_results(run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/games/{game_number}")
async def get_game_details(
    run_id: int,
    game_number: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed results for a specific game.
    
    Includes Charge tracking per turn and full action log.
    
    Args:
        run_id: Simulation run ID
        game_number: Game number within the run
        db: Database session
        
    Returns:
        Detailed game data including Charge tracking and action log
    """
    try:
        orchestrator = SimulationOrchestrator(db)
        return orchestrator.get_game_details(run_id, game_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/runs/{run_id}/cancel")
async def cancel_simulation(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Cancel a running simulation.
    
    The current game will complete before the cancellation takes effect.
    
    Args:
        run_id: Simulation run ID to cancel
        db: Database session
        
    Returns:
        Success status
    """
    orchestrator = SimulationOrchestrator(db)
    cancelled = orchestrator.cancel_simulation(run_id)
    
    if not cancelled:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel: run not found or not in running state"
        )
    
    return {"status": "cancelled", "run_id": run_id}


@router.post("/runs/{run_id}/resume")
async def resume_simulation(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Resume a paused, budget-exhausted, or failed simulation run.

    Spawns a background thread that reconstructs the run's config and
    in-memory aggregates from persisted game rows, then continues
    executing the remaining games (already-persisted games are skipped).

    Note: this is a server-hosted resume. If the run hits its daily
    request budget again, it parks back in "budget_exhausted" until this
    endpoint is called again -- the route never sleeps waiting for a
    budget reset. Multi-day sleep-wait mode is CLI-only.

    Args:
        run_id: Simulation run ID to resume
        db: Database session

    Returns:
        run_id and status confirming the resume was spawned
    """
    orchestrator = SimulationOrchestrator(db)

    try:
        status = orchestrator.get_status(run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    resumable_statuses = {"paused", "budget_exhausted", "failed"}
    if status["status"] not in resumable_statuses:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot resume simulation run {run_id} with status "
                f"'{status['status']}'; must be one of {sorted(resumable_statuses)}"
            ),
        )

    with _simulations_lock:
        if run_id in _active_simulations:
            raise HTTPException(
                status_code=409,
                detail=f"Simulation run {run_id} is already active",
            )

        thread = threading.Thread(
            target=_resume_simulation_background,
            args=(run_id,),
            name=f"simulation-resume-{run_id}",
            daemon=False,
        )
        _active_simulations[run_id] = thread
        thread.start()

    logger.info(f"Spawned background resume thread for simulation {run_id}")

    return {
        "run_id": run_id,
        "status": "running",
        "message": f"Simulation resume started. Poll GET /admin/simulation/runs/{run_id} for progress.",
    }


@router.post("/runs/{run_id}/pause")
async def pause_simulation(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Best-effort pause of a running simulation.

    Args:
        run_id: Simulation run ID to pause
        db: Database session

    Returns:
        Success status
    """
    orchestrator = SimulationOrchestrator(db)

    try:
        status = orchestrator.get_status(run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if status["status"] not in ("pending", "running"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot pause: run {run_id} is not running (status '{status['status']}')",
        )

    paused = orchestrator.pause_simulation(run_id)
    if not paused:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot pause: run {run_id} not found or not in a pausable state",
        )

    return {"status": "pause_requested", "run_id": run_id}


@router.get("/runs/{run_id}/report", response_class=PlainTextResponse)
async def get_simulation_report(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate and download a markdown report for a simulation run.
    
    Returns a formatted markdown report with:
    - Overall statistics
    - Matchup matrix
    - Charge efficiency analysis
    - First-player advantage
    - Notable games
    
    Args:
        run_id: Simulation run ID
        db: Database session
        
    Returns:
        Markdown formatted report as plain text
    """
    try:
        orchestrator = SimulationOrchestrator(db)
        results = orchestrator.get_results(run_id)
        
        reporter = SimulationReporter(results)
        report = reporter.generate_markdown_report()
        
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error generating report for run {run_id}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
