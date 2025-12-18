# Google OAuth 2.0 Authentication Setup Guide

This guide explains how to set up Google OAuth 2.0 authentication for GGLTCG.

## Overview

GGLTCG uses Google OAuth 2.0 for user authentication. This allows players to:

- Sign in securely with their Google account
- Maintain their identity across sessions
- Set custom display names (with profanity filtering)
- Track game statistics and leaderboard rankings

## Architecture

### Backend (FastAPI)

- **User Model**: Stores Google ID, first name, and custom display name
- **JWT Tokens**: Issues short-lived JWT tokens (24 hours) for API
  authentication
- **Rate Limiting**: Protects auth endpoints from abuse
- **Profanity Filter**: Validates custom display names

### Frontend (React)

- **Google OAuth Provider**: Uses `@react-oauth/google` for OAuth flow
- **Auth Context**: Manages authentication state across the app
- **Auto Token Injection**: Axios interceptor adds JWT to all API requests
- **Auto Logout**: Redirects to login on 401 responses

## Setup Instructions

### 1. Google Cloud Console Configuration

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one

2. **Enable Google+ API**
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google+ API"
   - Click "Enable"

3. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client ID"
   - Choose "Web application"
   - Name it "GGLTCG Web Client"

4. **Configure Authorized Redirect URIs**

   Add the following URIs:

   ```text
   # Production
   https://ggltcg.vercel.app
   https://ggltcg.vercel.app/login

   # Development
   http://localhost:5173
   http://localhost:5173/login
   http://localhost:3000
   http://localhost:3000/login
   ```

5. **Save Credentials**
   - Copy the **Client ID**
   - Copy the **Client Secret**
   - Keep these secure!

### 2. Backend Environment Variables

Create or update `.env` file in `backend/`:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# JWT Secret (generate a random string)
JWT_SECRET_KEY=your_random_secret_key_here

# Database (already configured)
DATABASE_URL=your_database_url

# CORS (add frontend URLs)
ALLOWED_ORIGINS=http://localhost:5173,https://ggltcg.vercel.app
```text
**⚠️ SECURITY**:
- Never commit `.env` to version control
- Use different secrets for development and production
- Generate JWT secret with: `python -c "import secrets;
  print(secrets.token_urlsafe(32))"`

### 3. Frontend Environment Variables

Create or update `.env` file in `frontend/`:

```bash
# Google OAuth (Client ID only - never expose Secret!)
VITE_GOOGLE_CLIENT_ID=your_google_client_id_here

# API URL
VITE_API_URL=http://localhost:8000  # Development
# VITE_API_URL=https://ggltcg.onrender.com  # Production
```text
**⚠️ SECURITY**:
- Only include `GOOGLE_CLIENT_ID` in frontend
- Never include `GOOGLE_CLIENT_SECRET` in frontend
- Vite exposes `VITE_*` variables to the browser

### 4. Backend Installation

```bash
cd backend

# Activate virtual environment
source ../.venv/bin/activate

# Install new dependencies
pip install -r requirements.txt

# Run database migration
alembic upgrade head

# Start server
python run_server.py
```text
### 5. Frontend Installation

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```text
## Deployment

### Render (Backend)

1. **Environment Variables**
   - Go to Render dashboard > Your service > Environment
   - Add the following variables:
     ```
     GOOGLE_CLIENT_ID=<your_client_id>
     GOOGLE_CLIENT_SECRET=<your_client_secret>
     JWT_SECRET_KEY=<generate_new_secret_for_production>
     ALLOWED_ORIGINS=https://ggltcg.vercel.app
     ```

2. **Database Migration**
   - Migrations run automatically on deploy via `render.yaml`
   - Verify with: `alembic current`

### Vercel (Frontend)

1. **Environment Variables**
   - Go to Vercel dashboard > Your project > Settings > Environment Variables
   - Add the following:
     ```
     VITE_GOOGLE_CLIENT_ID=<your_client_id>
     VITE_API_URL=https://ggltcg.onrender.com
     ```

2. **Redeploy**
   - Environment changes require a redeploy
   - Push to main branch or manually trigger deploy

## Testing Authentication

### Local Testing

1. **Start Backend**

   ```bash
   cd backend
   source ../.venv/bin/activate
   python run_server.py
   ```

1. **Start Frontend**

   ```bash
   cd frontend
   npm run dev
   ```

1. **Test Login Flow**
   - Open `http://localhost:5173/login`
   - Click "Sign in with Google"
   - Complete OAuth flow
   - Should redirect to home page with user authenticated

