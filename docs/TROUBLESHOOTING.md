# Troubleshooting Guide

## Development Issues

### Backend/API Issues

- **Health Check:** Visit `http://localhost:8000/health` to verify the backend is running.
- **API Documentation:** Check `http://localhost:8000/docs` for interactive API docs.
- **Logs:** Check the backend terminal for detailed error messages.

### Frontend Issues

- **Console Errors:** Open browser developer console (F12) to check for errors.
- **API Connection:** Verify `VITE_API_URL` in `.env.local` points to the correct backend URL.
- **Network Tab:** Check the Network tab in developer tools to see API request/response details.

### Authentication Issues

- **OAuth Credentials:** Confirm Google OAuth credentials are correctly set:
  - Backend: `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `backend/.env`
  - Frontend: `VITE_GOOGLE_CLIENT_ID` in `frontend/.env.local`
- **Setup Guide:** See [GOOGLE_OAUTH_SETUP.md](development/GOOGLE_OAUTH_SETUP.md) for detailed setup instructions.
- **Implementation Details:** See [AUTH_IMPLEMENTATION.md](development/AUTH_IMPLEMENTATION.md) for how authentication works.

## AI/LLM Issues

### Rate Limit Exceeded

If you see "429 Too Many Requests" or rate limit errors:

- **Check Usage:** Visit <https://aistudio.google.com/usage> to see your API usage.
- **Free Tier Limits:** Most free tier models have a limit of 15 requests per minute (RPM).
- **Wait Period:** Wait 1 minute before trying again.
- **Automatic Retry:** The code automatically retries with exponential backoff (1s, 2s, 4s).
- **Slow Down:** If playing frequently, slow down between turns to avoid hitting rate limits.

### AI Not Making Decisions

If the AI player is not responding:

1. **Check Backend Logs:** Look at the backend terminal for detailed logs showing:
   - Gemini API calls and responses
   - Prompts sent to the AI
   - Error messages or warnings
2. **Look for Errors:** Search for `ERROR` or `WARNING` messages in the output.
3. **Verify API Key:** Ensure `GOOGLE_API_KEY` is set correctly in `backend/.env`.
4. **Check Model:** Verify the model name in `GEMINI_MODEL` (if set) is valid.

### Capacity Issues

If you get "503 Service Unavailable" or capacity errors:

- **Model Overloaded:** The free tier model may be at capacity.
- **Try Alternative Model:** Set `GEMINI_MODEL` in `backend/.env` to one of:
  - `gemini-2.5-flash` (newest, more stable)
  - `gemini-flash-latest` (automatically uses latest stable)
  - `gemini-2.0-flash` (proven stable)
- **Fallback Model:** The system automatically tries a fallback model if the primary fails.

### Using Alternative LLM Providers

The project supports multiple LLM providers beyond Google Gemini:

- **See Setup Guide:** `backend/AI_SETUP.md` has detailed setup instructions for:
  - Google Gemini (recommended for free tier)
  - Claude (Anthropic)
  - Other providers
- **Switch Provider:** Update your `.env` file according to the provider's requirements.

## Production Issues

### Backend Won't Wake Up

If the backend at <https://ggltcg.onrender.com> won't wake up:

- **Free Tier Sleep:** Render's free tier puts the backend to sleep after inactivity.
- **Wake Time:** It can take up to 50 seconds to wake up on first request.
- **Patience:** Wait for the initial request to complete, then subsequent requests will be fast.

### Frontend Not Loading

- **Deployment Status:** Check [Vercel Dashboard](https://vercel.com/dashboard) for deployment status.
- **Build Errors:** Look for build errors in the Vercel deployment logs.
- **Environment Variables:** Ensure all required env vars are set in Vercel project settings.

## Database Issues

### Migration Errors

- **Check Alembic:** Ensure you've run all migrations: `alembic upgrade head`
- **Migration Guide:** See [DATABASE_SCHEMA.md](development/DATABASE_SCHEMA.md) for details.

### Connection Issues

- **Connection String:** Verify `DATABASE_URL` in `backend/.env` is correct.
- **PostgreSQL Running:** Ensure PostgreSQL is running locally or accessible remotely.

## Getting Help

If you're still stuck:

1. **Check Documentation:** See the [Documentation Index](README.md) for guides.
2. **Search Issues:** Check [GitHub Issues](https://github.com/RegisCA/ggltcg/issues) for similar problems.
3. **Open an Issue:** Create a new issue with:
   - Steps to reproduce
   - Error messages
   - Environment details (OS, Python version, etc.)
