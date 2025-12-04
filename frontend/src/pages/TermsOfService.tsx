/**
 * Terms of Service page for GGLTCG.
 * 
 * Required for Google OAuth verification.
 */

import React from 'react';

interface TermsOfServiceProps {
  onBack: () => void;
}

export const TermsOfService: React.FC<TermsOfServiceProps> = ({ onBack }) => {
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
        <h1 className="text-4xl font-bold mb-8 text-game-highlight">Terms of Service</h1>
        
        <div className="space-y-8 text-gray-300 leading-relaxed">
          <section>
            <p className="text-sm text-gray-400 mb-6">
              <strong>Last Updated:</strong> December 4, 2025
            </p>
            <p className="mb-4">
              Welcome to GGLTCG (Googooland Trading Card Game). By accessing or using our game, you agree 
              to be bound by these Terms of Service. If you do not agree to these terms, please do not use GGLTCG.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">1. Acceptance of Terms</h2>
            <p className="mb-4">
              By creating an account or playing GGLTCG, you agree to:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>These Terms of Service</li>
              <li>Our Privacy Policy (see footer link)</li>
              <li>Follow the game rules and community guidelines</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">2. Description of Service</h2>
            <p className="mb-4">
              GGLTCG is a free-to-play online trading card game. The service includes:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Playing card game matches against AI or other players</li>
              <li>Creating and customizing decks</li>
              <li>Tracking statistics and leaderboard rankings</li>
              <li>Participating in online multiplayer matches</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">3. User Accounts</h2>
            
            <h3 className="text-xl font-semibold mb-3 text-gray-200">Account Creation</h3>
            <p className="mb-4">
              To play GGLTCG, you must sign in using your Google account. By signing in, you:
            </p>
            <ul className="list-disc list-inside space-y-2 mb-4 ml-4">
              <li>Confirm you have a valid Google account</li>
              <li>Authorize GGLTCG to access your basic Google profile information</li>
              <li>Agree to maintain the security of your Google account</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 text-gray-200">Account Responsibility</h3>
            <p className="mb-4">
              You are responsible for:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>All activity that occurs under your account</li>
              <li>Maintaining the confidentiality of your Google account credentials</li>
              <li>Notifying us immediately of any unauthorized use of your account</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">4. User Conduct</h2>
            <p className="mb-4">You agree NOT to:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Use offensive, inappropriate, or abusive display names</li>
              <li>Cheat, exploit bugs, or use automated tools to play the game</li>
              <li>Harass, threaten, or abuse other players</li>
              <li>Attempt to gain unauthorized access to the game servers or other accounts</li>
              <li>Reverse engineer, decompile, or disassemble the game</li>
              <li>Use the game for any illegal purposes</li>
              <li>Impersonate other players or GGLTCG staff</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">5. Display Names and Content</h2>
            <p className="mb-4">
              When setting a custom display name, you agree to:
            </p>
            <ul className="list-disc list-inside space-y-2 mb-4 ml-4">
              <li>Use appropriate language (no profanity, hate speech, or offensive terms)</li>
              <li>Not impersonate others</li>
              <li>Follow our character limits (1-50 characters)</li>
            </ul>
            <p className="mb-4">
              We reserve the right to change or remove any display name that violates these terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">6. Intellectual Property</h2>
            
            <h3 className="text-xl font-semibold mb-3 text-gray-200">Game Content</h3>
            <p className="mb-4">
              All content in GGLTCG, including but not limited to:
            </p>
            <ul className="list-disc list-inside space-y-2 mb-4 ml-4">
              <li>Card designs, names, and artwork</li>
              <li>Game rules and mechanics</li>
              <li>User interface and design</li>
              <li>Code and software</li>
            </ul>
            <p className="mb-4">
              ...is owned by or licensed to GGLTCG and protected by copyright and other intellectual property laws.
            </p>

            <h3 className="text-xl font-semibold mb-3 text-gray-200">Open Source</h3>
            <p className="mb-4">
              GGLTCG is an open-source project. The source code is available under the MIT License on{' '}
              <a 
                href="https://github.com/RegisCA/ggltcg" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-game-highlight hover:underline"
              >
                GitHub
              </a>.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">7. Game Rules and Balance</h2>
            <p className="mb-4">
              We reserve the right to:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Modify game rules, card effects, and game balance at any time</li>
              <li>Add, remove, or modify cards</li>
              <li>Update the game mechanics and features</li>
              <li>Perform maintenance that may temporarily interrupt service</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">8. Disclaimers and Limitations</h2>
            
            <h3 className="text-xl font-semibold mb-3 text-gray-200">Service "As Is"</h3>
            <p className="mb-4">
              GGLTCG is provided "as is" without warranties of any kind. We do not guarantee:
            </p>
            <ul className="list-disc list-inside space-y-2 mb-4 ml-4">
              <li>Uninterrupted or error-free service</li>
              <li>That the game will meet your expectations</li>
              <li>That bugs or errors will be corrected</li>
              <li>Permanent availability of the service</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 text-gray-200">Limitation of Liability</h3>
            <p className="mb-4">
              GGLTCG and its developers shall not be liable for:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Any indirect, incidental, or consequential damages</li>
              <li>Loss of data or game progress</li>
              <li>Service interruptions or downtime</li>
              <li>Any damages arising from use of the game</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">9. Termination</h2>
            
            <h3 className="text-xl font-semibold mb-3 text-gray-200">By You</h3>
            <p className="mb-4">
              You may stop using GGLTCG at any time. To delete your account and data, contact us at{' '}
              <a href="mailto:regiseloi+ggltcg@me.com" className="text-game-highlight hover:underline">
                regiseloi+ggltcg@me.com
              </a>.
            </p>

            <h3 className="text-xl font-semibold mb-3 text-gray-200">By Us</h3>
            <p className="mb-4">
              We reserve the right to suspend or terminate your access to GGLTCG at any time for:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Violation of these Terms of Service</li>
              <li>Abusive or disruptive behavior</li>
              <li>Cheating or exploitation</li>
              <li>Any reason we deem necessary to protect the service or community</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">10. No Monetary Transactions</h2>
            <p className="mb-4">
              GGLTCG is completely free to play. We do not:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Sell cards, packs, or in-game items</li>
              <li>Offer paid subscriptions or premium features</li>
              <li>Accept any form of payment from users</li>
            </ul>
            <p className="mt-4">
              All game content is available to all players equally.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">11. Changes to Terms</h2>
            <p className="mb-4">
              We may modify these Terms of Service at any time. Changes will be effective immediately upon 
              posting. Your continued use of GGLTCG after changes constitutes acceptance of the modified terms.
            </p>
            <p className="mb-4">
              Material changes will be indicated by updating the "Last Updated" date at the top of this page.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">12. Governing Law</h2>
            <p className="mb-4">
              These Terms of Service are governed by and construed in accordance with the laws of the 
              jurisdiction where the service is operated, without regard to conflict of law principles.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">13. Contact Information</h2>
            <p className="mb-4">
              If you have questions about these Terms of Service, please contact us:
            </p>
            <p className="mb-2">
              <strong>Email:</strong> <a 
                href="mailto:regiseloi+ggltcg@me.com" 
                className="text-game-highlight hover:underline"
              >
                regiseloi+ggltcg@me.com
              </a>
            </p>
            <p className="mb-2">
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

          <section className="mt-12 p-6 bg-gray-800 rounded-lg border-2 border-game-highlight">
            <h2 className="text-2xl font-bold mb-4 text-white">Acknowledgment</h2>
            <p className="mb-4">
              By using GGLTCG, you acknowledge that you have read and understood these Terms of Service 
              and agree to be bound by them.
            </p>
            <p className="text-gray-400 italic">
              Thank you for playing GGLTCG! We hope you enjoy the game.
            </p>
          </section>
        </div>

        {/* Footer Navigation */}
        <div className="mt-12 pt-8 border-t-2 border-gray-700">
          <button
            onClick={onBack}
            className="inline-block px-6 py-3 bg-game-highlight hover:bg-red-600 text-white font-bold rounded-lg transition-all"
          >
            Return to Game
          </button>
        </div>
      </main>
    </div>
  );
};
