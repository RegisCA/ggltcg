/**
 * Login page with Google OAuth integration.
 * 
 * Provides Google Sign-In button and handles authentication flow.
 */

import React from 'react';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';
import { authService } from '../api/authService';

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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-600 to-blue-600">
      <div className="bg-white p-8 rounded-lg shadow-2xl max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">GGLTCG</h1>
          <p className="text-gray-600">Googooland Trading Card Game</p>
        </div>

        <div className="mb-6 text-center">
          <h2 className="text-2xl font-semibold text-gray-700 mb-2">
            Welcome!
          </h2>
          <p className="text-gray-600">
            Sign in with your Google account to play
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        <div className="flex flex-col items-center mb-6">
          <div className="flex justify-center w-full">
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
        </div>

        {isLoading && (
          <div className="text-center text-gray-600">
            <p>Signing in...</p>
          </div>
        )}

        <div className="mt-8 text-center text-sm text-gray-500">
          <p>
            By signing in, you agree to our{' '}
            <button
              onClick={onShowTermsOfService}
              className="text-blue-600 hover:underline"
            >
              Terms of Service
            </button>
          </p>
          <p className="mt-1">
            and{' '}
            <button
              onClick={onShowPrivacyPolicy}
              className="text-blue-600 hover:underline"
            >
              Privacy Policy
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
