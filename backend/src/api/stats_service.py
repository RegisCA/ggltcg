"""
Stats service for logging and analytics.

Handles AI decision logging, game playback recording, and player stats updates.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)


def _get_session_local():
    """Lazy import of SessionLocal to avoid requiring DATABASE_URL at import time."""
    from api.database import SessionLocal
    return SessionLocal


def _get_models():
    """Lazy import of database models."""
    from api.db_models import (
        AIDecisionLogModel,
        GamePlaybackModel,
        PlayerStatsModel,
        GameModel,
    )
    return AIDecisionLogModel, GamePlaybackModel, PlayerStatsModel, GameModel


class StatsService:
    """
    Service for managing game statistics and logging.
    
    Provides methods for:
    - Logging AI decisions (prompts/responses)
    - Recording game playback data
    - Updating player statistics
    - Cleaning up old records
    """
    
    def __init__(self, use_database: bool = True):
        """
        Initialize the stats service.
        
        Args:
            use_database: Whether to persist to database (False for testing)
        """
        self.use_database = use_database
    
    # ========================================
    # AI Decision Logging
    # ========================================
    
    def log_ai_decision(
        self,
        game_id: str,
        turn_number: int,
        player_id: str,
        model_name: str,
        prompts_version: str,
        prompt: str,
        response: str,
        action_number: Optional[int] = None,
        reasoning: Optional[str] = None,
        # v3 fields (Issue #260)
        ai_version: int = 2,
        turn_plan: Optional[dict] = None,
        plan_execution_status: Optional[str] = None,
        fallback_reason: Optional[str] = None,
        planned_action_index: Optional[int] = None,
    ) -> None:
        """
        Log an AI decision for debugging and analysis.
        
        Args:
            game_id: Game ID (UUID string)
            turn_number: Current turn number
            player_id: AI player ID in the game
            model_name: Gemini model name (e.g., "gemini-2.0-flash")
            prompts_version: Version of prompts.py (e.g., "1.0")
            prompt: Full prompt sent to the AI
            response: Raw response from the AI
            action_number: Parsed action number (if successful)
            reasoning: AI's reasoning (if parsed)
            ai_version: AI version (2 or 3)
            turn_plan: Full TurnPlan dict for v3 (stored with each action log entry)
            plan_execution_status: "complete" or "fallback"
            fallback_reason: Why fallback occurred (if any)
            planned_action_index: Which action in the plan (0-based)
        """
        if not self.use_database:
            logger.debug(f"AI decision logged (no-db): game={game_id}, turn={turn_number}, v={ai_version}")
            return
        
        SessionLocal = _get_session_local()
        AIDecisionLogModel, _, _, _ = _get_models()
        
        db = SessionLocal()
        try:
            log_entry = AIDecisionLogModel(
                game_id=uuid.UUID(game_id),
                turn_number=turn_number,
                player_id=player_id,
                model_name=model_name,
                prompts_version=prompts_version,
                prompt=prompt,
                response=response,
                action_number=action_number,
                reasoning=reasoning,
                # v3 fields
                ai_version=ai_version,
                turn_plan=turn_plan,
                plan_execution_status=plan_execution_status,
                fallback_reason=fallback_reason,
                planned_action_index=planned_action_index,
            )
            db.add(log_entry)
            db.commit()
            logger.debug(f"AI decision logged: game={game_id}, turn={turn_number}, model={model_name}, v={ai_version}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log AI decision: {e}")
            # Don't raise - logging is non-critical
        finally:
            db.close()
    
    # ========================================
    # Game Playback Recording
    # ========================================
    
    def record_game_playback(
        self,
        game_id: str,
        player1_id: str,
        player1_name: str,
        player2_id: str,
        player2_name: str,
        winner_id: Optional[str],
        starting_deck_p1: list[str],
        starting_deck_p2: list[str],
        first_player_id: str,
        play_by_play: list[dict],
        turn_count: int,
        game_started_at: Optional[datetime] = None,
        cc_tracking: Optional[list[dict]] = None,
    ) -> None:
        """
        Record a completed game for playback and analysis.
        
        Args:
            game_id: Game ID (UUID string)
            player1_id: Player 1 ID
            player1_name: Player 1 display name
            player2_id: Player 2 ID
            player2_name: Player 2 display name
            winner_id: Winner's player ID (None if tie/abandoned)
            starting_deck_p1: List of card names for player 1
            starting_deck_p2: List of card names for player 2
            first_player_id: ID of player who went first
            play_by_play: List of play-by-play entries
            turn_count: Total number of turns
            game_started_at: When the game was created (for duration calculation)
            cc_tracking: List of per-turn CC tracking records (Issue #252)
        """
        if not self.use_database:
            logger.debug(f"Game playback recorded (no-db): game={game_id}")
            return
        
        SessionLocal = _get_session_local()
        _, GamePlaybackModel, _, _ = _get_models()
        
        db = SessionLocal()
        try:
            # Check if playback already exists (idempotent)
            existing = db.query(GamePlaybackModel).filter(
                GamePlaybackModel.game_id == uuid.UUID(game_id)
            ).first()
            
            if existing:
                logger.debug(f"Playback already exists for game {game_id}")
                return
            
            playback = GamePlaybackModel(
                game_id=uuid.UUID(game_id),
                player1_id=player1_id,
                player1_name=player1_name,
                player2_id=player2_id,
                player2_name=player2_name,
                winner_id=winner_id,
                starting_deck_p1=starting_deck_p1,
                starting_deck_p2=starting_deck_p2,
                first_player_id=first_player_id,
                play_by_play=play_by_play,
                turn_count=turn_count,
                cc_tracking=cc_tracking,
                completed_at=datetime.now(timezone.utc),
            )
            # Set created_at to game start time if provided (for duration calculation)
            if game_started_at:
                playback.created_at = game_started_at
            db.add(playback)
            db.commit()
            logger.info(f"Game playback recorded: game={game_id}, turns={turn_count}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record game playback: {e}")
            # Don't raise - logging is non-critical
        finally:
            db.close()
    
    # ========================================
    # Player Stats Updates
    # ========================================
    
    def update_player_stats(
        self,
        player_id: str,
        display_name: str,
        won: bool,
        cards_used: list[str],
        tussles_initiated: int = 0,
        tussles_won: int = 0,
        turn_count: int = 0,
        game_duration_seconds: int = 0,
    ) -> None:
        """
        Update a player's statistics after a game.
        
        Args:
            player_id: Player ID (Google ID or AI ID)
            display_name: Player's display name
            won: Whether the player won
            cards_used: List of card names used in the game
            tussles_initiated: Number of tussles the player initiated
            tussles_won: Number of tussles the player won
            turn_count: Number of turns in the game
            game_duration_seconds: Duration of the game in seconds
        """
        if not self.use_database:
            logger.debug(f"Player stats updated (no-db): player={player_id}")
            return
        
        SessionLocal = _get_session_local()
        _, _, PlayerStatsModel, _ = _get_models()
        
        db = SessionLocal()
        try:
            # Get or create player stats
            stats = db.query(PlayerStatsModel).filter(
                PlayerStatsModel.player_id == player_id
            ).first()
            
            if not stats:
                stats = PlayerStatsModel(
                    player_id=player_id,
                    display_name=display_name,
                    games_played=0,
                    games_won=0,
                    total_tussles=0,
                    tussles_won=0,
                    total_turns=0,
                    total_game_duration_seconds=0,
                    card_stats={},
                )
                db.add(stats)
            
            # Update overall stats
            stats.games_played += 1
            if won:
                stats.games_won += 1
            stats.total_tussles += tussles_initiated
            stats.tussles_won += tussles_won
            stats.total_turns += turn_count
            stats.total_game_duration_seconds += game_duration_seconds
            stats.display_name = display_name  # Update display name in case it changed
            
            # Update card-specific stats
            card_stats = dict(stats.card_stats or {})
            for card_name in set(cards_used):  # Use set to count each card once per game
                if card_name not in card_stats:
                    card_stats[card_name] = {
                        "games_played": 0,
                        "games_won": 0,
                    }
                card_stats[card_name]["games_played"] += 1
                if won:
                    card_stats[card_name]["games_won"] += 1
            
            stats.card_stats = card_stats
            flag_modified(stats, 'card_stats')  # Ensure SQLAlchemy detects JSON change
            
            db.commit()
            logger.info(f"Player stats updated: player={player_id}, total_games={stats.games_played}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update player stats: {e}")
            # Don't raise - stats are non-critical
        finally:
            db.close()
    
    # ========================================
    # Data Retention Cleanup
    # ========================================
    
    def cleanup_old_ai_logs(self, max_age_hours: int = 6) -> int:
        """
        Delete AI decision logs older than the specified age.
        
        Args:
            max_age_hours: Maximum age in hours (default: 6)
            
        Returns:
            Number of records deleted
        """
        if not self.use_database:
            return 0
        
        SessionLocal = _get_session_local()
        AIDecisionLogModel, _, _, _ = _get_models()
        
        db = SessionLocal()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            deleted = db.query(AIDecisionLogModel).filter(
                AIDecisionLogModel.created_at < cutoff
            ).delete()
            db.commit()
            logger.info(f"Cleaned up {deleted} AI decision logs older than {max_age_hours} hour(s)")
            return deleted
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cleanup AI logs: {e}")
            return 0
        finally:
            db.close()
    
    def cleanup_old_playback(self, max_age_hours: int = 24) -> int:
        """
        Delete game playback records older than the specified age.
        
        Args:
            max_age_hours: Maximum age in hours (default: 24)
            
        Returns:
            Number of records deleted
        """
        if not self.use_database:
            return 0
        
        SessionLocal = _get_session_local()
        _, GamePlaybackModel, _, _ = _get_models()
        
        db = SessionLocal()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            deleted = db.query(GamePlaybackModel).filter(
                GamePlaybackModel.completed_at < cutoff
            ).delete()
            db.commit()
            logger.info(f"Cleaned up {deleted} game playback records older than {max_age_hours} hour(s)")
            return deleted
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cleanup playback records: {e}")
            return 0
        finally:
            db.close()
    
    def cleanup_old_simulations(self, max_age_days: int = 7) -> int:
        """
        Delete simulation runs older than the specified age.
        
        Simulation games are deleted via CASCADE when the run is deleted.
        
        Args:
            max_age_days: Maximum age in days (default: 7)
            
        Returns:
            Number of simulation runs deleted
        """
        if not self.use_database:
            return 0
        
        SessionLocal = _get_session_local()
        
        db = SessionLocal()
        try:
            from .db_models import SimulationRunModel
            
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            deleted = db.query(SimulationRunModel).filter(
                SimulationRunModel.created_at < cutoff
            ).delete()
            db.commit()
            logger.info(f"Cleaned up {deleted} simulation runs older than {max_age_days} day(s)")
            return deleted
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cleanup simulation runs: {e}")
            return 0
        finally:
            db.close()
    
    # ========================================
    # Query Methods (for future stats API)
    # ========================================
    
    def get_player_stats(self, player_id: str) -> Optional[dict]:
        """
        Get statistics for a specific player.
        
        Args:
            player_id: Player ID
            
        Returns:
            Dict with player stats or None if not found
        """
        if not self.use_database:
            return None
        
        SessionLocal = _get_session_local()
        _, _, PlayerStatsModel, _ = _get_models()
        
        db = SessionLocal()
        try:
            stats = db.query(PlayerStatsModel).filter(
                PlayerStatsModel.player_id == player_id
            ).first()
            
            if not stats:
                return None
            
            return {
                "player_id": stats.player_id,
                "display_name": stats.display_name,
                "games_played": stats.games_played,
                "games_won": stats.games_won,
                "win_rate": stats.win_rate,
                "total_tussles": stats.total_tussles,
                "tussles_won": stats.tussles_won,
                "avg_turns": stats.avg_turns,
                "avg_game_duration_seconds": stats.avg_game_duration_seconds,
                "card_stats": stats.card_stats,
            }
        except Exception as e:
            logger.error(f"Failed to get player stats: {e}")
            return None
        finally:
            db.close()
    
    def get_leaderboard(self, limit: int = 10, min_games: int = 3) -> list[dict]:
        """
        Get top players by win rate.
        
        Args:
            limit: Maximum number of players to return
            min_games: Minimum games played to qualify
            
        Returns:
            List of player stats dicts ordered by win rate
        """
        if not self.use_database:
            return []
        
        SessionLocal = _get_session_local()
        _, _, PlayerStatsModel, _ = _get_models()
        
        db = SessionLocal()
        try:
            # Get players with minimum games, calculate win rate in Python for reliability
            stats_list = db.query(PlayerStatsModel).filter(
                PlayerStatsModel.games_played >= min_games
            ).all()
            
            # Sort by win rate (descending), then by total wins (descending)
            stats_list.sort(
                key=lambda s: (s.win_rate, s.games_won),
                reverse=True
            )
            
            # Take top N
            stats_list = stats_list[:limit]
            
            return [
                {
                    "player_id": s.player_id,
                    "display_name": s.display_name,
                    "games_played": s.games_played,
                    "games_won": s.games_won,
                    "win_rate": s.win_rate,
                }
                for s in stats_list
            ]
        except Exception as e:
            logger.error(f"Failed to get leaderboard: {e}")
            return []
        finally:
            db.close()
    
    def get_card_leaderboard(
        self,
        card_name: str,
        limit: int = 10,
        min_games: int = 3,
    ) -> list[dict]:
        """
        Get top players by win rate with a specific card.
        
        Args:
            card_name: Name of the card
            limit: Maximum number of players to return
            min_games: Minimum games with this card to qualify
            
        Returns:
            List of player stats dicts ordered by win rate with card
        """
        if not self.use_database:
            return []
        
        SessionLocal = _get_session_local()
        _, _, PlayerStatsModel, _ = _get_models()
        
        db = SessionLocal()
        try:
            # Get all players who have used this card
            all_stats = db.query(PlayerStatsModel).all()
            
            # Filter and calculate card-specific stats
            card_stats_list = []
            for stats in all_stats:
                if not stats.card_stats or card_name not in stats.card_stats:
                    continue
                
                card_data = stats.card_stats[card_name]
                games_played = card_data.get("games_played", 0)
                games_won = card_data.get("games_won", 0)
                
                if games_played < min_games:
                    continue
                
                win_rate = (games_won / games_played * 100) if games_played > 0 else 0.0
                
                card_stats_list.append({
                    "player_id": stats.player_id,
                    "display_name": stats.display_name,
                    "games_played": games_played,
                    "games_won": games_won,
                    "win_rate": win_rate,
                })
            
            # Sort by win rate (descending), then by total wins (descending)
            card_stats_list.sort(
                key=lambda s: (s["win_rate"], s["games_won"]),
                reverse=True
            )
            
            return card_stats_list[:limit]
        except Exception as e:
            logger.error(f"Failed to get card leaderboard: {e}")
            return []
        finally:
            db.close()


# Global singleton instance
_stats_service: Optional[StatsService] = None


def get_stats_service() -> StatsService:
    """
    Get the global StatsService instance.
    
    Returns:
        StatsService instance
    """
    global _stats_service
    if _stats_service is None:
        _stats_service = StatsService()
    return _stats_service
