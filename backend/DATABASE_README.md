# PostgreSQL Database Integration - Testing & Deployment Guide

## Overview

The GGLTCG backend now uses PostgreSQL for persistent game storage, replacing the in-memory dict. This enables:
- Game sessions survive server restarts
- Foundation for online multiplayer
- Ability to query game statistics
- Audit trail of all game actions

## Local Development Setup

### Prerequisites

- PostgreSQL installed locally (optional for local dev)
- Access to Render PostgreSQL database via `DATABASE_URL`
- Python virtual environment activated

### Option 1: Use Render Database for Development

This is the simplest approach - use the same database as production:

```bash
# Set DATABASE_URL environment variable
export DATABASE_URL="postgres://your-render-database-url-here"

# Run migrations
cd backend
alembic upgrade head

# Start the server
cd src
python run_server.py
```

### Option 2: Local PostgreSQL Database

If you want to run a local PostgreSQL database:

```bash
# Install PostgreSQL (macOS)
brew install postgresql@14
brew services start postgresql@14

# Create database
createdb ggltcg_dev

# Set DATABASE_URL
export DATABASE_URL="postgresql://localhost/ggltcg_dev"

# Run migrations
cd backend
alembic upgrade head

# Start the server
cd src
python run_server.py
```

## Database Migrations

### Running Migrations

```bash
cd backend

# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

### Creating New Migrations

When you modify database models:

```bash
cd backend

# Generate migration automatically
alembic revision --autogenerate -m "description_of_changes"

# Or create empty migration
alembic revision -m "description_of_changes"

# Review the generated migration in alembic/versions/
# Then apply it
alembic upgrade head
```

## Testing the Integration

### Manual Testing

1. **Start the backend with DATABASE_URL set**

```bash
cd backend
export DATABASE_URL="your-database-url"
cd src
python run_server.py
```

2. **Create a new game** (via frontend or API)

```bash
# Using curl
curl -X POST http://localhost:8000/games \
  -H "Content-Type: application/json" \
  -d '{
    "player1": {"player_id": "alice", "name": "Alice", "deck": ["Ka", "Beary", "Wizard", "Wake", "Sun", "Twist"]},
    "player2": {"player_id": "bob", "name": "Bob", "deck": ["Ballaber", "Snuggles", "Demideca", "Wake", "Rush", "Copy"]}
  }'
```

3. **Verify game was saved to database**

```bash
# Connect to database
psql $DATABASE_URL

# Query games table
SELECT id, player1_name, player2_name, status, turn_number FROM games;

