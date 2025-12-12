/**
 * Login page with Google OAuth integration.
 * 
 * Provides Google Sign-In button, game branding, and authentication flow.
 * Enhanced with game description to help new players understand what they're signing up for.
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
  onShowTermsOfService 
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
    <div className="min-h-screen flex flex-col items-center justify-center bg-game-bg" style={{ padding: 'var(--spacing-component-md)' }}>
      <div className="max-w-lg w-full">
        {/* Hero Section */}
        <div className="text-center" style={{ marginBottom: 'var(--spacing-component-xl)' }}>
          <h1 
            className="text-6xl sm:text-7xl font-bold text-game-highlight"
            style={{ 
              marginBottom: 'var(--spacing-component-sm)',
              fontWeight: 700,
              textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
            }}
          >
            GGLTCG
          </h1>
          <p className="text-xl text-gray-300">Googooland Trading Card Game</p>
        </div>

        {/* Game Description Card */}
        <div 
          className="bg-game-card rounded-lg border border-gray-700"
          style={{ padding: 'var(--spacing-component-lg)', marginBottom: 'var(--spacing-component-lg)' }}
        >
          <h2 
            className="text-2xl font-bold text-white text-center"
            style={{ marginBottom: 'var(--spacing-component-md)' }}
          >
            A Tactical Card Game
          </h2>
          
          <div className="text-gray-300 text-center" style={{ marginBottom: 'var(--spacing-component-lg)', lineHeight: '1.6' }}>
            <p style={{ marginBottom: 'var(--spacing-component-sm)' }}>
              Build a 6-card deck from over 20 unique cards. 
              Play <span className="text-blue-400 font-semibold">Toys</span> and <span className="text-purple-400 font-semibold">Actions</span> to outmaneuver your opponent.
            </p>
            <p>
              Win <span className="text-game-highlight font-semibold">Tussles</span> and 
              sleep all their cards to claim victory!
            </p>
          </div>

          {/* Feature Pills */}
          <div className="flex flex-wrap justify-center" style={{ gap: 'var(--spacing-component-xs)', marginBottom: 'var(--spacing-component-lg)' }}>
            <span className="bg-purple-600/30 text-purple-300 text-sm rounded-full" style={{ padding: '4px 12px' }}>
              🎯 No Random Draws
            </span>
            <span className="bg-blue-600/30 text-blue-300 text-sm rounded-full" style={{ padding: '4px 12px' }}>
              ⚡ Quick 1-5 min Games
            </span>
            <span className="bg-green-600/30 text-green-300 text-sm rounded-full" style={{ padding: '4px 12px' }}>
              🤖 Play vs AI or Friends
            </span>
          </div>

          {/* How to Play Button */}
          <div className="text-center" style={{ marginBottom: 'var(--spacing-component-md)' }}>
            <button
              onClick={() => setShowHowToPlay(true)}
              className="text-blue-400 hover:text-blue-300 hover:underline font-medium"
            >
              📖 Learn How to Play
            </button>
          </div>

          {/* Sign In Section */}
          <div 
            className="border-t border-gray-600"
            style={{ paddingTop: 'var(--spacing-component-lg)' }}
          >
            <p className="text-center text-gray-400 text-sm" style={{ marginBottom: 'var(--spacing-component-md)' }}>
              Sign in to track your stats and play online
            </p>

            {error && (
              <div 
                className="bg-red-900/50 border border-red-500 text-red-300 rounded text-sm text-center"
                style={{ marginBottom: 'var(--spacing-component-md)', padding: 'var(--spacing-component-sm)' }}
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
              <div className="text-center text-gray-400 text-sm" style={{ marginTop: 'var(--spacing-component-sm)' }}>
                <p>Signing in...</p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <Footer
          variant="light"
          showTagline={false}
          onShowPrivacyPolicy={onShowPrivacyPolicy}
          onShowTermsOfService={onShowTermsOfService}
        />
        <p className="text-center text-xs text-gray-500" style={{ marginTop: 'var(--spacing-component-xs)' }}>
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>

      {/* How to Play Modal */}
      <HowToPlay isOpen={showHowToPlay} onClose={() => setShowHowToPlay(false)} />
    </div>
  );
};

export default LoginPage;
