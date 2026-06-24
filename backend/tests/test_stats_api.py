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


class TestCardStatsAggregateEndpoint:
    """Tests for GET /stats/cards"""

    def test_get_card_stats_empty(self):
        """Test card stats with no data."""
        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_card_stats_aggregate.return_value = ([], 0)
            mock_get_service.return_value = mock_service

            response = client.get("/stats/cards")

            assert response.status_code == 200
            data = response.json()
            assert data["entries"] == []
            assert data["total_cards"] == 0
            assert data["total_games"] == 0

    def test_get_card_stats_success(self):
        """Test successful card stats retrieval, ranked and shaped."""
        mock_cards = [
            {
                "card_name": "Ka", "games_played": 20, "games_won": 16,
                "games_lost": 4, "win_rate": 80.0, "pick_rate": 50.0,
                "player_count": 3,
            },
            {
                "card_name": "Knight", "games_played": 10, "games_won": 4,
                "games_lost": 6, "win_rate": 40.0, "pick_rate": 25.0,
                "player_count": 2,
            },
        ]

        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_card_stats_aggregate.return_value = (mock_cards, 40)
            mock_get_service.return_value = mock_service

            response = client.get("/stats/cards")

            assert response.status_code == 200
            data = response.json()
            assert data["total_cards"] == 2
            assert data["total_games"] == 40
            assert data["entries"][0]["rank"] == 1
            assert data["entries"][0]["card_name"] == "Ka"
            assert data["entries"][0]["games_lost"] == 4
            assert data["entries"][0]["pick_rate"] == 50.0
            assert data["entries"][0]["player_count"] == 3
            assert data["entries"][1]["rank"] == 2

    def test_get_card_stats_with_params(self):
        """Test card stats passes min_games to the service."""
        with patch('api.routes_stats.get_stats_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_card_stats_aggregate.return_value = ([], 0)
            mock_get_service.return_value = mock_service

            response = client.get("/stats/cards?limit=10&min_games=5")

            assert response.status_code == 200
            assert response.json()["min_games_required"] == 5
            mock_service.get_card_stats_aggregate.assert_called_once_with(min_games=5)

    def test_get_card_stats_limit_validation(self):
        """Test that limit parameter is validated."""
        assert client.get("/stats/cards?limit=201").status_code == 422
        assert client.get("/stats/cards?limit=0").status_code == 422


class TestStatsServiceIntegration:
    """Tests for StatsService card leaderboard method."""

    def test_get_card_leaderboard_no_db(self):
        """Test card leaderboard returns empty without database."""
        from api.stats_service import StatsService

        service = StatsService(use_database=False)
        result = service.get_card_leaderboard("Ka", limit=10, min_games=3)

        assert result == []

    def test_get_card_stats_aggregate_no_db(self):
        """Test card stats aggregate returns empty without database."""
        from api.stats_service import StatsService

        service = StatsService(use_database=False)
        result = service.get_card_stats_aggregate(min_games=1)

        assert result == ([], 0)

    def test_get_card_stats_aggregate_sums_across_players(self):
        """Test aggregation sums per-card stats across all players (real DB)."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from api.db_models import Base, PlayerStatsModel
        from api.stats_service import StatsService

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine)

        # Two players both used Ka; only player1 used Knight
        seed = TestSession()
        seed.add_all([
            PlayerStatsModel(
                player_id="p1", display_name="Alice",
                games_played=10, games_won=6,
                total_tussles=0, tussles_won=0,
                card_stats={
                    "Ka": {"games_played": 8, "games_won": 5},
                    "Knight": {"games_played": 4, "games_won": 1},
                },
            ),
            PlayerStatsModel(
                player_id="p2", display_name="Bob",
                games_played=6, games_won=2,
                total_tussles=0, tussles_won=0,
                card_stats={
                    "Ka": {"games_played": 6, "games_won": 3},
                },
            ),
        ])
        seed.commit()
        seed.close()

        service = StatsService(use_database=True)
        with patch('api.stats_service._get_session_local', return_value=TestSession):
            cards, total_games = service.get_card_stats_aggregate(min_games=1)

        assert total_games == 16  # 10 + 6
        by_name = {c["card_name"]: c for c in cards}

        ka = by_name["Ka"]
        assert ka["games_played"] == 14  # 8 + 6
        assert ka["games_won"] == 8       # 5 + 3
        assert ka["games_lost"] == 6
        assert ka["player_count"] == 2
        assert ka["win_rate"] == 8 / 14 * 100
        assert ka["pick_rate"] == 14 / 16 * 100

        knight = by_name["Knight"]
        assert knight["games_played"] == 4
        assert knight["player_count"] == 1

        # Sorted by win rate descending: Ka (57%) before Knight (25%)
        assert [c["card_name"] for c in cards] == ["Ka", "Knight"]

    def test_get_card_stats_aggregate_min_games_filter(self):
        """Test that min_games filters out rarely-picked cards (real DB)."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from api.db_models import Base, PlayerStatsModel
        from api.stats_service import StatsService

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine)

        seed = TestSession()
        seed.add(PlayerStatsModel(
            player_id="p1", display_name="Alice",
            games_played=5, games_won=3,
            total_tussles=0, tussles_won=0,
            card_stats={
                "Ka": {"games_played": 5, "games_won": 3},
                "Rush": {"games_played": 1, "games_won": 0},
            },
        ))
        seed.commit()
        seed.close()

        service = StatsService(use_database=True)
        with patch('api.stats_service._get_session_local', return_value=TestSession):
            cards, _ = service.get_card_stats_aggregate(min_games=3)

        assert [c["card_name"] for c in cards] == ["Ka"]
    
    def test_get_leaderboard_with_min_games_no_db(self):
        """Test leaderboard with min_games param without database."""
        from api.stats_service import StatsService
        
        service = StatsService(use_database=False)
        result = service.get_leaderboard(limit=10, min_games=5)
        
        assert result == []
