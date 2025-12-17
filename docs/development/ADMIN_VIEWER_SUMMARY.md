# Admin Data Viewer - Implementation Summary

## Overview

A simple web-based admin panel for viewing GGLTCG database data without complex
authentication or heavy infrastructure.

## What Was Built

### Backend API (`/backend/src/api/routes_admin.py`)

New `/admin/*` endpoints providing read-only access to database data:

- `GET /admin/stats/summary` — Dashboard stats. Shows user counts,
  game stats, AI log counts and recent activity.

- `GET /admin/ai-logs` — AI decision logs (limit: 50). Includes Gemini
  prompts, responses and basic reasoning metadata.

- `GET /admin/ai-logs/{id}` — Specific AI log. Returns full prompt and
  response details for a single log entry.

- `GET /admin/games` — Games list (limit: 100). Returns active and
  completed games with summary metadata.

- `GET /admin/games/{id}` — Full game state. Returns the complete JSONB
  game state for a given game ID.

- `GET /admin/game-playbacks` — Completed games (limit: 30). Play-by-
  play summaries for recently completed games.

- `GET /admin/game-playbacks/{id}` — Full playback. Includes starting
  decks and complete play-by-play data.

- `GET /admin/players` — Player stats. Aggregated leaderboard-style
  statistics for players.

- `GET /admin/users` — Registered users. Google OAuth accounts.

### Frontend UI (`/frontend/src/components/AdminDataViewer.tsx`)

React-based admin panel with:

- **Summary Tab**: Database overview with real-time stats
- **AI Logs Tab**: Expandable log viewer with prompt/response inspection
- **Games Tab**: Game browser with status indicators
- **Playbacks Tab**: Completed game viewer with JSON export

**Access**: `http://localhost:5173/admin.html` (dev) or `/admin.html`
(production)

## Key Features

✅ **No Authentication** - Simple access for internal use
✅ **Read-Only** - Safe to use without worrying about data modification
✅ **Auto-Refresh** - Summary updates every 30s, logs every 10s
✅ **Responsive Design** - Works on desktop and tablet
✅ **JSON Export** - Direct links to raw JSON data

## Usage

### Local Development

```bash
# Terminal 1: Start backend
cd backend
source ../.venv/bin/activate
python run_server.py

# Terminal 2: Start frontend
cd frontend
npm run dev

# Open browser
open http://localhost:5173/admin.html

```

### Production

Access directly via deployed frontend URL:

```text
https://your-app.vercel.app/admin.html

```

## Common Use Cases

### Debug AI Behavior

1. Go to AI Logs tab
2. Click "View Full" on recent logs
3. Review prompt structure and AI response
4. Check reasoning quality

### Review Recent Games

1. Go to Games tab
2. Filter by status if needed
3. Check game progression and player activity
4. Copy game ID for deeper inspection

### Monitor System Health

1. View Summary tab
2. Check recent activity (24h games, 1h AI logs)
3. Verify expected player/game counts
4. Look for anomalies

### Export Game Data

1. Go to Playbacks tab
2. Find completed game
3. Click "View Full Playback JSON"
4. Copy/save JSON for analysis

## Database Tables Covered

- `users` — `/admin/users` — Google OAuth accounts
- `games` — `/admin/games` — Game sessions (active and completed)
- `game_playback` — `/admin/game-playbacks` — Completed games
  (24h retention)

- `ai_decision_logs` — `/admin/ai-logs` — AI prompts/responses
  (1h retention)

- `player_stats` — `/admin/players` — Aggregated player statistics

Not yet covered:

- `game_actions` — Individual actions (future enhancement)
- `game_stats` — Aggregated game metrics (future enhancement)

## Security Considerations

⚠️ **NO AUTHENTICATION** - Anyone with the URL can access data

**Current State**: Acceptable for:

- Internal development
- Small teams with trusted access
- Low-sensitivity data

**Not Recommended For**:

- Public-facing deployments
- Sensitive player information
- Production with external users

**Future Enhancements**:

1. Add API key authentication
2. Implement admin role checking
3. IP whitelist restrictions
4. OAuth-based admin access

## Testing

Run automated tests:

```bash
./scripts/test-admin-viewer.sh

```

Tests verify:

- All endpoints return valid JSON
- Database queries execute successfully
- Pagination and filtering work
- CORS allows frontend access

## Implementation Notes

### Why Separate HTML File?

Using `admin.html` instead of integrating into main app:

- ✅ Simpler deployment (no routing changes)
- ✅ Easier to secure/restrict later
- ✅ Independent from main app auth flow
- ✅ Can be removed without affecting game

### Why No Authentication?

Keeping it simple for MVP:

- Small team, trusted environment
- Focus on functionality first
- Easy to add later without refactoring
- Reduces initial development time

### Vite Multi-Page Setup

The `vite.config.ts` was updated to support multiple HTML entry points:

```typescript
build: {
  rollupOptions: {
    input: {
      main: resolve(__dirname, 'index.html'),
      admin: resolve(__dirname, 'admin.html'),
    },
  },
}

```

This allows both `index.html` (main app) and `admin.html` to work independently.

## Files Modified/Created

**Backend**:

- ✨ NEW: `backend/src/api/routes_admin.py` (484 lines)
- 📝 MODIFIED: `backend/src/api/app.py` (registered admin router)

**Frontend**:

- ✨ NEW: `frontend/src/components/AdminDataViewer.tsx` (419 lines)
- ✨ NEW: `frontend/src/admin.tsx` (entry point)
- ✨ NEW: `frontend/admin.html` (HTML page)
- 📝 MODIFIED: `frontend/vite.config.ts` (multi-page config)

**Documentation**:

- ✨ NEW: `docs/development/ADMIN_VIEWER.md` (comprehensive guide)
- ✨ NEW: `scripts/test-admin-viewer.sh` (automated testing)
- ✨ NEW: `docs/development/ADMIN_VIEWER_SUMMARY.md` (this file)

## Next Steps (Optional Enhancements)

**Short Term**:
**Short Term**:

1. Add basic API key authentication
2. Add date range filtering for logs
3. Export functionality (CSV/JSON downloads)
4. Search/filter capabilities per tab

**Long Term**:
**Long Term**:

1. Real-time updates via WebSocket
2. Graph visualizations (games over time, win rates)
3. Admin actions (mark games as abandoned, reset stats)
4. Audit logging for admin access

## Deployment

No special deployment steps needed:

**Backend**: Admin routes included automatically via `routes_admin.py` import
**Frontend**: `admin.html` builds alongside `index.html` via Vite

Verify deployment:

```bash
# Backend
curl https://your-api.onrender.com/admin/stats/summary

# Frontend
open https://your-app.vercel.app/admin.html

```

---

**Status**: ✅ Complete and Ready for Use
**Test Coverage**: API endpoints verified
**Documentation**: Complete
**Security**: ⚠️ No auth (acceptable for internal use)
