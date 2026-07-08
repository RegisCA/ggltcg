/**
 * Admin sign-in gate for /admin.html.
 *
 * admin.html has no router/AuthContext of its own (see admin.tsx) but shares
 * the same origin and localStorage as the main game, so it reuses the exact
 * same Google sign-in flow and token storage keys (ggltcg_auth_token /
 * ggltcg_user) — apiClient's request interceptor already attaches the
 * resulting Bearer token to every /admin/* call with no further wiring.
 *
 * Being signed in only proves you're *a* GGLTCG user; the backend still
 * requires the token's email to be in the ADMIN_EMAILS allowlist (see
 * backend/src/api/admin_auth.py) before any /admin/* route responds. This
 * gate makes exactly one request (the summary stats AdminApp needs first
 * anyway, via the shared useSummary() query/cache) to find out which of
 * three states applies: not signed in (401), signed in but not allowlisted
 * (403), or authorized.
 */

import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { authService } from '../../api/authService';
import { useSummary } from '../../hooks/useAdminData';
import AdminApp from './AdminApp';

const TOKEN_KEY = 'ggltcg_auth_token';
const USER_KEY = 'ggltcg_user';

function readStoredDisplayName(): string | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    const user = JSON.parse(raw) as { display_name?: string; first_name?: string };
    return user.display_name ?? user.first_name ?? null;
  } catch {
    return null;
  }
}

function clearStoredAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

const shellStyle: React.CSSProperties = {
  minHeight: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 'var(--spacing-component-lg)',
  background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))',
  color: 'var(--ink-text)',
};

const cardStyle: React.CSSProperties = {
  maxWidth: '420px',
  width: '100%',
  padding: 'var(--spacing-component-lg)',
  background: 'var(--color-panel)',
  borderRadius: '8px',
  border: '1px solid rgba(242,193,78,.25)',
  boxShadow: '0 8px 24px rgba(0,0,0,.4)',
  textAlign: 'center',
};

const SignInScreen: React.FC<{ error: string | null; onSuccess: (c: CredentialResponse) => void }> = ({
  error,
  onSuccess,
}) => (
  <div style={shellStyle}>
    <div style={cardStyle}>
      <h1 style={{ fontFamily: 'var(--font-card-name)', fontSize: '28px', marginBottom: 'var(--spacing-component-sm)' }}>
        GGLTCG Admin
      </h1>
      <p style={{ fontSize: '13px', color: 'var(--ink-faint)', marginBottom: 'var(--spacing-component-lg)' }}>
        Sign in with an authorized Google account to continue.
      </p>
      {error && (
        <div
          style={{
            marginBottom: 'var(--spacing-component-md)',
            padding: 'var(--spacing-component-sm)',
            borderRadius: '6px',
            fontSize: '13px',
            background: 'rgba(224,113,107,.12)',
            border: '1px solid var(--danger)',
            color: 'var(--danger)',
          }}
        >
          {error}
        </div>
      )}
      <div className="flex justify-center">
        <GoogleLogin
          onSuccess={onSuccess}
          onError={() => {}}
          theme="filled_blue"
          size="large"
          text="signin_with"
          shape="rectangular"
        />
      </div>
    </div>
  </div>
);

const NotAuthorizedScreen: React.FC<{ onSignOut: () => void }> = ({ onSignOut }) => {
  const displayName = readStoredDisplayName();
  return (
    <div style={shellStyle}>
      <div style={cardStyle}>
        <h1 style={{ fontFamily: 'var(--font-card-name)', fontSize: '28px', marginBottom: 'var(--spacing-component-sm)' }}>
          Not Authorized
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--ink-muted)', marginBottom: 'var(--spacing-component-md)' }}>
          {displayName ? `Signed in as ${displayName}, but this` : 'This'} account isn't on the admin allowlist.
        </p>
        <button
          onClick={onSignOut}
          style={{
            background: 'none',
            border: '1px solid rgba(237,232,222,.25)',
            borderRadius: '6px',
            padding: '8px 16px',
            cursor: 'pointer',
            fontWeight: 700,
            color: 'var(--ink-text)',
          }}
        >
          Sign out and try a different account
        </button>
        <p style={{ marginTop: 'var(--spacing-component-md)', fontSize: '11px', color: 'var(--ink-faint)' }}>
          Note: signing out here also signs you out of the main game (same account, shared session).
        </p>
      </div>
    </div>
  );
};

const ErrorScreen: React.FC<{ onRetry: () => void }> = ({ onRetry }) => (
  <div style={shellStyle}>
    <div style={cardStyle}>
      <p style={{ marginBottom: 'var(--spacing-component-md)' }}>Couldn't reach the admin API.</p>
      <button
        onClick={onRetry}
        style={{
          background: 'none',
          border: '1px solid rgba(237,232,222,.25)',
          borderRadius: '6px',
          padding: '8px 16px',
          cursor: 'pointer',
          fontWeight: 700,
          color: 'var(--ink-text)',
        }}
      >
        Retry
      </button>
    </div>
  </div>
);

/** Renders once a token exists; resolves which of the three post-token states applies. */
const AuthorizedGate: React.FC<{ onSignOut: () => void }> = ({ onSignOut }) => {
  const summaryQuery = useSummary();

  if (summaryQuery.isLoading) {
    return (
      <div style={shellStyle}>
        <p style={{ color: 'var(--ink-faint)' }}>Checking admin access...</p>
      </div>
    );
  }

  if (summaryQuery.isError) {
    const status = (summaryQuery.error as { response?: { status?: number } })?.response?.status;
    if (status === 403) {
      return <NotAuthorizedScreen onSignOut={onSignOut} />;
    }
    if (status === 401) {
      // Token invalid/expired despite existing; onSignOut clears storage
      // AND flips the parent's hasToken flag, so it re-renders the
      // sign-in screen instead of leaving this branch showing nothing.
      onSignOut();
      return null;
    }
    return <ErrorScreen onRetry={() => summaryQuery.refetch()} />;
  }

  return <AdminApp />;
};

const AdminAuthGate: React.FC = () => {
  const [hasToken, setHasToken] = useState<boolean>(() => !!localStorage.getItem(TOKEN_KEY));
  const [loginError, setLoginError] = useState<string | null>(null);

  const handleSignOut = () => {
    clearStoredAuth();
    setHasToken(false);
  };

  const handleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) {
      setLoginError('Failed to get credentials from Google');
      return;
    }
    setLoginError(null);
    try {
      const authResponse = await authService.authenticateWithGoogle(credentialResponse.credential);
      localStorage.setItem(TOKEN_KEY, authResponse.jwt_token);
      localStorage.setItem(USER_KEY, JSON.stringify(authResponse.user));
      setHasToken(true);
    } catch {
      setLoginError('Sign-in failed. Please try again.');
    }
  };

  if (!hasToken) {
    return <SignInScreen error={loginError} onSuccess={handleSuccess} />;
  }

  return <AuthorizedGate onSignOut={handleSignOut} />;
};

export default AdminAuthGate;