# View full game state
SELECT game_state FROM games WHERE id = 'your-game-id';
```

4. **Stop and restart the server**

```bash
# Stop server (Ctrl+C)
# Restart server
python run_server.py
```

5. **Load the game** (should still exist)

```bash
curl http://localhost:8000/games/your-game-id
```

### Automated Testing

Run the existing test suite:

```bash
cd backend
pytest tests/
```

The tests will use in-memory mode by default (database disabled for unit tests).

## Database Schema

### Games Table

Primary table storing complete game state:

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| player1_id | VARCHAR(255) | Player 1 identifier |
| player1_name | VARCHAR(255) | Player 1 display name |
| player2_id | VARCHAR(255) | Player 2 identifier |
| player2_name | VARCHAR(255) | Player 2 display name |
| status | VARCHAR(50) | 'active', 'completed', or 'abandoned' |
| winner_id | VARCHAR(255) | Winner player ID (NULL if ongoing) |
| turn_number | INTEGER | Current turn number |
| active_player_id | VARCHAR(255) | Current player's turn |
| phase | VARCHAR(50) | Current phase ('Start', 'Main', 'End') |
| game_state | JSONB | Complete serialized game state |
| created_at | TIMESTAMP | Game creation time |
| updated_at | TIMESTAMP | Last update time |

**Indexes:**
- player1_id, player2_id (for finding user's games)
- status (for filtering active games)
- updated_at (for sorting by recency)
- Combined player + status (for efficient queries)

### Game Actions Table (Future)

Stores individual actions for analytics:

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| game_id | UUID | Foreign key to games |
| turn_number | INTEGER | Turn when action occurred |
| player_id | VARCHAR(255) | Player who took action |
| action_type | VARCHAR(50) | Type of action |
| action_data | JSONB | Action details |
| result_description | TEXT | Play-by-play description |
| created_at | TIMESTAMP | Action timestamp |

### Game Stats Table (Future)

Aggregated statistics for completed games:

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| game_id | UUID | Foreign key to games (unique) |
| winner_id | VARCHAR(255) | Winner player ID |
| loser_id | VARCHAR(255) | Loser player ID |
| total_turns | INTEGER | Number of turns |
| duration_seconds | INTEGER | Game duration |
| ...stats... | INTEGER | Various game statistics |
| created_at | TIMESTAMP | Stat creation time |

## Performance Considerations

### Caching Strategy

The `GameService` implements a two-tier storage:

1. **In-memory cache**: Active games are cached in memory for fast access
2. **Database storage**: All games persisted to PostgreSQL

**Read flow:**
- Check cache → Return if found
- Load from database → Cache → Return

**Write flow:**
- Update cache
- Save to database

This provides excellent performance while ensuring persistence.

### Connection Pooling

SQLAlchemy uses connection pooling:
- Pool size: 5 connections
- Max overflow: 10 additional connections
- Pool pre-ping: Verifies connections before use

### Query Optimization

- Indexes on frequently queried columns
- JSONB for flexible schema
- Denormalized columns for common queries (turn_number, status, etc.)

## Deployment

### Render Deployment

The deployment process is automated via `render.yaml`:

1. **Build**: `pip install -r requirements.txt`
2. **Pre-deploy**: `alembic upgrade head` (runs migrations)
3. **Start**: `uvicorn api.app:app`

### Environment Variables

Required in Render environment:

- `DATABASE_URL`: PostgreSQL connection string (set automatically by Render)
- `GOOGLE_API_KEY`: Google Gemini API key
- `GEMINI_MODEL`: Primary model name
- `GEMINI_FALLBACK_MODEL`: Fallback model name

### Monitoring

After deployment, verify:

```bash
# Check migration status
DATABASE_URL="your-render-url" alembic current

# Check games table exists
psql your-render-url -c "\dt"

# View active games
psql your-render-url -c "SELECT count(*) FROM games WHERE status='active';"
```

## Troubleshooting

### Migration Errors

**Error: "DATABASE_URL environment variable is required"**
```bash
# Make sure DATABASE_URL is set
echo $DATABASE_URL
export DATABASE_URL="your-database-url"
```

**Error: "relation 'games' already exists"**
```bash
# Check current version
alembic current

# If needed, stamp the database with the current version
alembic stamp head
```

### Connection Errors

**Error: "connection to server ... failed"**
```bash
# Verify DATABASE_URL is correct
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"

# Check if database exists
psql $DATABASE_URL -c "\l"
```

### Data Issues

**Game not persisting**
```bash
# Check logs for errors
# Verify use_database=True in GameService
# Check database write permissions
```

**Deserialization errors**
```bash
# Check game_state JSONB structure
psql $DATABASE_URL -c "SELECT game_state FROM games LIMIT 1;"

# Verify serialization/deserialization functions match
```

## Rollback Plan

If database causes issues:

1. **Immediate**: Set env var `USE_DATABASE=false` to disable persistence
2. **Fix**: Address database issues, test locally
3. **Redeploy**: Enable database again

## Next Steps

### Phase 1B: Action Logging

- Enable `game_actions` table
- Log every action to database
- Build action replay system

### Phase 1C: Statistics

- Enable `game_stats` table
- Calculate stats on game completion
- Build leaderboard endpoints

### Phase 2: Multiplayer

- Add WebSocket support
- Implement player matching
- Add authentication/authorization

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Render PostgreSQL](https://render.com/docs/databases)
