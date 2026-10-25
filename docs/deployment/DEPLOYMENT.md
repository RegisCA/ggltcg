# Deployment

GGLTCG runs on free tiers: the FastAPI backend and its PostgreSQL database on
[Render](https://render.com), the React frontend on
[Vercel](https://vercel.com). Both deploy automatically when `main` changes,
so every merged pull request goes straight to production.

```text
 push to main ──┬──► Render  (backend/)   pip install → alembic upgrade head → uvicorn
                │      └── PostgreSQL (Render)
                └──► Vercel  (frontend/)  npm install → tsc + vite build → static SPA
```

This guide covers how production is set up and how to stand up your own copy.
For local development, see the [README](../../README.md#run-it-locally).

- [Backend on Render](#backend-on-render)
- [Frontend on Vercel](#frontend-on-vercel)
- [Google sign-in](#google-sign-in)
- [Scheduled maintenance](#scheduled-maintenance)
- [Verifying a deploy](#verifying-a-deploy)
- [Troubleshooting](#troubleshooting)
- [Moving the backend to another region](#moving-the-backend-to-another-region)

## Backend on Render

### Database

Create a Render PostgreSQL instance first and copy its **External Database
URL**. Use the full hostname (for example `dpg-xxxx-a.oregon-postgres.render.com`).
The short internal form (`dpg-xxxx-a`) fails at startup with
`could not translate host name`.

### Web service

Create a Render web service from the repository with these settings. They are
also captured as a Render Blueprint in
[`backend/render.yaml`](../../backend/render.yaml).

| Setting | Value |
| --- | --- |
| Root directory | `backend` |
| Runtime | Python, `PYTHON_VERSION=3.13.0` |
| Build command | `pip install -r requirements.txt` |
| Start command | `alembic upgrade head && cd src && uvicorn api.app:app --host 0.0.0.0 --port $PORT` |
| Branch | `main`, auto-deploy on |

Migrations run as part of the start command because Render's free tier has no
pre-deploy step. Every schema change therefore ships as an Alembic migration in
`backend/alembic/versions/`; the database is never changed by hand.

Pin `PYTHON_VERSION`. Without it Render may pick a newer Python than the pinned
dependencies support, and the build fails while compiling `pydantic-core`.

### Environment variables

`backend/.env.example` is the commented template for local development. In
production:

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | yes | PostgreSQL External Database URL. A `sqlite:///` URL works for local development. |
| `GOOGLE_API_KEY` | yes | Gemini API key for the AI opponent ([get one](https://aistudio.google.com/api-keys)). |
| `GOOGLE_CLIENT_ID` | yes | OAuth client ID used to verify Google sign-in tokens. |
| `JWT_SECRET_KEY` | yes | Signs session tokens. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
| `ALLOWED_ORIGINS` | yes | Comma-separated CORS origins, e.g. `https://ggltcg.vercel.app,http://localhost:5173`. |
| `GEMINI_MODEL` | no | Primary model. Default `gemini-flash-lite-latest`. |
| `GEMINI_FALLBACK_MODEL` | no | Used when the primary returns 429. Default `gemini-2.5-flash-lite`. |
| `ADMIN_EMAILS` | no | Google accounts allowed into `/admin.html` and `/admin/*`. Empty means nobody (fails closed). |
| `MAINTENANCE_API_KEY` | no | Shared secret for `/maintenance/*`, used by the scheduled cleanup job. Unset disables those endpoints (503). |
| `ENVIRONMENT` | no | `production` in production; tags Sentry events. |
| `SENTRY_DSN` | no | Backend error tracking. |
| `POSTHOG_API_KEY`, `POSTHOG_HOST` | no | Server-side analytics events. Unset disables them. |
| `LOG_LEVEL` | no | Python log level. |
| `CARDS_CSV_PATH` | no | Alternative card data file (see below). |

Change the AI model by editing `GEMINI_MODEL` in the Render dashboard rather
than in `render.yaml`, so a model swap doesn't need a code change.

### Alternative card data

`CARDS_CSV_PATH` points the engine at a different card file with the same
columns as `backend/data/cards.csv`. On Render, paths are relative to
`/opt/render/project/src/`, so a file committed at `backend/data/custom.csv`
is `/opt/render/project/src/backend/data/custom.csv`. The simulation harness
uses the same variable to test cost changes without editing the real data.

## Frontend on Vercel

Import the repository into Vercel, set the project's root directory to
`frontend` and choose the Vite framework preset (`npm run build`, output
`dist`). The build produces three entry points: `index.html` (the game),
`admin.html` (the admin dashboard) and `design.html` (a component fixture
harness). Screens inside the game are switched in React state rather than by
URL path, so no rewrite rules are needed.

| Variable | Required | Purpose |
| --- | --- | --- |
| `VITE_API_URL` | yes | Backend base URL, e.g. `https://<your-service>.onrender.com`. |
| `VITE_GOOGLE_CLIENT_ID` | yes | Same OAuth client ID as the backend. Never the client secret. |
| `VITE_SENTRY_DSN` | no | Frontend error tracking. |
| `VITE_POSTHOG_KEY`, `VITE_POSTHOG_HOST` | no | Product analytics. Unset disables them. |

Vite inlines these at build time, so redeploy after changing one.

After the first Vercel deploy, add its domain to the backend's
`ALLOWED_ORIGINS`. Add preview domains too if you want preview deployments to
reach the API.

## Google sign-in

Players sign in with Google; the backend verifies the ID token and issues its
own JWT. Create an OAuth 2.0 client in Google Cloud Console and add your
Vercel domain and `http://localhost:5173` as authorised JavaScript origins.
Step-by-step instructions are in
[GOOGLE_OAUTH_SETUP.md](../development/GOOGLE_OAUTH_SETUP.md).

## Scheduled maintenance

[`.github/workflows/cleanup.yml`](../../.github/workflows/cleanup.yml) calls
`POST /maintenance/cleanup` once a day, authenticated with the
`MAINTENANCE_API_KEY` repository secret. It marks abandoned games and purges
stale AI decision logs, playback data and simulation rows so the free-tier
database stays small. It can also be run by hand from the Actions tab or the
admin dashboard's Maintenance tab.

## Verifying a deploy

`GET /health` reports database connectivity, the applied migration, the
deployed commit and the active AI models:

```json
{
  "status": "healthy",
  "database": { "connected": true, "migration_version": "014" },
  "games": { "in_progress": 1, "total": 3113 },
  "deploy": { "git_commit": "492422f…", "git_branch": "main" },
  "ai": { "planner": "enum", "model": "gemini-flash-lite-latest", "fallback_model": "gemini-2.5-flash-lite" }
}
```

Compare `deploy.git_commit` with `git log origin/main` to confirm a merge is
live. Free-tier builds can take several minutes after a push. Then open the
frontend, start a game against the AI and play a turn.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| First request takes ~50 s | The free tier sleeps after 15 minutes idle. The frontend's loading screen waits on `/health` while the service wakes. |
| `Error loading ASGI app` | The start command must `cd src` before `uvicorn api.app:app`, with root directory `backend`. |
| Build fails compiling `pydantic-core` | `PYTHON_VERSION` is not pinned to `3.13.0`. |
| `could not translate host name "dpg-..."` | `DATABASE_URL` uses the internal hostname. Use the External Database URL. |
| CORS errors in the browser | The frontend's origin is missing from `ALLOWED_ORIGINS`. Update it and let Render restart. |
| Frontend calls the wrong backend | `VITE_API_URL` is baked in at build time. Fix it in Vercel and redeploy. |
| AI turns fail or stall | Check `GOOGLE_API_KEY`, then Render logs for quota errors. 429s fall back to `GEMINI_FALLBACK_MODEL` automatically. |
| Admin dashboard says access denied | Your Google account is not in `ADMIN_EMAILS`. |

Render logs are under the service's **Logs** tab; Vercel build logs are on each
deployment's page.

## Moving the backend to another region

Production moved from Ohio to Oregon in May 2026 by running a second service
alongside the first:

1. Create a new Render web service from the same repository, with the settings
   in [Web service](#web-service).
2. Copy the environment variables from the old service, then set
   `DATABASE_URL` to the External URL of the database you want to use.
3. Deploy and check `/health`, Google sign-in and an AI turn.
4. Point the frontend's `VITE_API_URL` and the cleanup workflow's `API_URL` at
   the new service, and update `ALLOWED_ORIGINS` if the domain changed.
5. Suspend the old service for a few days as a rollback path, then delete it.
