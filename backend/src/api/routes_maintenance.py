"""
Maintenance routes for database cleanup tasks.

These endpoints are called by GitHub Actions on a schedule to:
1. Mark abandoned games (active > 24 hours)
2. Delete old AI decision logs (> 6 hours)
3. Delete old game playback data (> 24 hours)
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import text

from .database import SessionLocal
from .db_models import GameModel, AIDecisionLogModel, GamePlaybackModel, SimulationRunModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


# Simple API key auth for maintenance endpoints
# Set MAINTENANCE_API_KEY env var in production
MAINTENANCE_API_KEY = os.getenv("MAINTENANCE_API_KEY", "dev-maintenance-key")


class CleanupResult(BaseModel):
    """Result of a cleanup operation."""
    games_abandoned: int
    ai_logs_deleted: int
    playback_deleted: int
    simulations_deleted: int = 0
    execution_time_ms: int


class CleanupStats(BaseModel):
    """Current stats before cleanup."""
    active_games_total: int
    active_games_stale: int  # Active but not updated in 24h
    ai_logs_total: int
    ai_logs_stale: int  # Older than 6 hours
    playback_total: int
    playback_stale: int  # Older than 24 hours
    simulations_total: int = 0
    simulations_stale: int = 0  # Older than 7 days


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """Verify the maintenance API key."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    if x_api_key != MAINTENANCE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


@router.get("/stats", response_model=CleanupStats)
async def get_cleanup_stats(x_api_key: Optional[str] = Header(None)):
    """
    Get current cleanup stats without performing cleanup.
    
    Useful for monitoring how much data would be cleaned up.
    """
    verify_api_key(x_api_key)
    
    now = datetime.now(timezone.utc)
    six_hours_ago = now - timedelta(hours=6)
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    db = SessionLocal()
    try:
        # Active games stats
        active_games_total = db.query(GameModel).filter(
            GameModel.status == "active"
        ).count()
        
        active_games_stale = db.query(GameModel).filter(
            GameModel.status == "active",
            GameModel.updated_at < twenty_four_hours_ago
        ).count()
        
        # AI decision logs stats
        ai_logs_total = db.query(AIDecisionLogModel).count()
        ai_logs_stale = db.query(AIDecisionLogModel).filter(
            AIDecisionLogModel.created_at < six_hours_ago
        ).count()
        
        # Game playback stats
        playback_total = db.query(GamePlaybackModel).count()
        playback_stale = db.query(GamePlaybackModel).filter(
            GamePlaybackModel.created_at < twenty_four_hours_ago
        ).count()
        
        # Simulation stats (7 day retention)
        seven_days_ago = now - timedelta(days=7)
        simulations_total = db.query(SimulationRunModel).count()
        simulations_stale = db.query(SimulationRunModel).filter(
            SimulationRunModel.created_at < seven_days_ago
        ).count()
        
        return CleanupStats(
            active_games_total=active_games_total,
            active_games_stale=active_games_stale,
            ai_logs_total=ai_logs_total,
            ai_logs_stale=ai_logs_stale,
            playback_total=playback_total,
            playback_stale=playback_stale,
            simulations_total=simulations_total,
            simulations_stale=simulations_stale,
        )
    finally:
        db.close()


@router.post("/cleanup", response_model=CleanupResult)
async def run_cleanup(x_api_key: Optional[str] = Header(None)):
    """
    Run all cleanup tasks.
    
    This endpoint is called by GitHub Actions on a schedule.
    Requires X-API-Key header for authentication.
    
    Tasks:
    1. Mark games as 'abandoned' if active for > 24 hours
    2. Delete AI decision logs older than 6 hours
    3. Delete game playback data older than 24 hours
    4. Delete simulation runs older than 7 days
    """
    verify_api_key(x_api_key)
    
    start_time = datetime.now(timezone.utc)
    now = start_time
    six_hours_ago = now - timedelta(hours=6)
    twenty_four_hours_ago = now - timedelta(hours=24)
    seven_days_ago = now - timedelta(days=7)
    
    games_abandoned = 0
    ai_logs_deleted = 0
    playback_deleted = 0
    simulations_deleted = 0
    
    db = SessionLocal()
    try:
        # 1. Mark abandoned games
        result = db.execute(
            text("""
                UPDATE games 
                SET status = 'abandoned', updated_at = NOW()
                WHERE status = 'active' 
                AND updated_at < :cutoff
            """),
            {"cutoff": twenty_four_hours_ago}
        )
        games_abandoned = result.rowcount
        logger.info(f"Marked {games_abandoned} games as abandoned")
        
        # 2. Delete old AI decision logs
        result = db.execute(
            text("""
                DELETE FROM ai_decision_logs 
                WHERE created_at < :cutoff
            """),
            {"cutoff": six_hours_ago}
        )
        ai_logs_deleted = result.rowcount
        logger.info(f"Deleted {ai_logs_deleted} AI decision logs")
        
        # 3. Delete old game playback data
        result = db.execute(
            text("""
                DELETE FROM game_playback 
                WHERE created_at < :cutoff
            """),
            {"cutoff": twenty_four_hours_ago}
        )
        playback_deleted = result.rowcount
        logger.info(f"Deleted {playback_deleted} game playback records")
        
        # 4. Delete old simulation runs (games cascade delete)
        result = db.execute(
            text("""
                DELETE FROM simulation_runs 
                WHERE created_at < :cutoff
            """),
            {"cutoff": seven_days_ago}
        )
        simulations_deleted = result.rowcount
        logger.info(f"Deleted {simulations_deleted} simulation runs")
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
    finally:
        db.close()
    
    end_time = datetime.now(timezone.utc)
    execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
    
    return CleanupResult(
        games_abandoned=games_abandoned,
        ai_logs_deleted=ai_logs_deleted,
        playback_deleted=playback_deleted,
        simulations_deleted=simulations_deleted,
        execution_time_ms=execution_time_ms,
    )
