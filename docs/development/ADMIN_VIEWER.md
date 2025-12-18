# Admin Data Viewer

Simple data viewer for GGLTCG database monitoring and debugging.

## Features

- **Summary Dashboard**: Overview of database stats (users, games, AI logs,
  playbacks)

- **AI Logs Viewer**: Review Gemini prompts and responses
- **Games List**: Browse active and completed games
- **Game Playbacks**: View completed game summaries with play-by-play

## Access

### Local Development

1. Start the backend server:

```bash
cd backend
source ../.venv/bin/activate
python run_server.py

```

1. Start the frontend dev server:

```bash
cd frontend
npm run dev

```

1. Open the admin viewer:

```text
http://localhost:5173/admin.html

```

### Production

The admin viewer is deployed alongside the main application:

```text
https://your-frontend-url.vercel.app/admin.html

```

## API Endpoints

All admin endpoints are under `/admin`:

### Summary Stats

```bash
GET /admin/stats/summary

```

Returns database summary with counts and recent activity.

### AI Logs

```bash
# List recent AI logs
GET /admin/ai-logs?limit=50&game_id={optional}

# Get specific log
GET /admin/ai-logs/{log_id}

```

### Games

```bash
# List recent games
GET /admin/games?limit=20&status={optional}

# Get specific game with full state
GET /admin/games/{game_id}

```

### Game Playbacks

```bash
# List completed games
GET /admin/game-playbacks?limit=20&winner_id={optional}

# Get full playback with play-by-play
GET /admin/game-playbacks/{game_id}

```

### Players

```bash
# Get player stats (leaderboard order)
GET /admin/players?limit=20

```

### Users

```bash
# Get registered users
GET /admin/users?limit=20

```

## Usage Examples

### View Recent AI Decisions

1. Click "AI Logs" tab
1. Click "View Full" on any log to see the complete prompt and response
1. Use this to debug AI behavior or understand decision-making

### Debug a Specific Game

1. Click "Games" tab
1. Find the game by player names or game code
1. Copy the game ID
1. Use the API to get full game state:

    ```bash
    curl http://localhost:8000/admin/games/{game_id}

    ```

### Review Completed Games

1. Click "Playbacks" tab
1. Browse completed games
1. Click "View Full Playback JSON" to see complete play-by-play

## Development

The admin viewer consists of:

- **Backend**: `/backend/src/api/routes_admin.py` - FastAPI routes
- **Frontend**: `/frontend/src/components/AdminDataViewer.tsx` - React component
- **Entry Point**: `/frontend/admin.html` - Standalone HTML page

### Adding New Views

1. Add API endpoint in `routes_admin.py`
1. Add React component or tab in `AdminDataViewer.tsx`
1. Test locally before deploying

## Security Considerations

**IMPORTANT**: The admin viewer currently has NO authentication.

### Current State

- ⚠️ Anyone with the URL can access the admin panel
- Only suitable for internal/development use

### Recommended Improvements

1. Add authentication middleware to `/admin/*` routes
1. Implement role-based access control (admin users only)
1. Add API key or token authentication
1. Restrict by IP address in production

Example authentication check:

```python
from fastapi import Header, HTTPException

async def verify_admin_token(x_admin_token: str = Header(...)):
    if x_admin_token != os.getenv("ADMIN_TOKEN"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

```

## Data Retention

Different data types have different retention policies:

- **Users**: Permanent
- **Games**: Permanent (with status updates)
- **Player Stats**: Permanent
- **Game Playbacks**: 24 hours (auto-cleanup)
- **AI Logs**: 1 hour (auto-cleanup)

Cleanup is handled by the `/maintenance/cleanup` scheduled task.

## Troubleshooting

### Admin page shows "Database not configured"

- Ensure `DATABASE_URL` environment variable is set
- Check backend logs for database connection errors

### No data showing

- Verify backend server is running
- Check browser console for CORS or network errors
- Ensure frontend `.env` has correct `VITE_API_BASE_URL`

### API returns 503 error

- Database connection failed
- Check PostgreSQL is running and accessible
- Verify database credentials in `DATABASE_URL`
