"""
Tests for Stats API routes.

Tests the /stats/* endpoints for leaderboard and player stats.
"""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add backend/src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.app import app


client = TestClient(app)


class TestPlayerStatsEndpoint:
    """Tests for GET /stats/players/{player_id}"""
    
    def test_get_player_stats_not_found(self):
        """Test 404 when player has no stats."""
        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_player_stats.return_value = None
            mock_get_service.return_value = mock_service
            
            response = client.get("/stats/players/nonexistent-player")
            
            assert response.status_code == 404
            assert "No stats found" in response.json()["detail"]
    
    def test_get_player_stats_success(self):
        """Test successful player stats retrieval."""
        mock_stats = {
            "player_id": "test-player-123",
            "display_name": "TestPlayer",
            "games_played": 10,
            "games_won": 7,
            "win_rate": 70.0,
            "total_tussles": 25,
            "tussles_won": 18,
            "card_stats": {
                "Ka": {"games_played": 8, "games_won": 6},
                "Knight": {"games_played": 5, "games_won": 3},
            },
        }
        
        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_player_stats.return_value = mock_stats
            mock_get_service.return_value = mock_service
            
            response = client.get("/stats/players/test-player-123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["player_id"] == "test-player-123"
            assert data["display_name"] == "TestPlayer"
            assert data["games_played"] == 10
            assert data["games_won"] == 7
            assert data["win_rate"] == 70.0
            assert data["total_tussles"] == 25
            assert data["tussles_won"] == 18
            assert data["tussle_win_rate"] == 72.0
            assert len(data["card_stats"]) == 2
    
    def test_get_player_stats_card_stats_sorted(self):
        """Test that card stats are sorted by games played."""
        mock_stats = {
            "player_id": "test-player",
            "display_name": "Test",
            "games_played": 10,
            "games_won": 5,
            "win_rate": 50.0,
            "total_tussles": 0,
            "tussles_won": 0,
            "card_stats": {
                "Rush": {"games_played": 2, "games_won": 1},
                "Ka": {"games_played": 8, "games_won": 4},
                "Knight": {"games_played": 5, "games_won": 2},
            },
        }
        
        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_player_stats.return_value = mock_stats
            mock_get_service.return_value = mock_service
            
            response = client.get("/stats/players/test-player")
            
            assert response.status_code == 200
            data = response.json()
            card_names = [cs["card_name"] for cs in data["card_stats"]]
            # Should be sorted by games_played descending
            assert card_names == ["Ka", "Knight", "Rush"]


class TestLeaderboardEndpoint:
    """Tests for GET /stats/leaderboard"""
    
    def test_get_leaderboard_empty(self):
        """Test leaderboard with no qualifying players."""
        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_leaderboard.return_value = []
            mock_get_service.return_value = mock_service
            
            response = client.get("/stats/leaderboard")
            
            assert response.status_code == 200
            data = response.json()
            assert data["entries"] == []
            assert data["total_players"] == 0
    
    def test_get_leaderboard_success(self):
        """Test successful leaderboard retrieval."""
        mock_leaderboard = [
            {"player_id": "p1", "display_name": "Player1", "games_played": 10, "games_won": 8, "win_rate": 80.0},
            {"player_id": "p2", "display_name": "Player2", "games_played": 10, "games_won": 6, "win_rate": 60.0},
            {"player_id": "p3", "display_name": "Player3", "games_played": 10, "games_won": 5, "win_rate": 50.0},
        ]
        
        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_leaderboard.return_value = mock_leaderboard
            mock_get_service.return_value = mock_service
            
            response = client.get("/stats/leaderboard")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_players"] == 3
            assert len(data["entries"]) == 3
            
            # Check ranks are assigned correctly
            assert data["entries"][0]["rank"] == 1
            assert data["entries"][0]["display_name"] == "Player1"
            assert data["entries"][1]["rank"] == 2
            assert data["entries"][2]["rank"] == 3
    
    def test_get_leaderboard_with_params(self):
        """Test leaderboard with custom limit and min_games."""
        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_leaderboard.return_value = []
            mock_get_service.return_value = mock_service
            
            response = client.get("/stats/leaderboard?limit=5&min_games=10")
            
            assert response.status_code == 200
            data = response.json()
            assert data["min_games_required"] == 10
            
            # Verify service was called with correct params
            mock_service.get_leaderboard.assert_called_once_with(limit=5, min_games=10)
    
    def test_get_leaderboard_limit_validation(self):
        """Test that limit parameter is validated."""
        # Limit too high
        response = client.get("/stats/leaderboard?limit=101")
        assert response.status_code == 422  # Validation error
        
        # Limit too low
        response = client.get("/stats/leaderboard?limit=0")
        assert response.status_code == 422


class TestCardLeaderboardEndpoint:
    """Tests for GET /stats/leaderboard/card/{card_name}"""
    
    def test_get_card_leaderboard_empty(self):
        """Test card leaderboard with no qualifying players."""
        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_card_leaderboard.return_value = []
            mock_get_service.return_value = mock_service
            
            response = client.get("/stats/leaderboard/card/Ka")
            
            assert response.status_code == 200
            data = response.json()
            assert data["entries"] == []
            assert data["card_name"] == "Ka"
    
    def test_get_card_leaderboard_success(self):
        """Test successful card leaderboard retrieval."""
        mock_leaderboard = [
            {"player_id": "p1", "display_name": "KaMaster", "games_played": 10, "games_won": 9, "win_rate": 90.0},
            {"player_id": "p2", "display_name": "KaFan", "games_played": 8, "games_won": 5, "win_rate": 62.5},
        ]
        
        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_card_leaderboard.return_value = mock_leaderboard
            mock_get_service.return_value = mock_service
            
            response = client.get("/stats/leaderboard/card/Ka")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_players"] == 2
            assert data["card_name"] == "Ka"
            assert data["entries"][0]["rank"] == 1
            assert data["entries"][0]["display_name"] == "KaMaster"
    
    def test_get_card_leaderboard_url_encoded_name(self):
        """Test card leaderboard with URL-encoded card name."""
        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_card_leaderboard.return_value = []
            mock_get_service.return_value = mock_service
            
            # Card name with space (if any)
            response = client.get("/stats/leaderboard/card/Copy%20of%20Ka")
            
            assert response.status_code == 200
            mock_service.get_card_leaderboard.assert_called_once()
            call_args = mock_service.get_card_leaderboard.call_args
            assert call_args.kwargs["card_name"] == "Copy of Ka"


class TestStatsServiceIntegration:
    """Tests for StatsService card leaderboard method."""
    
    def test_get_card_leaderboard_no_db(self):
        """Test card leaderboard returns empty without database."""
        from api.stats_service import StatsService
        
        service = StatsService(use_database=False)
        result = service.get_card_leaderboard("Ka", limit=10, min_games=3)
        
        assert result == []
    
    def test_get_leaderboard_with_min_games_no_db(self):
        """Test leaderboard with min_games param without database."""
        from api.stats_service import StatsService
        
        service = StatsService(use_database=False)
        result = service.get_leaderboard(limit=10, min_games=5)
        
        assert result == []
