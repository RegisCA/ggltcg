# Database Schema Design for GGLTCG

**Version:** 1.0
**Date:** November 21, 2025
**Purpose:** PostgreSQL persistence for multiplayer game sessions

---

## Overview

This document defines the PostgreSQL schema for persisting GGLTCG game sessions.
The design follows a phased approach:

- **Phase 1** (This Implementation): JSONB-based storage with minimal schema
  changes
- **Phase 2** (Future): Normalized tables for advanced queries and analytics
- **Phase 3** (Future): Event sourcing for replay and time-travel debugging

---

## Phase 1: JSONB Storage Schema

### Design Philosophy

**Goal:** Add persistence with minimal code changes to existing game engine

**Approach:**

- Store complete GameEngine state as JSONB
- Add minimal metadata columns for queries
- Enable fast read/write operations
- Support multiplayer session management

**Benefits:**

- ✅ Fast to implement (minimal refactoring)
- ✅ Flexible schema (easy to evolve)
- ✅ Preserves existing game logic
- ✅ Supports server restart recovery

**Trade-offs:**

- ❌ Limited query capabilities (can't easily query game details)
- ❌ Requires full state deserialization for any read
- ❌ No historical tracking of individual actions

---

## Table Definitions

### Table: `games`

Primary table for storing active game sessions.

```sql
CREATE TABLE games (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Game metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Player information (for queries and matchmaking)
    player1_id VARCHAR(255) NOT NULL,
    player1_name VARCHAR(255) NOT NULL,
    player2_id VARCHAR(255) NOT NULL,
    player2_name VARCHAR(255) NOT NULL,

    -- Game status
    status VARCHAR(50) NOT NULL DEFAULT 'active',
        -- 'active': Game in progress
        -- 'completed': Game finished
        -- 'abandoned': Player disconnected/timeout

    winner_id VARCHAR(255),  -- NULL if game not finished

    -- Current turn info (denormalized for queries)
    turn_number INTEGER NOT NULL DEFAULT 1,
    active_player_id VARCHAR(255) NOT NULL,
    phase VARCHAR(50) NOT NULL DEFAULT 'Start',

    -- Full game state (JSONB)
    game_state JSONB NOT NULL,
        -- Serialized GameEngine state
        -- Contains: players, cards, zones, effects, etc.
        -- Structure: {
        --   "game_id": "...",
        --   "players": {...},
        --   "active_player_id": "...",
        --   "turn_number": 1,
        --   "phase": "Main",
        --   "first_player_id": "...",
        --   "winner_id": null,
        --   "game_log": [...],
        --   "play_by_play": [...]
        -- }

    -- Indexes
    CONSTRAINT games_status_check CHECK (status IN ('active', 'completed', 'abandoned'))
);

-- Indexes for common queries
CREATE INDEX idx_games_player1 ON games(player1_id);
CREATE INDEX idx_games_player2 ON games(player2_id);
CREATE INDEX idx_games_status ON games(status);
CREATE INDEX idx_games_updated_at ON games(updated_at);
CREATE INDEX idx_games_active_player ON games(active_player_id) WHERE status = 'active';

-- Combined index for finding player's active games
CREATE INDEX idx_games_player_active ON games(player1_id, player2_id, status)
    WHERE status = 'active';

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_games_updated_at
    BEFORE UPDATE ON games
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```text
### Table: `game_actions` (Optional - For Analytics)

Stores individual game actions for future analytics and debugging.

```sql
CREATE TABLE game_actions (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Foreign key to game
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,

    -- Action metadata
    turn_number INTEGER NOT NULL,
    player_id VARCHAR(255) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
        -- e.g., 'play_card', 'tussle', 'end_turn',
        -- 'activate_ability'

    -- Action details (JSONB for flexibility)
    action_data JSONB NOT NULL,
        -- Structure depends on action_type:
        -- play_card: {"card_id": "...", "card_name": "...",
        --  "target_ids": [...], "cost": 3}
        -- tussle: {"attacker_id": "...", "defender_id": "...", "cost": 1}
        -- end_turn: {}

    -- Result of action
    result_description TEXT,  -- Play-by-play text

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_game_actions_game_id ON game_actions(game_id);
CREATE INDEX idx_game_actions_player ON game_actions(player_id);
CREATE INDEX idx_game_actions_type ON game_actions(action_type);
CREATE INDEX idx_game_actions_turn ON game_actions(game_id, turn_number);
```text
### Table: `game_stats` (Optional - For Leaderboards)

Aggregated statistics for completed games.

```sql
CREATE TABLE game_stats (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Foreign key to game
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,

    -- Game outcome
    winner_id VARCHAR(255) NOT NULL,
    loser_id VARCHAR(255) NOT NULL,

    -- Game metrics
    total_turns INTEGER NOT NULL,
    duration_seconds INTEGER,  -- Calculated from created_at to updated_at

    -- Winner stats
    winner_cards_played INTEGER,
    winner_tussles_initiated INTEGER,
    winner_direct_attacks INTEGER,

    -- Loser stats
    loser_cards_played INTEGER,
    loser_tussles_initiated INTEGER,
    loser_direct_attacks INTEGER,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Constraint: one stats record per game
    CONSTRAINT game_stats_unique_game UNIQUE (game_id)
);

-- Indexes for leaderboards
CREATE INDEX idx_game_stats_winner ON game_stats(winner_id);
CREATE INDEX idx_game_stats_loser ON game_stats(loser_id);
CREATE INDEX idx_game_stats_created_at ON game_stats(created_at DESC);
```text
---

## Implementation Strategy

### Phase 1A: Core Persistence (This PR)

**Scope:**

- Implement `games` table only
- Add SQLAlchemy ORM models
- Create database service layer
- Refactor `game_service.py` to use database
- Support game create, read, update operations

**Files to Create:**

- `backend/src/api/database.py` - Database connection and session management
- `backend/src/api/db_models.py` - SQLAlchemy ORM models
- `backend/alembic/versions/001_create_games_table.py` - Migration script
- `backend/alembic.ini` - Alembic configuration
- `backend/alembic/env.py` - Alembic environment

**Files to Modify:**

- `backend/src/api/game_service.py` - Add database persistence
- `backend/requirements.txt` - Add SQLAlchemy, Alembic, psycopg2
- `backend/render.yaml` - Add database config and migration command

### Phase 1B: Action Logging (Future PR)

**Scope:**

- Implement `game_actions` table
- Log every action to database
- Enable action replay functionality

### Phase 1C: Statistics (Future PR)

**Scope:**

- Implement `game_stats` table
- Calculate stats on game completion
- Build leaderboard API endpoints

---

## Data Flow

### Creating a Game

```text
1. API receives POST /games request
2. GameService.create_game() creates GameEngine instance
3. GameEngine.state serialized to JSONB
4. INSERT INTO games (player1_id, player2_id, game_state, ...)
5. Return game_id to client
```text
### Loading a Game

```text
1. API receives GET /games/{game_id} request
2. SELECT game_state FROM games WHERE id = game_id
3. Deserialize JSONB to GameState dataclass
4. Reconstruct GameEngine instance
5. Return to client
```text
### Updating a Game

```text
1. API receives POST /games/{game_id}/play-card request
2. Load game from database
3. Execute action via GameEngine
4. Serialize updated state to JSONB
5. UPDATE games SET game_state = ..., updated_at = NOW() WHERE id = game_id
6. Return updated state to client
```text
---

## Serialization Strategy

### GameState Serialization

The `GameState` dataclass will be serialized to JSON using a custom encoder:

```python
def serialize_game_state(game_state: GameState) -> dict:
    """Convert GameState to JSON-serializable dict."""
    return {
        "game_id": game_state.game_id,
        "players": {
            player_id: serialize_player(player)
            for player_id, player in game_state.players.items()
        },
        "active_player_id": game_state.active_player_id,
        "turn_number": game_state.turn_number,
        "phase": game_state.phase.value,
        "first_player_id": game_state.first_player_id,
        "winner_id": game_state.winner_id,
        "game_log": game_state.game_log,
        "play_by_play": game_state.play_by_play,
    }

def deserialize_game_state(data: dict, card_loader: CardLoader) -> GameState:
    """Convert JSON dict to GameState."""
    return GameState(
        game_id=data["game_id"],
        players={
            player_id: deserialize_player(player_data, card_loader)
            for player_id, player_data in data["players"].items()
        },
        active_player_id=data["active_player_id"],
        turn_number=data["turn_number"],
        phase=Phase(data["phase"]),
        first_player_id=data["first_player_id"],
        winner_id=data.get("winner_id"),
        game_log=data.get("game_log", []),
        play_by_play=data.get("play_by_play", []),
    )
```text
### Card Serialization

Cards will be serialized with their full state including modifications:

```python
def serialize_card(card: Card) -> dict:
    """Convert Card to JSON-serializable dict."""
    return {
        "id": card.id,
        "name": card.name,
        "card_type": card.card_type.value,
        "cost": card.cost,
        "effect_text": card.effect_text,
        "speed": card.speed,
        "strength": card.strength,
        "stamina": card.stamina,
        "primary_color": card.primary_color,
        "accent_color": card.accent_color,
        "owner": card.owner,
        "controller": card.controller,
        "zone": card.zone.value,
        "modifications": card.modifications,
    }
```text
---

## Security Considerations

### SQL Injection Prevention

✅ **Using SQLAlchemy ORM** - Parameterized queries prevent SQL injection

### Authentication & Authorization (Future)

For multiplayer, we'll need to add:

- Player authentication (OAuth or JWT tokens)
- Authorization checks (can player access this game?)
- Rate limiting (prevent spam)

**Placeholder for Phase 2:**

```sql
-- Add after implementing auth
ALTER TABLE games ADD COLUMN player1_auth_id VARCHAR(255);
ALTER TABLE games ADD COLUMN player2_auth_id VARCHAR(255);
```text
### Data Privacy

- Player IDs should be non-guessable (UUIDs)
- Game states should only be visible to participating players
- Implement proper CORS and HTTPS in production

---

## Performance Considerations

### JSONB Indexing (Future Optimization)

If we need to query game state contents:

```sql
-- Example: Find games where a specific card is in play
CREATE INDEX idx_games_state_cards ON games
    USING GIN ((game_state->'players'));

-- Example: Find games by winner
CREATE INDEX idx_games_state_winner ON games
    ((game_state->>'winner_id'))
    WHERE (game_state->>'winner_id') IS NOT NULL;
```text
### Connection Pooling

Use SQLAlchemy's connection pooling with appropriate settings:

```python
engine = create_engine(
    database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
)
```text
### Caching Strategy (Future)

For high-traffic games:

- Add Redis cache layer
- Cache active game states in memory
- Invalidate on updates
- Fallback to database on cache miss

---

## Migration Path

### Step 1: Deploy with Both Systems

- Keep in-memory dict alongside database
- Write to both
- Read from database with fallback to memory
- Validate consistency

### Step 2: Database-Only Mode

- Remove in-memory storage
- All reads/writes from database
- Monitor performance

### Step 3: Optimize

- Add indexes based on query patterns
- Implement caching if needed
- Consider read replicas for scaling

---

## Monitoring & Maintenance

### Metrics to Track

- Game creation rate
- Average game duration
- Database query latency
- Connection pool utilization
- Failed deserialization errors

### Cleanup Strategy

**Abandoned Games:**

```sql
-- Delete games abandoned for >24 hours
DELETE FROM games
WHERE status = 'active'
  AND updated_at < NOW() - INTERVAL '24 hours';
```text
**Completed Games:**

```sql
-- Archive completed games after 30 days
-- Move to archive table or export to S3
```text
---

## Testing Strategy

### Unit Tests

- Test serialization/deserialization of all game objects
- Test database CRUD operations
- Test transaction rollback on errors

### Integration Tests

- Create game → load game → verify state matches
- Execute action → save → load → verify state updated
- Concurrent updates (test transaction isolation)

### Performance Tests

- Measure serialization overhead
- Benchmark database write latency
- Test with large game states (6 cards per player)

---

## Rollback Plan

If database causes issues in production:

1. **Immediate:** Revert to in-memory storage via feature flag
2. **Short-term:** Fix database issues, re-deploy
3. **Long-term:** Improve monitoring and alerting

---

## Future Enhancements (Phase 2+)

### Normalized Schema

Replace JSONB with properly normalized tables:

```sql
CREATE TABLE players (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    name VARCHAR(255),
    cc INTEGER
);

CREATE TABLE cards_in_game (
    id UUID PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    card_template_id INTEGER,
    owner_id UUID REFERENCES players(id),
    controller_id UUID REFERENCES players(id),
    zone VARCHAR(50),
    modifications JSONB
);
```text
**Benefits:**

- Advanced queries (e.g., "Which cards win most often?")
- Better indexing and performance
- Referential integrity

**Costs:**

- More complex schema
- More code to maintain
- Harder to evolve game rules

### Event Sourcing

Store game events instead of state:

```sql
CREATE TABLE game_events (
    id BIGSERIAL PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    event_type VARCHAR(50),
    event_data JSONB,
    created_at TIMESTAMP
);
```text
**Benefits:**

- Complete audit trail
- Replay games from any point
- Debugging historical issues

**Costs:**

- Higher storage requirements
- More complex state reconstruction
- Potential performance impact

---

## Conclusion

This schema design provides a solid foundation for PostgreSQL persistence while
minimizing changes to the existing codebase. The JSONB approach offers
flexibility for rapid iteration while maintaining data integrity and enabling
future enhancements.

**Next Steps:**

1. ✅ Review and approve schema design
2. ✅ Set up Render PostgreSQL instance
3. ✅ Implement SQLAlchemy models
4. ✅ Create Alembic migrations
5. ✅ Refactor game_service.py
6. ✅ Deploy and test

---

## Appendix: Player ID Strategy

**Updated:** December 2, 2025

### Player Identification

Players are identified by their **Google ID** (from OAuth authentication), not
by randomly generated UUIDs or session-based IDs.

- **Authenticated User** — ID: Google ID (numeric); Example: `10966245...`
- **AI Opponent** — ID: Fixed string; Example: `ai-gemiknight`
- **Guest (future)** — ID: `guest-{uuid}`; Example: `guest-a1b2...`

**Why Google ID?**

- Consistent across sessions and devices
- Enables accurate stat tracking per player
- No duplicate records when same player plays multiple games

**Implementation:**

- Frontend passes `user.google_id` from auth context when starting games
- Backend stores this in `player1_id`/`player2_id` columns
- Stats are aggregated by this ID in `player_stats` table

### Table: `player_stats` (Implemented)

Tracks cumulative statistics per player across all games.

```sql
CREATE TABLE player_stats (
    player_id VARCHAR(255) PRIMARY KEY,  -- Google ID or 'ai-gemiknight'
    display_name VARCHAR(255) NOT NULL,
    games_played INTEGER NOT NULL DEFAULT 0,
    games_won INTEGER NOT NULL DEFAULT 0,
    total_tussles INTEGER NOT NULL DEFAULT 0,
    tussles_won INTEGER NOT NULL DEFAULT 0,
    card_stats JSONB DEFAULT '{}',  -- Per-card statistics
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```text
**`card_stats` JSONB Structure:**

```json
{
  "Ka": {
    "games_played": 15,
    "games_won": 12,
    "tussles_initiated": 8,
    "tussles_won": 6
  },
  "Knight": {
    "games_played": 10,
    "games_won": 8,
    "tussles_initiated": 5,
    "tussles_won": 4
  }
}
```text
### Migration Notes

**Migration 005** (`005_merge_legacy_player_stats.py`) consolidated legacy
records from before the Google ID fix:

- Merged `human`, `player1` → Sully's Google ID
- Merged `human-*`, `player2` → Régis's Google ID
- Merged `ai`, `ai-*` → `ai-gemiknight`

### Alembic Migrations at Startup

Since Render free tier doesn't support `preDeployCommand`, migrations run
automatically at app startup via FastAPI's lifespan handler in `app.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()  # Runs 'alembic upgrade head'
    yield
```text
This ensures database schema is always up-to-date when the app starts.
