/**
 * Privacy Policy page for GGLTCG.
 * 
 * Required for Google OAuth verification.
 */

import React from 'react';

interface PrivacyPolicyProps {
  onBack: () => void;
}

export const PrivacyPolicy: React.FC<PrivacyPolicyProps> = ({ onBack }) => {
  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      {/* Header */}
      <header className="bg-gray-800 border-b-4 border-game-highlight" style={{ padding: 'var(--spacing-component-lg)' }}>
        <div className="container mx-auto" style={{ padding: '0 var(--spacing-component-md)' }}>
          <button
            onClick={onBack}
            className="text-2xl font-bold text-game-highlight hover:text-red-400 transition-colors"
          >
            ← Back to GGLTCG
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto max-w-4xl" style={{ padding: 'var(--spacing-component-xl) var(--spacing-component-md)' }}>
        <h1 className="text-4xl font-bold text-game-highlight" style={{ marginBottom: 'var(--spacing-component-xl)' }}>Privacy Policy</h1>
        
        <div className="text-gray-300 leading-relaxed" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-component-xl)' }}>
          <section>
            <p className="text-sm text-gray-400" style={{ marginBottom: 'var(--spacing-component-lg)' }}>
              <strong>Last Updated:</strong> December 4, 2025
            </p>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              Welcome to GGLTCG (Googooland Trading Card Game). This Privacy Policy explains how we collect, 
              use, and protect your information when you use our game.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-md)' }}>Information We Collect</h2>
            
            <h3 className="text-xl font-semibold text-gray-200" style={{ marginBottom: 'var(--spacing-component-sm)' }}>Google OAuth Information</h3>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              When you sign in with Google, we collect:
            </p>
            <ul className="list-disc list-inside space-y-2 mb-4 ml-4">
              <li>Your Google ID (a unique identifier)</li>
              <li>Your first name (for display purposes)</li>
              <li>Your email address (for account verification only)</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-200" style={{ marginBottom: 'var(--spacing-component-sm)' }}>Game Data</h3>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              While playing GGLTCG, we store:
            </p>
            <ul className="list-disc list-inside" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-component-xs)', marginBottom: 'var(--spacing-component-md)', marginLeft: 'var(--spacing-component-md)' }}>
              <li>Your custom display name (if you set one)</li>
              <li>Your game statistics (wins, losses, games played)</li>
              <li>Your game history and match results</li>
              <li>Deck configurations you create</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-md)' }}>How We Use Your Information</h2>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>We use your information to:</p>
            <ul className="list-disc list-inside" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-component-xs)', marginLeft: 'var(--spacing-component-md)' }}>
              <li>Authenticate your account and maintain your session</li>
              <li>Display your name to other players during games</li>
              <li>Track your game statistics and leaderboard rankings</li>
              <li>Provide matchmaking for multiplayer games</li>
              <li>Improve the game experience</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-md)' }}>Data Storage and Security</h2>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              Your data is stored securely in our database and protected using industry-standard practices:
            </p>
            <ul className="list-disc list-inside" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-component-xs)', marginBottom: 'var(--spacing-component-md)', marginLeft: 'var(--spacing-component-md)' }}>
              <li>All connections use HTTPS encryption</li>
              <li>Authentication tokens are securely generated and validated</li>
              <li>We do not store your Google password</li>
              <li>Database access is restricted and monitored</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-md)' }}>Data Sharing</h2>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              <strong>We do not sell, rent, or share your personal information with third parties.</strong>
            </p>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              The only information visible to other players is:
            </p>
            <ul className="list-disc list-inside" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-component-xs)', marginLeft: 'var(--spacing-component-md)' }}>
              <li>Your display name (either your first name or custom display name)</li>
              <li>Your game statistics on the leaderboard</li>
            </ul>
            <p style={{ marginTop: 'var(--spacing-component-md)' }}>
              See our{' '}
              <button
                onClick={() => window.open('https://github.com/RegisCA/ggltcg', '_blank')}
                className="text-game-highlight hover:underline"
              >
                Terms of Service
              </button>
              {' '}for more information about acceptable use.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-md)' }}>Third-Party Services</h2>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              GGLTCG uses the following third-party services:
            </p>
            <ul className="list-disc list-inside" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-component-xs)', marginBottom: 'var(--spacing-component-md)', marginLeft: 'var(--spacing-component-md)' }}>
              <li>
                <strong>Google OAuth 2.0:</strong> For secure authentication. Google's privacy policy 
                applies to their service: <a 
                  href="https://policies.google.com/privacy" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-game-highlight hover:underline"
                >
                  Google Privacy Policy
                </a>
              </li>
              <li>
                <strong>Vercel:</strong> Frontend hosting (privacy policy: <a 
                  href="https://vercel.com/legal/privacy-policy" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-game-highlight hover:underline"
                >
                  Vercel Privacy Policy
                </a>)
              </li>
              <li>
                <strong>Render:</strong> Backend hosting (privacy policy: <a 
                  href="https://render.com/privacy" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-game-highlight hover:underline"
                >
                  Render Privacy Policy
                </a>)
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-md)' }}>Your Rights</h2>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>You have the right to:</p>
            <ul className="list-disc list-inside" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-component-xs)', marginBottom: 'var(--spacing-component-md)', marginLeft: 'var(--spacing-component-md)' }}>
              <li>Update your display name at any time</li>
              <li>Request deletion of your account and associated data</li>
              <li>Revoke GGLTCG's access to your Google account at any time through your Google Account settings</li>
              <li>Request a copy of your data</li>
            </ul>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              To exercise these rights, please contact us at: <a 
                href="mailto:regiseloi+ggltcg@me.com" 
                className="text-game-highlight hover:underline"
              >
                regiseloi+ggltcg@me.com
              </a>
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-md)' }}>Children's Privacy</h2>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              GGLTCG is intended for general audiences. We do not knowingly collect personal information 
              from children under 13. If you are a parent or guardian and believe your child has provided 
              us with personal information, please contact us.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-md)' }}>Cookies and Local Storage</h2>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              GGLTCG uses browser local storage to:
            </p>
            <ul className="list-disc list-inside" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-component-xs)', marginLeft: 'var(--spacing-component-md)' }}>
              <li>Store your authentication token (keeps you logged in)</li>
              <li>Remember your user preferences</li>
            </ul>
            <p style={{ marginTop: 'var(--spacing-component-md)' }}>
              You can clear this data at any time through your browser settings, but you will be logged out.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-md)' }}>Changes to This Policy</h2>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              We may update this Privacy Policy from time to time. We will notify you of any changes by 
              updating the "Last Updated" date at the top of this policy. Your continued use of GGLTCG 
              after any changes constitutes acceptance of the updated policy.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-md)' }}>Contact Us</h2>
            <p style={{ marginBottom: 'var(--spacing-component-md)' }}>
              If you have any questions about this Privacy Policy or our data practices, please contact us:
            </p>
            <p style={{ marginBottom: 'var(--spacing-component-xs)' }}>
              <strong>Email:</strong> <a 
                href="mailto:regiseloi+ggltcg@me.com" 
                className="text-game-highlight hover:underline"
              >
                regiseloi+ggltcg@me.com
              </a>
            </p>
            <p style={{ marginBottom: 'var(--spacing-component-xs)' }}>
              <strong>Project:</strong> <a 
                href="https://github.com/RegisCA/ggltcg" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-game-highlight hover:underline"
              >
                GitHub Repository
              </a>
            </p>
          </section>
        </div>

        {/* Footer Navigation */}
        <div className="border-t-2 border-gray-700" style={{ marginTop: 'calc(var(--spacing-component-xl) * 1.5)', paddingTop: 'var(--spacing-component-xl)' }}>
          <button
            onClick={onBack}
            className="inline-block bg-game-highlight hover:bg-red-600 text-white font-bold rounded-lg transition-all"
            style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-lg)' }}
          >
            Return to Game
          </button>
        </div>
      </main>
    </div>
  );
};
