#!/usr/bin/env python3
"""
One-off script to backfill historical completed games into PostHog as
game_analyzed events.

Joins games (real player IDs, winner, timestamps) with game_stats (turns,
duration, action counts) — the two tables that survive the cleanup task —
and emits one game_analyzed event per human player, timestamped at game
completion. The event vocabulary matches the live push in
api/analytics.py + GameService._push_game_analyzed, with two differences:
`went_first` and `deck` are omitted (only stored in game_playback, which
has 24-hour retention) and `backfilled: true` is added so backfilled
events can be filtered in insights.

Idempotent: each event gets a deterministic UUID derived from
(game_id, player_id), so re-running the script cannot create duplicates.

After the events, one $set per human player updates the person profile
with current games_played / games_won / win_rate from player_stats.

Run from backend directory (reads DATABASE_URL and POSTHOG_API_KEY from env):
    python scripts/backfill_posthog_events.py --dry-run   # print, send nothing
    python scripts/backfill_posthog_events.py             # send
"""

import sys
import uuid
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import argparse
import os

from api.database import SessionLocal
from api.db_models import GameModel, GameStatsModel, PlayerStatsModel
from api.analytics import is_ai_player

# Namespace for deterministic event UUIDs (random once, fixed forever —
# changing it would break idempotency with previously backfilled events)
BACKFILL_UUID_NAMESPACE = uuid.UUID("6f9619ff-8b86-4d01-b42d-00cf4fc964ff")


def build_events(db) -> list[dict]:
    """Build the game_analyzed payloads for all completed games."""
    rows = (
        db.query(GameModel, GameStatsModel)
        .join(GameStatsModel, GameStatsModel.game_id == GameModel.id)
        .filter(GameModel.status == "completed", GameModel.winner_id.isnot(None))
        .order_by(GameModel.updated_at)
        .all()
    )
    print(f"Found {len(rows)} completed games with stats")

    events = []
    for game, stats in rows:
        players = {
            game.player1_id: game.player1_name,
            game.player2_id: game.player2_name,
        }
        for pid in players:
            if is_ai_player(pid):
                continue
            opponent_id = next(o for o in players if o != pid)
            is_winner = pid == game.winner_id
            side = "winner" if is_winner else "loser"

            events.append({
                "uuid": uuid.uuid5(BACKFILL_UUID_NAMESPACE, f"{game.id}:{pid}"),
                "distinct_id": pid,
                "timestamp": game.updated_at,
                "properties": {
                    "game_id": str(game.id),
                    "opponent_type": "ai" if is_ai_player(opponent_id) else "human",
                    "total_turns": stats.total_turns,
                    "duration_seconds": stats.duration_seconds or 0,
                    "is_winner": is_winner,
                    "cards_played": getattr(stats, f"{side}_cards_played"),
                    "tussles_initiated": getattr(stats, f"{side}_tussles_initiated"),
                    "direct_attacks": getattr(stats, f"{side}_direct_attacks"),
                    "backfilled": True,
                },
            })
    return events


def build_person_updates(db, player_ids: set[str]) -> list[dict]:
    """Current rollups from player_stats for every player we emitted for."""
    updates = []
    for stats in (
        db.query(PlayerStatsModel).filter(PlayerStatsModel.player_id.in_(player_ids)).all()
    ):
        updates.append({
            "distinct_id": stats.player_id,
            "set": {
                "games_played": stats.games_played,
                "games_won": stats.games_won,
                "win_rate": stats.win_rate,
            },
        })
    return updates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print payloads, send nothing")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        events = build_events(db)
        person_updates = build_person_updates(db, {e["distinct_id"] for e in events})
    finally:
        db.close()

    print(f"Prepared {len(events)} game_analyzed events for "
          f"{len({e['distinct_id'] for e in events})} players")

    if args.dry_run:
        for e in events:
            print(f"  {e['timestamp']} {e['distinct_id'][:24]:<24} {e['properties']}")
        for u in person_updates:
            print(f"  $set {u['distinct_id'][:24]:<24} {u['set']}")
        print("Dry run — nothing sent.")
        return

    api_key = os.getenv("POSTHOG_API_KEY")
    if not api_key:
        print("ERROR: POSTHOG_API_KEY not set")
        sys.exit(1)

    from posthog import Posthog

    client = Posthog(
        project_api_key=api_key,
        host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"),
        historical_migration=True,  # batch endpoint; avoids quota alarms on spikes
    )

    for e in events:
        client.capture(
            "game_analyzed",
            distinct_id=e["distinct_id"],
            properties=e["properties"],
            timestamp=e["timestamp"],
            uuid=e["uuid"],
        )
    for u in person_updates:
        client.capture(
            "$set",
            distinct_id=u["distinct_id"],
            properties={"$set": u["set"]},
        )

    client.flush()
    print(f"Sent {len(events)} events and {len(person_updates)} person updates.")


if __name__ == "__main__":
    main()
