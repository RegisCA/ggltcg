"""
Admin routes for viewing database data.

Simple data viewer for debugging and monitoring.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .database import SessionLocal
from .db_models import (
    AIDecisionLogModel,
    GamePlaybackModel,
    GameModel,
    PlayerStatsModel,
    UserModel
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


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


@router.get("/ai-logs")
async def get_ai_logs(
    limit: int = Query(50, ge=1, le=200),
    game_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get recent AI decision logs.
    
    Shows Gemini prompts and responses for debugging.
    
    Args:
        limit: Maximum number of logs to return (default 50, max 200)
        game_id: Optional filter by game ID
        db: Database session
        
    Returns:
        List of AI decision logs with prompts and responses
    """
    query = db.query(AIDecisionLogModel).order_by(desc(AIDecisionLogModel.created_at))
    
    if game_id:
        query = query.filter(AIDecisionLogModel.game_id == game_id)
    
    logs = query.limit(limit).all()
    
    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "game_id": str(log.game_id),
                "turn_number": log.turn_number,
                "player_id": log.player_id,
                "model_name": log.model_name,
                "prompts_version": log.prompts_version,
                "prompt": log.prompt,
                "response": log.response,
                "action_number": log.action_number,
                "reasoning": log.reasoning,
                "created_at": log.created_at.isoformat(),
                # V3 fields
                "ai_version": log.ai_version,
                "turn_plan": log.turn_plan,
                "plan_execution_status": log.plan_execution_status,
                "fallback_reason": log.fallback_reason,
                "planned_action_index": log.planned_action_index,
            }
            for log in logs
        ]
    }


