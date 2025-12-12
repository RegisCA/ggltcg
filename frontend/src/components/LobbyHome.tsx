/**
 * Lobby Home Component
 * Main entry point for multiplayer - Create or Join a game
 */

import { useState } from 'react';
import { Leaderboard } from './Leaderboard';
import { PlayerStats } from './PlayerStats';
import { Footer } from './ui/Footer';
import { HowToPlay } from './HowToPlay';

interface LobbyHomeProps {
  onCreateLobby: () => void;
  onJoinLobby: () => void;
  onPlayVsAI: (hiddenMode: boolean) => void;
  onQuickPlay: () => void;
  onShowPrivacyPolicy?: () => void;
  onShowTermsOfService?: () => void;
}

export function LobbyHome({ 
  onCreateLobby, 
  onJoinLobby, 
  onPlayVsAI, 
  onQuickPlay,
  onShowPrivacyPolicy,
  onShowTermsOfService
}: LobbyHomeProps) {
  const [hoveredButton, setHoveredButton] = useState<string | null>(null);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [viewingPlayerId, setViewingPlayerId] = useState<string | null>(null);
  const [showHowToPlay, setShowHowToPlay] = useState(false);

  return (
    <div className="min-h-screen bg-game-bg flex items-center justify-center" style={{ padding: 'var(--spacing-component-md)' }}>
      <div className="max-w-2xl w-full">
        {/* Title */}
        <div className="text-center" style={{ marginBottom: 'var(--spacing-component-xl)' }}>
          <h1 
            className="text-7xl font-bold text-game-highlight" 
            style={{ 
              marginBottom: 'var(--spacing-component-sm)',
              fontWeight: 700,
              textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
            }}
          >
            GGLTCG
          </h1>
          <p className="text-3xl text-gray-100 font-semibold">Choose Your Game Mode</p>
        </div>

        {/* Game Mode Options */}
        <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
          {/* Create Lobby */}
          <button
            onClick={onCreateLobby}
            onMouseEnter={() => setHoveredButton('create')}
            onMouseLeave={() => setHoveredButton(null)}
            className={`
              w-full rounded-lg border-4 transition-all
              ${hoveredButton === 'create'
                ? 'border-game-highlight bg-gray-700 scale-105'
                : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }
            `}
            style={{ padding: 'var(--spacing-component-lg)' }}
          >
            <div className="text-3xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-xs)' }}>🎮 Create Game</div>
            <div className="text-xl text-gray-100 font-semibold">
              Host a new game and invite a friend
            </div>
            <div className="text-sm text-gray-300" style={{ marginTop: '4px' }}>
              Get a 6-character code to share
            </div>
          </button>

          {/* Join Lobby */}
          <button
            onClick={onJoinLobby}
            onMouseEnter={() => setHoveredButton('join')}
            onMouseLeave={() => setHoveredButton(null)}
            className={`
              w-full rounded-lg border-4 transition-all
              ${hoveredButton === 'join'
                ? 'border-game-highlight bg-gray-700 scale-105'
                : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }
            `}
            style={{ padding: 'var(--spacing-component-lg)' }}
          >
            <div className="text-3xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-xs)' }}>🔗 Join Game</div>
            <div className="text-xl text-gray-100 font-semibold">
              Enter a friend's game code
            </div>
            <div className="text-sm text-gray-300" style={{ marginTop: '4px' }}>
              Connect to an existing lobby
            </div>
          </button>

          {/* Play vs AI */}
          <button
            onClick={() => onPlayVsAI(false)}
            onMouseEnter={() => setHoveredButton('ai')}
            onMouseLeave={() => setHoveredButton(null)}
            className={`
              w-full rounded-lg border-4 transition-all
              ${hoveredButton === 'ai'
                ? 'border-purple-500 bg-gray-700 scale-105'
                : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }
            `}
            style={{ padding: 'var(--spacing-component-lg)' }}
          >
            <div className="text-3xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-xs)' }}>🤖 Play vs AI</div>
            <div className="text-xl text-gray-100 font-semibold">
              Practice against computer opponent
            </div>
            <div className="text-sm text-gray-300" style={{ marginTop: '4px' }}>
              Single-player mode
            </div>
          </button>

          {/* Quick Play */}
          <button
            onClick={onQuickPlay}
            onMouseEnter={() => setHoveredButton('quick')}
            onMouseLeave={() => setHoveredButton(null)}
            className={`
              w-full rounded-lg border-4 transition-all
              ${hoveredButton === 'quick'
                ? 'border-orange-500 bg-gray-700 scale-105'
                : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }
            `}
            style={{ padding: 'var(--spacing-component-lg)' }}
          >
            <div className="text-3xl font-bold text-white" style={{ marginBottom: 'var(--spacing-component-xs)' }}>⚡ Quick Play</div>
            <div className="text-xl text-gray-100 font-semibold">
              Jump straight into battle
            </div>
            <div className="text-sm text-gray-300" style={{ marginTop: '4px' }}>
              Random decks, instant action!
            </div>
          </button>

          {/* Secondary buttons row */}
          <div className="flex" style={{ gap: 'var(--spacing-component-sm)', marginTop: 'var(--spacing-component-xs)' }}>
            {/* Leaderboard Button */}
            <button
              onClick={() => setShowLeaderboard(true)}
              onMouseEnter={() => setHoveredButton('leaderboard')}
              onMouseLeave={() => setHoveredButton(null)}
              className={`
                flex-1 rounded-lg border-4 transition-all
                ${hoveredButton === 'leaderboard'
                  ? 'border-yellow-500 bg-gray-700 scale-105'
                  : 'border-gray-600 bg-gray-800 hover:border-gray-500'
                }
              `}
              style={{ padding: 'var(--spacing-component-md)' }}
            >
              <div className="text-2xl font-bold text-white" style={{ marginBottom: '4px' }}>🏆 Leaderboard</div>
              <div className="text-sm text-gray-300">
                View top players
              </div>
            </button>

            {/* How to Play Button */}
            <button
              onClick={() => setShowHowToPlay(true)}
              onMouseEnter={() => setHoveredButton('howtoplay')}
              onMouseLeave={() => setHoveredButton(null)}
              className={`
                flex-1 rounded-lg border-4 transition-all
                ${hoveredButton === 'howtoplay'
                  ? 'border-blue-500 bg-gray-700 scale-105'
                  : 'border-gray-600 bg-gray-800 hover:border-gray-500'
                }
              `}
              style={{ padding: 'var(--spacing-component-md)' }}
            >
              <div className="text-2xl font-bold text-white" style={{ marginBottom: '4px' }}>📖 How to Play</div>
              <div className="text-sm text-gray-300">
                Learn the rules
              </div>
            </button>
          </div>
        </div>

        {/* Footer */}
        <Footer
          variant="light"
          showTagline={true}
          onShowPrivacyPolicy={onShowPrivacyPolicy}
          onShowTermsOfService={onShowTermsOfService}
        />
      </div>

      {/* Leaderboard Modal */}
      {showLeaderboard && (
        <Leaderboard
          onClose={() => setShowLeaderboard(false)}
          onViewPlayer={(playerId) => {
            setShowLeaderboard(false);
            setViewingPlayerId(playerId);
          }}
        />
      )}

      {/* Player Stats Modal */}
      {viewingPlayerId && (
        <PlayerStats
          playerId={viewingPlayerId}
          onClose={() => {
            setViewingPlayerId(null);
            setShowLeaderboard(true);
          }}
        />
      )}

      {/* How to Play Modal */}
      <HowToPlay isOpen={showHowToPlay} onClose={() => setShowHowToPlay(false)} />
    </div>
  );
}
