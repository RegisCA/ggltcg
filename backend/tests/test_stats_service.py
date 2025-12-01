"""
Tests for the StatsService (AI decision logging, game playback, player stats).

These tests verify the data logging and statistics functionality.
"""

import uuid
from unittest.mock import patch

# Add backend/src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestStatsServiceNoDb:
    """Tests for StatsService without database (unit tests)."""
    
    def test_log_ai_decision_no_db(self):
        """Test that logging works without database."""
        from api.stats_service import StatsService
        
        service = StatsService(use_database=False)
        
        # Should not raise even without database
        service.log_ai_decision(
            game_id=str(uuid.uuid4()),
            turn_number=1,
            player_id="ai-player-1",
            model_name="gemini-2.0-flash",
            prompts_version="1.0",
            prompt="Test prompt",
            response='{"action_number": 1, "reasoning": "Test"}',
            action_number=1,
            reasoning="Test",
        )
    
    def test_record_game_playback_no_db(self):
        """Test that playback recording works without database."""
        from api.stats_service import StatsService
        
        service = StatsService(use_database=False)
        
        # Should not raise even without database
        service.record_game_playback(
            game_id=str(uuid.uuid4()),
            player1_id="player1",
            player1_name="Alice",
            player2_id="player2",
            player2_name="Bob",
            winner_id="player1",
            starting_deck_p1=["Ka", "Knight", "Clean", "Rush", "Wizard", "Demideca"],
            starting_deck_p2=["Ka", "Knight", "Clean", "Rush", "Wizard", "Demideca"],
            first_player_id="player1",
            play_by_play=[
                {"turn": 1, "player": "Alice", "description": "Played Ka"},
            ],
            turn_count=5,
        )
    
    def test_update_player_stats_no_db(self):
        """Test that player stats update works without database."""
        from api.stats_service import StatsService
        
        service = StatsService(use_database=False)
        
        # Should not raise even without database
        service.update_player_stats(
            player_id="player1",
            display_name="Alice",
            won=True,
            cards_used=["Ka", "Knight", "Clean"],
            tussles_initiated=3,
            tussles_won=2,
        )
    
    def test_cleanup_no_db_returns_zero(self):
        """Test that cleanup returns 0 without database."""
        from api.stats_service import StatsService
        
        service = StatsService(use_database=False)
        
        assert service.cleanup_old_ai_logs() == 0
        assert service.cleanup_old_playback() == 0
    
    def test_get_player_stats_no_db_returns_none(self):
        """Test that get_player_stats returns None without database."""
        from api.stats_service import StatsService
        
        service = StatsService(use_database=False)
        
        assert service.get_player_stats("player1") is None
    
    def test_get_leaderboard_no_db_returns_empty(self):
        """Test that leaderboard returns empty list without database."""
        from api.stats_service import StatsService
        
        service = StatsService(use_database=False)
        
        assert service.get_leaderboard() == []


class TestPromptsVersion:
    """Tests for prompts version tracking."""
    
    def test_prompts_version_exists(self):
        """Test that PROMPTS_VERSION is defined."""
        from game_engine.ai.prompts import PROMPTS_VERSION
        
        assert PROMPTS_VERSION is not None
        assert isinstance(PROMPTS_VERSION, str)
        assert len(PROMPTS_VERSION) > 0
    
    def test_prompts_version_format(self):
        """Test that PROMPTS_VERSION follows expected format (MAJOR.MINOR)."""
        from game_engine.ai.prompts import PROMPTS_VERSION
        
        parts = PROMPTS_VERSION.split(".")
        assert len(parts) >= 1, "Version should have at least one part"
        # Should be numeric
        for part in parts:
            assert part.isdigit(), f"Version part '{part}' should be numeric"


class TestLLMPlayerDecisionInfo:
    """Tests for LLMPlayer decision info tracking."""
    
    def test_get_last_decision_info_initial(self):
        """Test that get_last_decision_info returns empty info initially."""
        # Mock the API key to avoid requiring real credentials
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.generativeai.configure'):
                with patch('google.generativeai.GenerativeModel'):
                    from game_engine.ai.llm_player import LLMPlayer
                    
                    player = LLMPlayer(provider="gemini")
                    info = player.get_last_decision_info()
                    
                    assert info["prompt"] is None
                    assert info["response"] is None
                    assert info["model_name"] is not None
                    assert info["prompts_version"] is not None


class TestDbModels:
    """Tests for database models."""
    
    def test_ai_decision_log_model_exists(self):
        """Test that AIDecisionLogModel is properly defined."""
        from api.db_models import AIDecisionLogModel
        
        assert AIDecisionLogModel.__tablename__ == "ai_decision_logs"
    
    def test_game_playback_model_exists(self):
        """Test that GamePlaybackModel is properly defined."""
        from api.db_models import GamePlaybackModel
        
        assert GamePlaybackModel.__tablename__ == "game_playback"
    
    def test_player_stats_model_exists(self):
        """Test that PlayerStatsModel is properly defined."""
        from api.db_models import PlayerStatsModel
        
        assert PlayerStatsModel.__tablename__ == "player_stats"
    
    def test_player_stats_win_rate_calculation(self):
        """Test win rate calculation on PlayerStatsModel."""
        from api.db_models import PlayerStatsModel
        
        # Create instance without database
        stats = PlayerStatsModel(
            player_id="test-player",
            display_name="Test",
            games_played=10,
            games_won=7,
            total_tussles=0,
            tussles_won=0,
            card_stats={},
        )
        
        assert stats.win_rate == 70.0
    
    def test_player_stats_win_rate_zero_games(self):
        """Test win rate is 0 when no games played."""
        from api.db_models import PlayerStatsModel
        
        stats = PlayerStatsModel(
            player_id="test-player",
            display_name="Test",
            games_played=0,
            games_won=0,
            total_tussles=0,
            tussles_won=0,
            card_stats={},
        )
        
        assert stats.win_rate == 0.0


class TestMigration:
    """Tests for the Alembic migration."""
    
    def test_migration_file_exists(self):
        """Test that migration file exists."""
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "004_create_stats_tables.py"
        assert migration_path.exists(), f"Migration file not found at {migration_path}"
    
    def test_migration_imports(self):
        """Test that migration can be imported."""
        # Import the migration module
        import importlib.util
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "004_create_stats_tables.py"
        
        spec = importlib.util.spec_from_file_location("migration_004", str(migration_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check revision info
        assert module.revision == "004"
        assert module.down_revision == "003"
        
        # Check upgrade and downgrade functions exist
        assert hasattr(module, "upgrade")
        assert hasattr(module, "downgrade")
        assert callable(module.upgrade)
        assert callable(module.downgrade)


class TestStatsServiceSingleton:
    """Tests for stats service singleton."""
    
    def test_get_stats_service_returns_same_instance(self):
        """Test that get_stats_service returns singleton."""
        from api.stats_service import get_stats_service, _stats_service
        
        # Reset singleton for test
        import api.stats_service
        api.stats_service._stats_service = None
        
        service1 = get_stats_service()
        service2 = get_stats_service()
        
        assert service1 is service2
