/**
 * Login page with Google OAuth integration.
 *
 * Provides Google Sign-In button, game branding, and authentication flow.
 * Restyled to Paper & Ink (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md) — no
 * mockup exists for this screen, so this applies the established language:
 * desk gradient background, Gochi Hand title, dark panel, gold accents.
 *
 * Decorative emoji removed per §8 (🎯⚡🤖📖); none of these are content-bearing
 * state badges (same call as VictoryScreen/LobbyHome).
 */

import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';
import { authService } from '../api/authService';
import { Footer } from './ui/Footer';
import { HowToPlay } from './HowToPlay';

interface LoginPageProps {
  onShowPrivacyPolicy?: () => void;
  onShowTermsOfService?: () => void;
}

const LoginPage: React.FC<LoginPageProps> = ({
  onShowPrivacyPolicy,
  onShowTermsOfService,
}) => {
  const { login } = useAuth();
  const [error, setError] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [showHowToPlay, setShowHowToPlay] = useState(false);

  const handleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) {
      setError('Failed to get credentials from Google');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Send Google token to our backend
      const authResponse = await authService.authenticateWithGoogle(
        credentialResponse.credential
      );

      // Store token and user in context
      login(authResponse.jwt_token, authResponse.user);

      // AuthContext update will trigger App to re-render and show GameApp
    } catch (err) {
      console.error('Authentication failed:', err);
      setError('Authentication failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleError = () => {
    setError('Google Sign-In failed. Please try again.');
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center"
      style={{
        padding: 'var(--spacing-component-md)',
        background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))',
        color: 'var(--ink-text)',
      }}
    >
      <div className="max-w-lg w-full">
        {/* Hero Section */}
        <div className="text-center" style={{ marginBottom: 'var(--spacing-component-xl)' }}>
          <h1
            style={{
              fontFamily: 'var(--font-card-name)',
              fontSize: 'clamp(48px, 10vw, 72px)',
              lineHeight: 1,
              color: 'var(--ink-text)',
              marginBottom: 'var(--spacing-component-sm)',
            }}
          >
            GGLTCG
          </h1>
          <p style={{ fontSize: 'clamp(16px, 3vw, 20px)', fontWeight: 700, color: 'var(--ink-muted)' }}>
            Googooland Trading Card Game
          </p>
        </div>

        {/* Game Description Card */}
        <div
          style={{
            padding: 'var(--spacing-component-lg)',
            marginBottom: 'var(--spacing-component-lg)',
            background: 'var(--color-panel)',
            borderRadius: '8px',
            border: '1px solid rgba(242,193,78,.25)',
            boxShadow: '0 8px 24px rgba(0,0,0,.4)',
          }}
        >
          <h2
            className="text-center"
            style={{
              fontFamily: 'var(--font-card-name)',
              fontSize: '26px',
              color: 'var(--ink-text)',
              marginBottom: 'var(--spacing-component-md)',
            }}
          >
            A Tactical Card Game
          </h2>

          <div
            className="text-center"
            style={{ marginBottom: 'var(--spacing-component-lg)', lineHeight: '1.6', color: 'var(--ink-muted)' }}
          >
            <p style={{ marginBottom: 'var(--spacing-component-sm)' }}>
              Build a 6-card deck from over 20 unique cards.
              Play <span style={{ color: 'var(--you)', fontWeight: 700 }}>Toys</span> and{' '}
              <span style={{ color: 'var(--them)', fontWeight: 700 }}>Actions</span> to outmaneuver your opponent.
            </p>
            <p>
              Win <span style={{ color: 'var(--gold)', fontWeight: 700 }}>Tussles</span> and
              break all their cards to claim victory!
            </p>
          </div>

          {/* Feature Pills */}
          <div
            className="flex flex-wrap justify-center"
            style={{ gap: 'var(--spacing-component-xs)', marginBottom: 'var(--spacing-component-lg)' }}
          >
            {['No Random Draws', 'Quick 1-5 min Games', 'Play vs AI or Friends'].map((label) => (
              <span
                key={label}
                style={{
                  fontSize: '12px',
                  fontWeight: 700,
                  padding: '4px 12px',
                  borderRadius: '999px',
                  background: 'rgba(237,232,222,.08)',
                  border: '1px solid rgba(237,232,222,.15)',
                  color: 'var(--ink-muted)',
                }}
              >
                {label}
              </span>
            ))}
          </div>

          {/* How to Play Button */}
          <div className="text-center" style={{ marginBottom: 'var(--spacing-component-md)' }}>
            <button
              onClick={() => setShowHowToPlay(true)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontWeight: 700,
                color: 'var(--you)',
                textDecoration: 'underline',
              }}
            >
              Learn How to Play
            </button>
          </div>

          {/* Sign In Section */}
          <div
            style={{
              paddingTop: 'var(--spacing-component-lg)',
              borderTop: '1px solid rgba(237,232,222,.15)',
            }}
          >
            <p
              className="text-center"
              style={{ marginBottom: 'var(--spacing-component-md)', fontSize: '13px', color: 'var(--ink-faint)' }}
            >
              Sign in to track your stats and play online
            </p>

            {error && (
              <div
                className="text-center"
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
                onSuccess={handleSuccess}
                onError={handleError}
                useOneTap
                theme="filled_blue"
                size="large"
                text="signin_with"
                shape="rectangular"
              />
            </div>

            {isLoading && (
              <div
                className="text-center"
                style={{ marginTop: 'var(--spacing-component-sm)', fontSize: '13px', color: 'var(--ink-faint)' }}
              >
                <p>Signing in...</p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <Footer
          showTagline={false}
          onShowPrivacyPolicy={onShowPrivacyPolicy}
          onShowTermsOfService={onShowTermsOfService}
        />
        <p
          className="text-center"
          style={{ marginTop: 'var(--spacing-component-xs)', fontSize: '11px', color: 'var(--ink-faint)' }}
        >
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>

      {/* How to Play Modal */}
      <HowToPlay isOpen={showHowToPlay} onClose={() => setShowHowToPlay(false)} />
    </div>
  );
};

export default LoginPage;
