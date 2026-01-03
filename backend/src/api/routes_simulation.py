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
from simulation.config import SimulationConfig, SUPPORTED_MODELS
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
        default="gemini-2.5-flash-lite",
        description="Gemini model for player 1"
    )
    player2_model: str = Field(
        default="gemini-2.5-flash-lite",
        description="Gemini model for player 2"
    )
    player1_ai_version: int = Field(
        default=4,
        ge=2,
        le=4,
        description="AI planning version for player 1 (2=per-action, 3=turn-planning, 4=dual-request)"
    )
    player2_ai_version: int = Field(
        default=4,
        ge=2,
        le=4,
        description="AI planning version for player 2 (2=per-action, 3=turn-planning, 4=dual-request)"
    )
    iterations_per_matchup: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of games per deck matchup"
    )
    max_turns: int = Field(
        default=40,
        ge=10,
        le=100,
        description="Maximum turns before declaring draw"
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
    Get list of supported Gemini models for simulations.
    
    Returns:
        List of model identifiers (e.g., ["gemini-2.0-flash", ...])
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
    
    Args:
        request: Simulation configuration
        db: Database session
        
    Returns:
        run_id and initial status (status will be "pending" or "running")
    """
    # Validate model names
    if request.player1_model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid player1_model '{request.player1_model}'. Supported: {SUPPORTED_MODELS}"
        )
    if request.player2_model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid player2_model '{request.player2_model}'. Supported: {SUPPORTED_MODELS}"
        )
    
    # Create config
    config = SimulationConfig(
        deck_names=request.deck_names,
        player1_model=request.player1_model,
        player2_model=request.player2_model,
        player1_ai_version=request.player1_ai_version,
        player2_ai_version=request.player2_ai_version,
        iterations_per_matchup=request.iterations_per_matchup,
        max_turns=request.max_turns,
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
    
    Includes CC tracking per turn and full action log.
    
    Args:
        run_id: Simulation run ID
        game_number: Game number within the run
        db: Database session
        
    Returns:
        Detailed game data including CC tracking and action log
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
    - CC efficiency analysis
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
