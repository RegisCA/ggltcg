# Quick Deployment Fix

## Backend (Render) - IMMEDIATE FIX

Go to your Render dashboard and change the **Start Command** from:
```
uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
```

To:
```
uvicorn src.api.app:app --host 0.0.0.0 --port $PORT
```

Also ensure:
- **Root Directory:** `backend`
- **Build Command:** `pip install -r requirements.txt`

Then click **"Manual Deploy"** → **"Deploy latest commit"**

## Full Deployment Steps

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete instructions.

### Quick Checklist

#### Backend (Render)
1. ✅ Start Command: `uvicorn src.api.app:app --host 0.0.0.0 --port $PORT`
2. ✅ Root Directory: `backend`
3. ✅ Environment Variables:
   - `GOOGLE_API_KEY` (your actual key)
   - `GEMINI_MODEL=gemini-2.5-flash`
   - `PYTHON_VERSION=3.13.0`
   - `ALLOWED_ORIGINS=http://localhost:5173` (update after Vercel deploy)

#### Frontend (Vercel)
1. ✅ Root Directory: `frontend`
2. ✅ Framework: Vite
3. ✅ Build Command: `npm run build`
4. ✅ Output Directory: `dist`
5. ✅ Environment Variable:
   - `VITE_API_URL=https://ggltcg.onrender.com`

#### After Both Deploy
1. Update backend `ALLOWED_ORIGINS` to include Vercel domain
2. Redeploy backend to apply CORS changes
3. Test the full game flow

## Your URLs

After deployment, you'll have:
- **Backend:** `https://ggltcg.onrender.com`
- **Frontend:** `https://ggltcg.vercel.app`

Test backend: Visit `https://ggltcg.onrender.com/health`
Test frontend: Visit `https://ggltcg.vercel.app` and start a game
