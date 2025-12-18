# Frontend Overview

This document describes the GGLTCG frontend architecture, its integration with
the backend API, and how to run and work on the frontend locally.

## Tech Stack

- React 19
- TypeScript 5.9
- Vite 7
- TanStack Query (React Query)
- Axios
- Tailwind CSS 4 (via design tokens, not utility classes for spacing)
- Google OAuth via `@react-oauth/google`

## Entry Point and Providers

The main entry point is `frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from './contexts/AuthContext';
import './index.css';
import App from './App';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <App />
        <Analytics />
        <SpeedInsights />
      </AuthProvider>
    </GoogleOAuthProvider>
  </StrictMode>,
);
```text
Key points:

- Google OAuth is configured via `VITE_GOOGLE_CLIENT_ID`.
- `AuthProvider` manages the authenticated user and JWT storage.
- Analytics and performance insights are wired for production via Vercel.

## High-Level Layout

The main game UI is rendered from `App.tsx` and underlying components (see
`docs/development/ARCHITECTURE.md` for full layout):

- Game board with both players' zones (hand, in-play, sleep zone)
- Action panel for play/tussle/end-turn actions
- Log / play-by-play panel

Components are organized roughly as:

- `src/components/game/` – Game-specific UI (board, zones, cards, action panel)
- `src/components/ui/` – Reusable UI primitives (buttons, modals, panels)
- `src/api/` – Axios client and typed API wrappers
- `src/types/` – Shared TypeScript types for API responses and game objects
- `src/hooks/` – React Query hooks for fetching game state and performing
  actions

## Backend Integration

All backend calls go through a central Axios client in `src/api/client.ts` and
typed wrappers (e.g. `src/api/game.ts`, `src/api/authService.ts`).

Environment variable `VITE_API_URL` controls the backend base URL, typically:

- `http://localhost:8000` in development
- `https://ggltcg.onrender.com` in production

React Query is used to:

- Fetch current game state on an interval
- Trigger mutations for play-card, tussle, end-turn, lobby actions, stats, etc.

For detailed backend contracts and JSON shapes, see:

- `docs/development/ARCHITECTURE.md`
- `backend/src/api/schemas.py`

## Authentication Flow

Authentication is handled via Google OAuth and JWTs:

1. The frontend uses `@react-oauth/google` to obtain a Google ID token.
2. The token is sent to the backend `POST /auth/google` endpoint.
3. Backend verifies the Google token, creates/loads a user, and returns a JWT.
4. `AuthContext` stores the JWT (currently in `localStorage`) and attaches it to
   API requests.
5. Protected views/components can check the auth state and redirect to login as
   needed.

See:

- `docs/development/AUTH_IMPLEMENTATION.md`
- `docs/development/ENV_VARS_AUTH.md`

## Styling and Design System

The frontend uses a design-token-based system for spacing and typography (see
`coding.instructions.md` and `TYPOGRAPHY_DESIGN_SYSTEM.md`):

- Spacing uses CSS custom properties (e.g. `var(--spacing-component-md)`)
  instead of hard-coded pixels or Tailwind spacing utilities.
- Typography follows the defined heading/body hierarchy and font choices
  (Bangers, Lato).

When adding new components:

- Use existing tokens for padding, margins, and gaps.
- Keep layout consistent with the two-column game board + side panel pattern.

## Running the Frontend Locally

```bash
cd frontend
npm install
npm run dev
```text
You also need the backend running (see project `README.md` and
`docs/development/ARCHITECTURE.md`).

## Where to Go Next

- For effect and game engine details:
  `docs/development/EFFECT_SYSTEM_ARCHITECTURE.md`.
- For backend API and persistence: `docs/development/ARCHITECTURE.md`,
  `docs/development/DATABASE_SCHEMA.md`.
- For auth specifics: `docs/development/AUTH_IMPLEMENTATION.md`.
