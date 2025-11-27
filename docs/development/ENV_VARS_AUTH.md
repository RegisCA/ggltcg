# Environment Variables Reference

Quick reference for setting up authentication environment variables.

## Required Environment Variables

### Backend (.env)

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=<your_google_client_id>
GOOGLE_CLIENT_SECRET=<your_google_client_secret>

# JWT Secret (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=<your_random_secret_key>

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,https://ggltcg.vercel.app

# Database (already configured)
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### Frontend (.env)

```bash
# Google OAuth (Client ID only - NEVER include Secret!)
VITE_GOOGLE_CLIENT_ID=<your_google_client_id>

# API URL
VITE_API_URL=http://localhost:8000  # Development
# VITE_API_URL=https://ggltcg.onrender.com  # Production
```

## Generating Secrets

### JWT Secret Key
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Example Output
```
MdR7X9kP2nQ8vL5wY3jF6tH4sB1mN0cA9zE2xK7pG
```

## Deployment Configuration

### Render (Backend)

Add these in Render Dashboard → Environment:
- `GOOGLE_CLIENT_ID` = your_client_id
- `GOOGLE_CLIENT_SECRET` = your_client_secret
- `JWT_SECRET_KEY` = new_random_secret_for_production
- `ALLOWED_ORIGINS` = https://ggltcg.vercel.app
- `DATABASE_URL` = (auto-configured by Render)

### Vercel (Frontend)

Add these in Vercel Dashboard → Settings → Environment Variables:
- `VITE_GOOGLE_CLIENT_ID` = your_client_id
- `VITE_API_URL` = https://ggltcg.onrender.com

## Security Notes

- **NEVER** commit `.env` files to git
- **NEVER** include `GOOGLE_CLIENT_SECRET` in frontend
- Use different secrets for development and production
- Rotate `JWT_SECRET_KEY` periodically
- Keep production secrets secure and backed up

## Verification

### Backend
```bash
cd backend
source ../.venv/bin/activate
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Client ID:', os.getenv('GOOGLE_CLIENT_ID')[:20] + '...')"
```

### Frontend
```bash
cd frontend
npm run dev
# Check browser console: window.import.meta.env
```
