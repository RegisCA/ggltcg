"""
PostHog server-side analytics.

Pushes a `game_analyzed` enrichment event per human player when a game
completes. The event vocabulary is shared with the frontend instrumentation
(frontend/src/analytics/posthog.ts): distinct_id is the player's Google ID,
so server-side events join the same PostHog person as the client events.

Disabled unless POSTHOG_API_KEY is set (local dev, CI, and tests emit
nothing). Failures are logged and swallowed — analytics must never break
game persistence.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_client = None
_client_initialized = False


def _get_client():
    """Lazily build the PostHog client, or None when analytics is disabled."""
    global _client, _client_initialized
    if _client_initialized:
        return _client
    _client_initialized = True

    api_key = os.getenv("POSTHOG_API_KEY")
    if not api_key:
        logger.info("POSTHOG_API_KEY not set; PostHog analytics disabled")
        return None

    try:
        from posthog import Posthog

        _client = Posthog(
            project_api_key=api_key,
            host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"),
        )
        logger.info("PostHog analytics enabled")
    except Exception as e:
        logger.error(f"Failed to initialize PostHog client: {e}")
        _client = None
    return _client


def is_ai_player(player_id: str) -> bool:
    """AI opponents use generated IDs like 'ai-gemiknight' / 'ai-player-123'."""
    return player_id.startswith("ai-")


def capture_game_analyzed(
    distinct_id: str,
    properties: dict,
    person_properties: Optional[dict] = None,
) -> None:
    """
    Send one game_analyzed event for a human player.

    person_properties are attached via $set so PostHog updates the person's
    profile (games_played, win_rate, ...) for cohorting.
    """
    client = _get_client()
    if client is None:
        return
    try:
        props = dict(properties)
        if person_properties:
            props["$set"] = person_properties
        client.capture("game_analyzed", distinct_id=distinct_id, properties=props)
    except Exception as e:
        logger.error(f"Failed to capture game_analyzed for {distinct_id}: {e}")
