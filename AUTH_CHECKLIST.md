# Authentication Implementation Checklist

Quick checklist for implementing Google OAuth 2.0 authentication.

## Setup Phase

- [ ] **Google Cloud Console**
  - [ ] Create OAuth 2.0 Client ID
  - [ ] Add authorized redirect URIs
  - [ ] Copy Client ID
  - [ ] Copy Client Secret (keep secure!)

- [ ] **Environment Variables**
  - [ ] Backend `.env`: Add `GOOGLE_CLIENT_ID`
  - [ ] Backend `.env`: Add `GOOGLE_CLIENT_SECRET`
  - [ ] Backend `.env`: Generate and add `JWT_SECRET_KEY`
  - [ ] Backend `.env`: Update `ALLOWED_ORIGINS`
  - [ ] Frontend `.env`: Add `VITE_GOOGLE_CLIENT_ID`

## Installation Phase

- [ ] **Backend**
  - [ ] Run `pip install -r requirements.txt`
  - [ ] Run `alembic upgrade head` (create users table)
  - [ ] Verify no import errors

- [ ] **Frontend**
  - [ ] Run `npm install`
  - [ ] Add `react-router-dom` if needed
  - [ ] Verify no TypeScript errors

## Integration Phase

- [ ] **Frontend App Setup**
  - [ ] Wrap app with `GoogleOAuthProvider` in `main.tsx`
  - [ ] Wrap app with `AuthProvider` in `main.tsx`
  - [ ] Add routing for login page
  - [ ] Add protected routes (optional)

- [ ] **Testing**
  - [ ] Start backend server
  - [ ] Start frontend dev server
  - [ ] Navigate to login page
  - [ ] Click "Sign in with Google"
  - [ ] Verify token received
  - [ ] Check API calls include Authorization header
  - [ ] Test display name update
  - [ ] Test profanity filter
  - [ ] Test auto-logout on 401

## Deployment Phase

- [ ] **Render (Backend)**
  - [ ] Add `GOOGLE_CLIENT_ID` env var
  - [ ] Add `GOOGLE_CLIENT_SECRET` env var
  - [ ] Add `JWT_SECRET_KEY` env var (new one!)
  - [ ] Update `ALLOWED_ORIGINS` env var
  - [ ] Push to main branch
  - [ ] Verify migration runs
  - [ ] Check logs for errors

- [ ] **Vercel (Frontend)**
  - [ ] Add `VITE_GOOGLE_CLIENT_ID` env var
  - [ ] Update `VITE_API_URL` to production backend
  - [ ] Push to main branch
  - [ ] Test production login flow

## Verification Phase

- [ ] **Production Testing**
  - [ ] Open production frontend
  - [ ] Sign in with Google
  - [ ] Verify user created in database
  - [ ] Test API calls are authenticated
  - [ ] Test custom display name
  - [ ] Check rate limiting works
  - [ ] Verify auto-logout

- [ ] **Security Checks**
  - [ ] Client Secret not in frontend code
  - [ ] CORS restricted to known origins
  - [ ] HTTPS used for all OAuth flows
  - [ ] Tokens expire after 24 hours
  - [ ] Rate limiting prevents abuse

## Optional Enhancements

- [ ] Add user profile page
- [ ] Add "Remember me" option
- [ ] Implement refresh tokens
- [ ] Add user avatars from Google
- [ ] Track game statistics
- [ ] Build leaderboard
- [ ] Add friend system

## Documentation

- [ ] Read `docs/development/GOOGLE_OAUTH_SETUP.md`
- [ ] Read `docs/development/AUTH_IMPLEMENTATION.md`
- [ ] Review `ISSUE_124_SUMMARY.md`
- [ ] Check environment variable reference

## Help & Troubleshooting

If stuck, check:
1. `docs/development/GOOGLE_OAUTH_SETUP.md` - Troubleshooting section
2. Backend logs - `python run_server.py`
3. Browser console - Network tab for API calls
4. Environment variables - Are they set correctly?
5. Google Cloud Console - Are redirect URIs configured?

## Time Estimates

- Setup: 1 hour
- Installation: 15 minutes
- Integration: 1.5 hours
- Testing: 30 minutes
- Deployment: 15 minutes

**Total: ~3 hours**
