/**
 * Lobby Home Component
 * Main entry point for multiplayer - Create or Join a game
 */

import { useState } from 'react';
import { Leaderboard } from './Leaderboard';
import { PlayerStats } from './PlayerStats';

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

  return (
    <div className="min-h-screen bg-game-bg flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-7xl font-bold mb-3 text-game-highlight">GGLTCG</h1>
          <p className="text-3xl text-gray-100 font-semibold">Choose Your Game Mode</p>
        </div>

        {/* Game Mode Options */}
        <div className="space-y-4">
          {/* Create Lobby */}
          <button
            onClick={onCreateLobby}
            onMouseEnter={() => setHoveredButton('create')}
            onMouseLeave={() => setHoveredButton(null)}
            className={`
              w-full p-6 rounded-lg border-4 transition-all
              ${hoveredButton === 'create'
                ? 'border-game-highlight bg-gray-700 scale-105'
                : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }
            `}
          >
            <div className="text-3xl mb-2 font-bold text-white">🎮 Create Game</div>
            <div className="text-xl text-gray-100 font-semibold">
              Host a new game and invite a friend
            </div>
            <div className="text-sm text-gray-300 mt-1">
              Get a 6-character code to share
            </div>
          </button>

          {/* Join Lobby */}
          <button
            onClick={onJoinLobby}
            onMouseEnter={() => setHoveredButton('join')}
            onMouseLeave={() => setHoveredButton(null)}
            className={`
              w-full p-6 rounded-lg border-4 transition-all
              ${hoveredButton === 'join'
                ? 'border-game-highlight bg-gray-700 scale-105'
                : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }
            `}
          >
            <div className="text-3xl mb-2 font-bold text-white">🔗 Join Game</div>
            <div className="text-xl text-gray-100 font-semibold">
              Enter a friend's game code
            </div>
            <div className="text-sm text-gray-300 mt-1">
              Connect to an existing lobby
            </div>
          </button>

          {/* Play vs AI */}
          <button
            onClick={() => onPlayVsAI(false)}
            onMouseEnter={() => setHoveredButton('ai')}
            onMouseLeave={() => setHoveredButton(null)}
            className={`
              w-full p-6 rounded-lg border-4 transition-all
              ${hoveredButton === 'ai'
                ? 'border-purple-500 bg-gray-700 scale-105'
                : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }
            `}
          >
            <div className="text-3xl mb-2 font-bold text-white">🤖 Play vs AI</div>
            <div className="text-xl text-gray-100 font-semibold">
              Practice against computer opponent
            </div>
            <div className="text-sm text-gray-300 mt-1">
              Single-player mode
            </div>
          </button>

          {/* Quick Play */}
          <button
            onClick={onQuickPlay}
            onMouseEnter={() => setHoveredButton('quick')}
            onMouseLeave={() => setHoveredButton(null)}
            className={`
              w-full p-6 rounded-lg border-4 transition-all
              ${hoveredButton === 'quick'
                ? 'border-orange-500 bg-gray-700 scale-105'
                : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }
            `}
          >
            <div className="text-3xl mb-2 font-bold text-white">⚡ Quick Play</div>
            <div className="text-xl text-gray-100 font-semibold">
              Jump straight into battle
            </div>
            <div className="text-sm text-gray-300 mt-1">
              Random decks, instant action!
            </div>
          </button>

          {/* Leaderboard Button */}
          <button
            onClick={() => setShowLeaderboard(true)}
            onMouseEnter={() => setHoveredButton('leaderboard')}
            onMouseLeave={() => setHoveredButton(null)}
            className={`
              w-full p-5 rounded-lg border-4 transition-all mt-2
              ${hoveredButton === 'leaderboard'
                ? 'border-yellow-500 bg-gray-700 scale-105'
                : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }
            `}
          >
            <div className="text-2xl mb-1 font-bold text-white">🏆 Leaderboard</div>
            <div className="text-lg text-gray-100 font-semibold">
              View top players and rankings
            </div>
          </button>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-gray-500 text-sm">
          <p>A trading card game where strategy meets imagination</p>
          <p className="mt-2">
            <button
              onClick={onShowPrivacyPolicy}
              className="text-blue-400 hover:underline mx-2"
            >
              Privacy Policy
            </button>
            •
            <button
              onClick={onShowTermsOfService}
              className="text-blue-400 hover:underline mx-2"
            >
              Terms of Service
            </button>
          </p>
        </div>
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
          onClose={() => setViewingPlayerId(null)}
        />
      )}
    </div>
  );
}
