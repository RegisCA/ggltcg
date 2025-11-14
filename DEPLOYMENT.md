# GGLTCG Deployment Guide

## Overview

This guide covers deploying the GGLTCG application to production:
- **Backend:** Render.com (Free Tier)
- **Frontend:** Vercel (Free Tier)

## Prerequisites

- GitHub account with the ggltcg repository
- Render account (connected to GitHub)
- Vercel account (connected to GitHub)
- Google Gemini API key (free from https://aistudio.google.com/apikey)

## Part 1: Backend Deployment (Render)

### Step 1: Fix Your Render Configuration

The error you're seeing is because Render is looking for the wrong module path. Here's how to fix it:

1. **Go to your Render dashboard** → Your web service (`ggltcg-backend`)

2. **Update the Start Command:**
   - Find the "Start Command" field
   - Change from: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
   - Change to: **`cd src && uvicorn api.app:app --host 0.0.0.0 --port $PORT`**

3. **Update the Root Directory:**
   - Set "Root Directory" to: `backend`

4. **Update the Build Command:**
   - Set "Build Command" to: `pip install -r requirements.txt`

### Step 2: Configure Environment Variables

In your Render service settings, add these environment variables:

| Key | Value | Notes |
|-----|-------|-------|
| `GOOGLE_API_KEY` | `your-actual-api-key` | From Google AI Studio |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Primary model |
| `GEMINI_FALLBACK_MODEL` | `gemini-2.5-flash-lite` | Fallback for capacity issues |
| `PYTHON_VERSION` | `3.13.0` | Python version |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Update after Vercel deployment |

### Step 3: Deploy Backend

1. Click **"Manual Deploy"** → **"Deploy latest commit"**
2. Wait for build to complete (3-5 minutes)
3. Once deployed, note your backend URL: `https://ggltcg.onrender.com`

### Step 4: Update CORS After Frontend Deployment

After you deploy to Vercel (Part 2), come back and update the `ALLOWED_ORIGINS` variable:

```text
ALLOWED_ORIGINS=https://ggltcg.vercel.app,https://ggltcg-git-*.vercel.app,http://localhost:5173
```

This allows your Vercel frontend (and local dev) to call your backend API.

## Part 2: Frontend Deployment (Vercel)

### Step 1: Configure Vercel Project

1. **Go to Vercel dashboard** → **Add New Project**
2. **Import your GitHub repository** (`RegisCA/ggltcg`)
3. **Configure the project:**
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build` (default is fine)
   - **Output Directory:** `dist` (default is fine)
   - **Install Command:** `npm install` (default is fine)

### Step 2: Configure Environment Variables

In Vercel project settings → Environment Variables, add:

| Name | Value | Environment |
|------|-------|-------------|
| `VITE_API_URL` | `https://ggltcg.onrender.com` | Production |

**Important:** Replace `ggltcg.onrender.com` with your actual Render backend URL from Part 1.

### Step 3: Deploy Frontend

1. Click **"Deploy"**
2. Wait for build to complete (2-3 minutes)
3. Once deployed, note your frontend URL: `https://ggltcg.vercel.app` (or similar)

### Step 4: Update Backend CORS

Go back to Render and update the `ALLOWED_ORIGINS` environment variable:

```
ALLOWED_ORIGINS=https://ggltcg.vercel.app,https://ggltcg-git-*.vercel.app,http://localhost:5173
```

**Note:** Replace `ggltcg.vercel.app` with your actual Vercel domain. Include preview deployment patterns if you want those to work.

Then redeploy your backend for the CORS changes to take effect.

## Verification & Testing

### Test Backend

Visit your Render URL directly:
```text
https://ggltcg.onrender.com/
```

You should see:
```json
{
  "name": "GGLTCG API",
  "version": "0.1.0",
  "status": "running"
}
```

Test the cards endpoint:
```text
https://ggltcg.onrender.com/games/cards
```

### Test Frontend

1. Visit your Vercel URL: `https://ggltcg.vercel.app`
2. Start a new game
3. Verify cards load correctly
4. Play a few turns against the AI

### Common Issues & Solutions

#### Backend Issues

**"Error loading ASGI app"**
- Verify Start Command is: `cd src && uvicorn api.app:app --host 0.0.0.0 --port $PORT`
- Verify Root Directory is: `backend`

**"Module not found" errors**
- Check that `requirements.txt` is in the `backend/` directory
- Verify Build Command is: `pip install -r requirements.txt`

**AI not responding**
- Check `GOOGLE_API_KEY` is set correctly in Render
- Check logs for API quota/capacity errors
- Fallback model should activate automatically on 429 errors

**Render free tier sleeping**
- Free tier spins down after 15 minutes of inactivity
- First request after sleep takes ~50 seconds
- Upgrade to paid tier for always-on service

#### Frontend Issues

**CORS errors in browser console**
- Verify `ALLOWED_ORIGINS` in Render includes your Vercel domain
- Redeploy backend after updating CORS
- Clear browser cache

**Can't connect to API**
- Verify `VITE_API_URL` in Vercel matches your Render backend URL
- Check backend is actually running (visit /health endpoint)
- Redeploy frontend after changing environment variables

**Cards not loading**
- Check Network tab in browser DevTools
- Verify backend `/games/cards` endpoint works directly
- Check for CORS errors

## Free Tier Limitations

### Render Free Tier
- 750 hours/month compute time
- Spins down after 15 minutes of inactivity
- 50-second cold start on first request
- 512MB RAM
- Shared CPU

**Workaround for sleeping:** Use a service like UptimeRobot to ping your backend every 14 minutes.

### Vercel Free Tier
- 100GB bandwidth/month
- 100 deployments/day
- Serverless function execution time: 10s max
- Fast, no cold starts for static assets

## Advanced Configuration

### Using an Alternate Deck (Custom Cards)

You can use a custom CSV file instead of the default `cards.csv` by setting the `CARDS_CSV_PATH` environment variable in Render:

1. **Upload your custom deck CSV** to your repository (e.g., `backend/data/custom_deck.csv`)
2. **In Render** → Environment Variables, add:
   - Key: `CARDS_CSV_PATH`
   - Value: `/opt/render/project/src/backend/data/custom_deck.csv`
3. **Redeploy** your backend

The CSV must follow the same format as `backend/data/cards.csv`.

Alternatively, you can modify the start command to use the `--deck` argument, but environment variables are cleaner for Render deployments.

## Production Best Practices

### Security
- Never commit `.env` files to Git
- Rotate API keys periodically
- Monitor API usage and quotas
- Use Render's secret environment variables

### Monitoring
- Check Render logs regularly for errors
- Monitor Google API quota usage
- Set up alerts for deployment failures
- Use Vercel Analytics (free tier available)

### Updates & Maintenance
- Test changes locally first
- Use feature branches and preview deployments
- Monitor error rates after deployments
- Keep dependencies updated (security patches)

## Troubleshooting Commands

### Check Backend Logs (Render)
1. Go to Render dashboard → Your service
2. Click "Logs" tab
3. Look for errors during startup or requests

### Check Frontend Build Logs (Vercel)
1. Go to Vercel dashboard → Your project
2. Click on a deployment
3. View build and function logs

### Test API Locally
```bash
cd backend
source venv/bin/activate  # or your virtualenv
uvicorn src.api.app:app --reload
```

Visit: http://localhost:8000/docs

### Test Frontend Locally Against Production Backend
```bash
cd frontend
echo "VITE_API_URL=https://ggltcg.onrender.com" > .env.local
npm run dev
```

Visit: http://localhost:5173

## Deployment Checklist

- [ ] Backend deployed to Render with correct Start Command
- [ ] All backend environment variables configured
- [ ] Backend health check returns 200 OK
- [ ] Frontend deployed to Vercel
- [ ] Frontend `VITE_API_URL` points to Render backend
- [ ] Backend CORS updated with Vercel domain
- [ ] Can start a new game from Vercel frontend
- [ ] AI opponent makes moves successfully
- [ ] Cards display correctly
- [ ] Victory screen works

## Support & Resources

- **Render Docs:** https://render.com/docs
- **Vercel Docs:** https://vercel.com/docs
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment/
- **Vite Deployment:** https://vite.dev/guide/static-deploy.html
- **Google Gemini API:** https://ai.google.dev/gemini-api/docs

## Next Steps

Once deployed successfully:

1. Test the full game flow in production
2. Share the Vercel URL with friends for playtesting
3. Monitor logs for any errors
4. Consider adding analytics (Vercel Analytics, Google Analytics)
5. Set up continuous deployment for automatic updates

---

**Congratulations! Your GGLTCG app is now live!** 🎉

Play at: `https://your-project.vercel.app`
