"""
Stats API routes for leaderboards and player statistics.

Endpoints for retrieving player stats and leaderboard data.
"""

import logging
from fastapi import APIRouter, HTTPException, Query

from api.schemas import (
    PlayerStatsResponse,
    LeaderboardResponse,
    LeaderboardEntry,
    CardStatsResponse,
)
from api.stats_service import get_stats_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["stats"])


# ============================================================================
# Player Stats Endpoints
# ============================================================================


@router.get("/players/{player_id}", response_model=PlayerStatsResponse)
async def get_player_stats(player_id: str) -> PlayerStatsResponse:
    """
    Get statistics for a specific player.
    
    - **player_id**: The player's ID (Google ID for authenticated users, or AI ID)
    
    Returns player's overall stats including games played, win rate, and card usage.
    """
    stats_service = get_stats_service()
    stats = stats_service.get_player_stats(player_id)
    
    if stats is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stats found for player {player_id}"
        )
    
    # Convert card_stats dict to list of CardStatsResponse
    card_stats_list = []
    if stats.get("card_stats"):
        for card_name, card_data in stats["card_stats"].items():
            games_played = card_data.get("games_played", 0)
            games_won = card_data.get("games_won", 0)
            win_rate = (games_won / games_played * 100) if games_played > 0 else 0.0
            card_stats_list.append(CardStatsResponse(
                card_name=card_name,
                games_played=games_played,
                games_won=games_won,
                win_rate=round(win_rate, 1),
            ))
    
    # Sort by games played descending
    card_stats_list.sort(key=lambda x: x.games_played, reverse=True)
    
    return PlayerStatsResponse(
        player_id=stats["player_id"],
        display_name=stats["display_name"],
        games_played=stats["games_played"],
        games_won=stats["games_won"],
        win_rate=round(stats["win_rate"], 1),
        total_tussles=stats["total_tussles"],
        tussles_won=stats["tussles_won"],
        tussle_win_rate=round(
            (stats["tussles_won"] / stats["total_tussles"] * 100)
            if stats["total_tussles"] > 0 else 0.0,
            1
        ),
        card_stats=card_stats_list,
    )


# ============================================================================
# Leaderboard Endpoints
# ============================================================================


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=100, description="Number of players to return"),
    min_games: int = Query(default=3, ge=1, le=100, description="Minimum games played to qualify"),
) -> LeaderboardResponse:
    """
    Get the top players leaderboard.
    
    - **limit**: Maximum number of players to return (default: 10)
    - **min_games**: Minimum games required to appear on leaderboard (default: 3)
    
    Returns players sorted by win rate (descending), then by total wins.
    """
    stats_service = get_stats_service()
    leaderboard = stats_service.get_leaderboard(limit=limit, min_games=min_games)
    
    entries = []
    for rank, player in enumerate(leaderboard, start=1):
        entries.append(LeaderboardEntry(
            rank=rank,
            player_id=player["player_id"],
            display_name=player["display_name"],
            games_played=player["games_played"],
            games_won=player["games_won"],
            win_rate=round(player["win_rate"], 1),
        ))
    
    return LeaderboardResponse(
        entries=entries,
        total_players=len(entries),
        min_games_required=min_games,
    )


@router.get("/leaderboard/card/{card_name}", response_model=LeaderboardResponse)
async def get_card_leaderboard(
    card_name: str,
    limit: int = Query(default=10, ge=1, le=100, description="Number of players to return"),
    min_games: int = Query(default=3, ge=1, le=100, description="Minimum games with card to qualify"),
) -> LeaderboardResponse:
    """
    Get the leaderboard for players using a specific card.
    
    - **card_name**: Name of the card (e.g., "Ka", "Knight", "Clean")
    - **limit**: Maximum number of players to return (default: 10)
    - **min_games**: Minimum games with this card to appear (default: 3)
    
    Returns players with highest win rate when using the specified card.
    """
    stats_service = get_stats_service()
    leaderboard = stats_service.get_card_leaderboard(
        card_name=card_name,
        limit=limit,
        min_games=min_games,
    )
    
    entries = []
    for rank, player in enumerate(leaderboard, start=1):
        entries.append(LeaderboardEntry(
            rank=rank,
            player_id=player["player_id"],
            display_name=player["display_name"],
            games_played=player["games_played"],
            games_won=player["games_won"],
            win_rate=round(player["win_rate"], 1),
        ))
    
    return LeaderboardResponse(
        entries=entries,
        total_players=len(entries),
        min_games_required=min_games,
        card_name=card_name,
    )
