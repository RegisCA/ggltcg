"""
Tests for the PostHog analytics module (game_analyzed enrichment push).

Analytics must be a no-op without POSTHOG_API_KEY and must never raise.
"""

from unittest.mock import MagicMock, patch

# Add backend/src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _reset_client():
    """Reset the module-level client cache between tests."""
    import api.analytics as analytics
    analytics._client = None
    analytics._client_initialized = False


class TestClientGating:
    """Client construction is gated on POSTHOG_API_KEY."""

    def test_disabled_without_api_key(self):
        from api import analytics
        _reset_client()

        with patch.dict('os.environ', {}, clear=False):
            import os
            os.environ.pop('POSTHOG_API_KEY', None)
            # No client, and capture is a silent no-op
            assert analytics._get_client() is None
            analytics.capture_game_analyzed("player-1", {"game_id": "g1"})

    def test_enabled_with_api_key(self):
        from api import analytics
        _reset_client()

        with patch.dict('os.environ', {'POSTHOG_API_KEY': 'phc_test'}):
            with patch('posthog.Posthog') as mock_posthog:
                client = analytics._get_client()
                assert client is not None
                mock_posthog.assert_called_once()
                assert mock_posthog.call_args.kwargs['host'] == 'https://us.i.posthog.com'

    def test_client_cached_after_first_call(self):
        from api import analytics
        _reset_client()

        with patch.dict('os.environ', {'POSTHOG_API_KEY': 'phc_test'}):
            with patch('posthog.Posthog') as mock_posthog:
                first = analytics._get_client()
                second = analytics._get_client()
                assert first is second
                mock_posthog.assert_called_once()


class TestCaptureGameAnalyzed:
    """Event payload shape and error swallowing."""

    def test_capture_sends_event_with_person_properties(self):
        from api import analytics
        _reset_client()

        mock_client = MagicMock()
        analytics._client = mock_client
        analytics._client_initialized = True

        analytics.capture_game_analyzed(
            "google-id-1",
            {"game_id": "g1", "is_winner": True},
            person_properties={"games_played": 5, "win_rate": 0.6},
        )

        mock_client.capture.assert_called_once()
        args, kwargs = mock_client.capture.call_args
        assert args[0] == "game_analyzed"
        assert kwargs["distinct_id"] == "google-id-1"
        assert kwargs["properties"]["game_id"] == "g1"
        assert kwargs["properties"]["$set"] == {"games_played": 5, "win_rate": 0.6}

    def test_capture_without_person_properties_has_no_set(self):
        from api import analytics
        _reset_client()

        mock_client = MagicMock()
        analytics._client = mock_client
        analytics._client_initialized = True

        analytics.capture_game_analyzed("google-id-1", {"game_id": "g1"})

        _, kwargs = mock_client.capture.call_args
        assert "$set" not in kwargs["properties"]

    def test_capture_swallows_client_errors(self):
        from api import analytics
        _reset_client()

        mock_client = MagicMock()
        mock_client.capture.side_effect = RuntimeError("posthog down")
        analytics._client = mock_client
        analytics._client_initialized = True

        # Must not raise
        analytics.capture_game_analyzed("google-id-1", {"game_id": "g1"})


class TestIsAiPlayer:
    def test_ai_ids(self):
        from api.analytics import is_ai_player
        assert is_ai_player("ai-gemiknight")
        assert is_ai_player("ai-player-123")

    def test_human_ids(self):
        from api.analytics import is_ai_player
        assert not is_ai_player("108234567890")
        assert not is_ai_player("guest-abc-123")