@router.get("/ai-logs/{log_id}")
async def get_ai_log(
    log_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific AI decision log by ID.
    
    Args:
        log_id: AI decision log ID
        db: Database session
        
    Returns:
        AI decision log details
    """
    log = db.query(AIDecisionLogModel).filter(AIDecisionLogModel.id == log_id).first()
    
    if not log:
        raise HTTPException(status_code=404, detail="AI log not found")
    
    return {
        "id": log.id,
        "game_id": str(log.game_id),
        "turn_number": log.turn_number,
        "player_id": log.player_id,
        "model_name": log.model_name,
        "prompts_version": log.prompts_version,
        "prompt": log.prompt,
        "response": log.response,
        "action_number": log.action_number,
        "reasoning": log.reasoning,
        "created_at": log.created_at.isoformat(),
        # V3 fields
        "ai_version": log.ai_version,
        "turn_plan": log.turn_plan,
        "plan_execution_status": log.plan_execution_status,
        "fallback_reason": log.fallback_reason,
        "planned_action_index": log.planned_action_index,
    }


@router.get("/game-playbacks")
async def get_game_playbacks(
    limit: int = Query(20, ge=1, le=100),
    winner_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get recent completed game playbacks.
    
    Shows game summaries with play-by-play.
    
    Args:
        limit: Maximum number of games to return (default 20, max 100)
        winner_id: Optional filter by winner player ID
        db: Database session
        
    Returns:
        List of game playback summaries
    """
    query = db.query(GamePlaybackModel).order_by(desc(GamePlaybackModel.created_at))
    
    if winner_id:
        query = query.filter(GamePlaybackModel.winner_id == winner_id)
    
    games = query.limit(limit).all()
    
    return {
        "count": len(games),
        "games": [
            {
                "id": game.id,
                "game_id": str(game.game_id),
                "player1_id": game.player1_id,
                "player1_name": game.player1_name,
                "player2_id": game.player2_id,
                "player2_name": game.player2_name,
                "winner_id": game.winner_id,
                "turn_count": game.turn_count,
                "created_at": game.created_at.isoformat(),
                "completed_at": game.completed_at.isoformat() if game.completed_at else None,
            }
            for game in games
        ]
    }


@router.get("/game-playbacks/{game_id}")
async def get_game_playback(
    game_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed game playback for a specific game.
    
    Args:
        game_id: Game ID (UUID)
        db: Database session
        
    Returns:
        Complete game playback with play-by-play
    """
    game = db.query(GamePlaybackModel).filter(
        GamePlaybackModel.game_id == game_id
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game playback not found")
    
    return {
        "id": game.id,
        "game_id": str(game.game_id),
        "player1_id": game.player1_id,
        "player1_name": game.player1_name,
        "player2_id": game.player2_id,
        "player2_name": game.player2_name,
        "winner_id": game.winner_id,
        "first_player_id": game.first_player_id,
        "starting_deck_p1": game.starting_deck_p1,
        "starting_deck_p2": game.starting_deck_p2,
        "play_by_play": game.play_by_play,
        "turn_count": game.turn_count,
        "cc_tracking": game.cc_tracking,
        "created_at": game.created_at.isoformat(),
        "completed_at": game.completed_at.isoformat() if game.completed_at else None,
    }


@router.get("/games")
async def get_games(
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get recent games.
    
    Args:
        limit: Maximum number of games to return (default 20, max 100)
        status: Optional filter by status (active, completed, abandoned, etc.)
        db: Database session
        
    Returns:
        List of games with metadata
    """
    query = db.query(GameModel).order_by(desc(GameModel.updated_at))
    
    if status:
        query = query.filter(GameModel.status == status)
    
    games = query.limit(limit).all()
    
    return {
        "count": len(games),
        "games": [
            {
                "id": str(game.id),
                "status": game.status,
                "player1_id": game.player1_id,
                "player1_name": game.player1_name,
                "player2_id": game.player2_id,
                "player2_name": game.player2_name,
                "game_code": game.game_code,
                "turn_number": game.turn_number,
                "phase": game.phase,
                "winner_id": game.winner_id,
                "created_at": game.created_at.isoformat(),
                "updated_at": game.updated_at.isoformat(),
            }
            for game in games
        ]
    }


@router.get("/games/{game_id}")
async def get_game(
    game_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed game state.
    
    Args:
        game_id: Game ID (UUID)
        db: Database session
        
    Returns:
        Complete game state including JSONB data
    """
    game = db.query(GameModel).filter(GameModel.id == game_id).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return {
        "id": str(game.id),
        "status": game.status,
        "player1_id": game.player1_id,
        "player1_name": game.player1_name,
        "player2_id": game.player2_id,
        "player2_name": game.player2_name,
        "game_code": game.game_code,
        "turn_number": game.turn_number,
        "phase": game.phase,
        "active_player_id": game.active_player_id,
        "winner_id": game.winner_id,
        "created_at": game.created_at.isoformat(),
        "updated_at": game.updated_at.isoformat(),
        "game_state": game.game_state,
    }


@router.get("/players")
async def get_players(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get player statistics.
    
    Args:
        limit: Maximum number of players to return (default 20, max 100)
        db: Database session
        
    Returns:
        List of player stats ordered by wins
    """
    players = db.query(PlayerStatsModel).order_by(
        desc(PlayerStatsModel.games_won)
    ).limit(limit).all()
    
    return {
        "count": len(players),
        "players": [
            {
                "player_id": player.player_id,
                "display_name": player.display_name,
                "games_played": player.games_played,
                "games_won": player.games_won,
                "win_rate": player.win_rate,
                "total_tussles": player.total_tussles,
                "tussles_won": player.tussles_won,
                "card_stats": player.card_stats,
                "created_at": player.created_at.isoformat(),
                "updated_at": player.updated_at.isoformat(),
            }
            for player in players
        ]
    }


@router.get("/users")
async def get_users(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get registered users with game stats.
    
    Args:
        limit: Maximum number of users to return (default 20, max 100)
        db: Database session
        
    Returns:
        List of users with player stats and last game info
    """
    users = db.query(UserModel).order_by(
        desc(UserModel.created_at)
    ).limit(limit).all()
    
    user_data = []
    for user in users:
        # Get player stats if they exist
        player_stats = db.query(PlayerStatsModel).filter(
            PlayerStatsModel.player_id == user.google_id
        ).first()
        
        # Get last game played (either as player1 or player2)
        last_game = db.query(GameModel).filter(
            (GameModel.player1_id == user.google_id) | 
            (GameModel.player2_id == user.google_id)
        ).order_by(desc(GameModel.updated_at)).first()
        
        user_data.append({
            "google_id": user.google_id,
            "first_name": user.first_name,
            "display_name": user.display_name,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "games_played": player_stats.games_played if player_stats else 0,
            "games_won": player_stats.games_won if player_stats else 0,
            "win_rate": player_stats.win_rate if player_stats else 0.0,
            "avg_turns": player_stats.avg_turns if player_stats else 0.0,
            "avg_game_duration_seconds": player_stats.avg_game_duration_seconds if player_stats else 0.0,
            "last_game_at": last_game.updated_at.isoformat() if last_game else None,
            "last_game_status": last_game.status if last_game else None,
            "favorite_decks": user.favorite_decks if user.favorite_decks else [[], [], []],
        })
    
    return {
        "count": len(user_data),
        "users": user_data
    }


@router.get("/stats/summary")
async def get_summary_stats(db: Session = Depends(get_db)):
    """
    Get summary statistics for the admin dashboard.
    
    Returns:
        Summary counts and recent activity
    """
    # Count records in each table
    total_users = db.query(UserModel).count()
    total_games = db.query(GameModel).count()
    active_games = db.query(GameModel).filter(GameModel.status == 'active').count()
    completed_games = db.query(GameModel).filter(GameModel.status == 'completed').count()
    total_ai_logs = db.query(AIDecisionLogModel).count()
    total_playbacks = db.query(GamePlaybackModel).count()
    
    # Recent AI logs (last hour)
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_ai_logs = db.query(AIDecisionLogModel).filter(
        AIDecisionLogModel.created_at >= one_hour_ago
    ).count()
    
    # Recent games (last 24 hours)
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    recent_games = db.query(GameModel).filter(
        GameModel.created_at >= one_day_ago
    ).count()
    
    return {
        "users": {
            "total": total_users
        },
        "games": {
            "total": total_games,
            "active": active_games,
            "completed": completed_games,
            "recent_24h": recent_games
        },
        "ai_logs": {
            "total": total_ai_logs,
            "recent_1h": recent_ai_logs
        },
        "playbacks": {
            "total": total_playbacks
        }
    }
