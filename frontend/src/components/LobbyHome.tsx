/**
 * Lobby Home Component
 * Main entry point for multiplayer - Create or Join a game
 */

import { useState } from 'react';

interface LobbyHomeProps {
  onCreateLobby: () => void;
  onJoinLobby: () => void;
  onPlayVsAI: (hiddenMode: boolean) => void;
}

export function LobbyHome({ onCreateLobby, onJoinLobby, onPlayVsAI }: LobbyHomeProps) {
  const [hoveredButton, setHoveredButton] = useState<string | null>(null);
  const [hiddenCardsMode, setHiddenCardsMode] = useState(false);

  return (
    <div className="min-h-screen bg-game-bg flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* Title */}
        <div className="text-center mb-12">
          <h1 className="text-7xl font-bold mb-4 text-game-highlight">GGLTCG</h1>
          <p className="text-3xl text-gray-100 font-semibold">Choose Your Game Mode</p>
        </div>

        {/* Game Mode Options */}
        <div className="space-y-6">
          {/* Create Lobby */}
          <button
            onClick={onCreateLobby}
            onMouseEnter={() => setHoveredButton('create')}
            onMouseLeave={() => setHoveredButton(null)}
            className={`
              w-full p-8 rounded-lg border-4 transition-all
              ${hoveredButton === 'create'
                ? 'border-game-highlight bg-gray-700 scale-105'
                : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }
            `}
          >
            <div className="text-4xl mb-3 font-bold text-gray-900">🎮 Create Game</div>
            <div className="text-2xl text-gray-800 font-semibold">
              Host a new game and invite a friend
            </div>
            <div className="text-base text-gray-700 mt-2">
              Get a 6-character code to share
            </div>
          </button>

          {/* Join Lobby */}
          <button
            onClick={onJoinLobby}
            onMouseEnter={() => setHoveredButton('join')}
            onMouseLeave={() => setHoveredButton(null)}
            className={`
              w-full p-8 rounded-lg border-4 transition-all
              ${hoveredButton === 'join'
                ? 'border-game-highlight bg-gray-700 scale-105'
                : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }
            `}
          >
            <div className="text-4xl mb-3 font-bold text-gray-900">🔗 Join Game</div>
            <div className="text-2xl text-gray-800 font-semibold">
              Enter a friend's game code
            </div>
            <div className="text-base text-gray-700 mt-2">
              Connect to an existing lobby
            </div>
          </button>

          {/* Play vs AI */}
          <div className="space-y-3">
            <button
              onClick={() => onPlayVsAI(hiddenCardsMode)}
              onMouseEnter={() => setHoveredButton('ai')}
              onMouseLeave={() => setHoveredButton(null)}
              className={`
                w-full p-8 rounded-lg border-4 transition-all
                ${hoveredButton === 'ai'
                  ? 'border-purple-500 bg-gray-700 scale-105'
                  : 'border-gray-600 bg-gray-800 hover:border-gray-500'
                }
              `}
            >
              <div className="text-4xl mb-3 font-bold text-gray-900">🤖 Play vs AI</div>
              <div className="text-2xl text-gray-800 font-semibold">
                Practice against computer opponent
              </div>
              <div className="text-base text-gray-700 mt-2">
                Single-player mode
              </div>
            </button>

            {/* Hidden Cards Toggle */}
            <div 
              className="flex items-center justify-center gap-3 p-3 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors"
              onClick={() => setHiddenCardsMode(!hiddenCardsMode)}
            >
              <div className={`
                w-12 h-6 rounded-full transition-colors relative
                ${hiddenCardsMode ? 'bg-purple-600' : 'bg-gray-600'}
              `}>
                <div className={`
                  absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform
                  ${hiddenCardsMode ? 'translate-x-6' : 'translate-x-0.5'}
                `} />
              </div>
              <span className="text-lg">
                🎭 <strong>Challenge Mode:</strong> Hidden cards during deck selection
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-12 text-gray-500 text-sm">
          <p>A trading card game where strategy meets imagination</p>
        </div>
      </div>
    </div>
  );
}