### API Testing

Test endpoints with curl:

```bash
# Authenticate (you need a real Google token)
curl -X POST http://localhost:8000/auth/google \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_GOOGLE_ID_TOKEN"}'

# Response: {"jwt_token": "...", "user": {...}}

# Verify token
curl http://localhost:8000/auth/verify \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get profile
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Update display name
curl -X PUT http://localhost:8000/auth/profile \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "CoolPlayer123"}'
```text
## Security Features

### Backend Security
- ✅ Token verification using Google's official library
- ✅ JWT tokens with expiration (24 hours)
- ✅ Rate limiting on auth endpoints (10 req/min)
- ✅ Profanity filtering on display names
- ✅ HTTPS required in production
- ✅ CORS restricted to known origins

### Frontend Security
- ✅ Tokens stored in localStorage (consider httpOnly cookies for production)
- ✅ Client Secret never exposed to browser
- ✅ Auto-logout on 401 responses
- ✅ Token validation on protected routes

### Best Practices
- Use HTTPS in production
- Rotate JWT secret keys periodically
- Monitor rate limiting logs for abuse
- Consider implementing refresh tokens for longer sessions
- Add 2FA for admin accounts (future)

## Troubleshooting

### "Invalid token" errors
- Check that `GOOGLE_CLIENT_ID` matches in both backend and frontend
- Verify token hasn't expired (Google tokens expire in 1 hour)
- Ensure backend can reach Google's token verification endpoint

### CORS errors
- Add frontend URL to `ALLOWED_ORIGINS` in backend `.env`
- Restart backend after changing environment variables
- Check browser console for specific CORS error

### Rate limiting errors
- Wait 60 seconds before retrying
- Check if you're making too many requests
- Consider increasing limits in `auth_routes.py` for development

### Display name rejected
- Check for profanity (better-profanity filter)
- Ensure length is 1-50 characters
- Try a different name

### Database migration fails
- Check `DATABASE_URL` is correct
- Ensure database is accessible
- Run `alembic current` to check migration status
- Run `alembic upgrade head` to apply migrations

## Migration from Unauthenticated System

No migration needed! Current system uses in-memory games only. After
authentication:
- Players can set persistent display names
- Game statistics will be tracked (future feature)
- Leaderboards can be implemented (future feature)

Existing game sessions will continue to work but won't be associated with
authenticated users until next game.

## API Reference

### POST `/auth/google`
Authenticate with Google OAuth token

**Request:**
```json
{
  "token": "google_id_token_here"
}
```text
**Response:**
```json
{
  "jwt_token": "eyJ...",
  "user": {
    "google_id": "123456789",
    "first_name": "John",
    "display_name": "John",
    "custom_display_name": null
  }
}
```text
### GET `/auth/verify`
Verify JWT token is valid

**Headers:**
```text
Authorization: Bearer <jwt_token>
```text
**Response:**
```json
{
  "valid": true,
  "google_id": "123456789"
}
```text
### GET `/auth/me`
Get current user profile

**Headers:**
```text
Authorization: Bearer <jwt_token>
```text
**Response:**
```json
{
  "google_id": "123456789",
  "first_name": "John",
  "display_name": "CoolPlayer",
  "custom_display_name": "CoolPlayer",
  "created_at": "2025-11-27T12:00:00Z",
  "updated_at": "2025-11-27T13:00:00Z"
}
```text
### PUT `/auth/profile`
Update display name

**Headers:**
```text
Authorization: Bearer <jwt_token>
```text
**Request:**
```json
{
  "display_name": "NewCoolName"
}
```text
**Response:**
```json
{
  "success": true,
  "user": {
    "google_id": "123456789",
    "first_name": "John",
    "display_name": "NewCoolName",
    "custom_display_name": "NewCoolName"
  }
}
```text
## Next Steps

After authentication is working:
1. Add protected routes in frontend (require login)
2. Implement user settings page for display name
3. Add game statistics tracking
4. Build leaderboard system
5. Consider adding refresh tokens for longer sessions
6. Add user profile avatars (from Google profile picture)
7. Implement friend/challenge system

## Support

For issues or questions:
- Check the troubleshooting section above
- Review server logs for error details
- Check browser console for frontend errors
- Verify environment variables are set correctly
