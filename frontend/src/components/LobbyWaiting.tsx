/**
 * Lobby Waiting Component
 * Waiting room showing game code, players, and deck selection status
 */

import { useState, useEffect } from 'react';
import { getLobbyStatus, startLobbyGame } from '../api/gameService';
import { DeckSelection } from './DeckSelection';

interface LobbyWaitingProps {
  gameId: string;
  gameCode: string;
  currentPlayerId: 'player1' | 'player2';
  currentPlayerName: string;
  otherPlayerName: string | null;
  onGameStarted: (gameId: string, firstPlayerId: string) => void;
  onBack: () => void;
}

type WaitingPhase = 'waiting-for-player' | 'deck-selection' | 'waiting-for-decks' | 'starting';

export function LobbyWaiting({
  gameId,
  gameCode,
  currentPlayerId,
  currentPlayerName,
  otherPlayerName: initialOtherPlayerName,
  onGameStarted,
  onBack,
}: LobbyWaitingProps) {
  const [phase, setPhase] = useState<WaitingPhase>(
    initialOtherPlayerName ? 'deck-selection' : 'waiting-for-player'
  );
  const [otherPlayerName, setOtherPlayerName] = useState<string | null>(initialOtherPlayerName);
  const [currentPlayerReady, setCurrentPlayerReady] = useState(false);
  const [otherPlayerReady, setOtherPlayerReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState(false);

  // Poll for lobby status when waiting for player 2 or waiting for deck submissions
  useEffect(() => {
    if (phase !== 'waiting-for-player' && phase !== 'waiting-for-decks') {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const status = await getLobbyStatus(gameCode);

        // Player 2 joined
        if (phase === 'waiting-for-player' && status.player2_name) {
          setOtherPlayerName(status.player2_name);
          setPhase('deck-selection');
        }

        // Check if both players are ready (other player submitted deck)
        if (phase === 'waiting-for-decks' && status.ready_to_start) {
          setOtherPlayerReady(true);
          // The game will start automatically - no need to call start again
          // Just wait for the status to become 'active' and poll game state
          setPhase('starting');
        }
      } catch (err) {
        console.error('Failed to poll lobby status:', err);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [gameCode, phase]);

  // When both players ready and status is 'starting', poll for game state
  useEffect(() => {
    if (phase !== 'starting') {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const status = await getLobbyStatus(gameCode);
        
        // Check if game has started by attempting to get game state
        // The game_state should be populated when status is 'active'
        if (status.ready_to_start) {
          // Try to get first_player_id from start response
          // Since we already submitted, we need to check if the game is actually active
          // For now, just navigate - the GameBoard will handle loading the state
          onGameStarted(gameId, ''); // Will be determined by game state
        }
      } catch (err) {
        console.error('Failed to check game start:', err);
      }
    }, 1000); // Poll more frequently when starting

    return () => clearInterval(pollInterval);
  }, [phase, gameCode, gameId, onGameStarted]);

  const handleCopyCode = () => {
    navigator.clipboard.writeText(gameCode);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleDeckSelected = async (deck: string[]) => {
    setError(null);

    try {
      const response = await startLobbyGame(gameCode, {
        player_id: currentPlayerId,
        deck,
      });

      setCurrentPlayerReady(true);

      // Check if game is ready to start (both players submitted)
      if (response.status === 'active' && response.first_player_id) {
        // Game started immediately
        onGameStarted(gameId, response.first_player_id);
      } else {
        // Wait for other player
        setPhase('waiting-for-decks');
      }
    } catch (err: any) {
      console.error('Failed to submit deck:', err);
      setError(err.response?.data?.detail || 'Failed to submit deck. Please try again.');
    }
  };

  // Deck selection phase
  if (phase === 'deck-selection' && !currentPlayerReady) {
    return (
      <div>
        {/* Header with game code and back button */}
        <div className="bg-gray-800 border-b-2 border-gray-600 p-4">
          <div className="max-w-7xl mx-auto flex justify-between items-center">
            <button
              onClick={onBack}
              className="text-gray-400 hover:text-game-highlight transition-colors flex items-center gap-2"
            >
              <span>←</span> Leave Lobby
            </button>

            <div className="text-center">
              <div className="text-sm text-gray-400 mb-1">Game Code</div>
              <button
                onClick={handleCopyCode}
                className="font-mono text-2xl font-bold text-game-highlight hover:text-red-400 transition-colors tracking-widest"
                title="Click to copy"
              >
                {gameCode} {copiedCode ? '✓' : '📋'}
              </button>
            </div>

            <div className="w-24"></div> {/* Spacer for centering */}
          </div>
        </div>

        {/* Players info banner */}
        <div className="bg-purple-900/20 border-b-2 border-purple-500/50 p-3">
          <div className="max-w-7xl mx-auto flex justify-center gap-8 text-center">
            <div>
              <div className="text-sm text-gray-400">Player 1</div>
              <div className="font-bold text-lg">{currentPlayerId === 'player1' ? currentPlayerName : otherPlayerName} {currentPlayerId === 'player1' && '(You)'}</div>
            </div>
            <div className="text-2xl text-gray-600">vs</div>
            <div>
              <div className="text-sm text-gray-400">Player 2</div>
              <div className="font-bold text-lg">{currentPlayerId === 'player2' ? currentPlayerName : otherPlayerName} {currentPlayerId === 'player2' && '(You)'}</div>
            </div>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="bg-red-900/30 border-2 border-red-500 rounded p-4 max-w-2xl mx-auto mt-4">
            <div className="text-red-200">{error}</div>
          </div>
        )}

        {/* Deck Selection */}
        <DeckSelection
          playerName={currentPlayerName}
          onDeckSelected={handleDeckSelected}
        />
      </div>
    );
  }

  // Waiting room display
  return (
    <div className="min-h-screen bg-game-bg flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* Back Button */}
        <button
          onClick={onBack}
          className="mb-8 text-xl text-gray-400 hover:text-game-highlight transition-colors flex items-center gap-2 font-semibold"
        >
          <span className="text-2xl">←</span> Leave Lobby
        </button>

        {/* Game Code Display */}
        <div className="bg-gray-800 rounded-lg p-8 border-2 border-gray-600 mb-6">
          <div className="text-center">
            <div className="text-lg text-gray-300 mb-3 font-semibold">Share this code with your friend:</div>
            <button
              onClick={handleCopyCode}
              className="font-mono text-6xl font-bold text-game-highlight hover:text-red-400 transition-colors tracking-widest"
              title="Click to copy"
            >
              {gameCode}
            </button>
            <div className="text-lg text-gray-300 mt-3 font-semibold">
              {copiedCode ? '✅ Copied to clipboard!' : '📋 Click to copy'}
            </div>
          </div>
        </div>

        {/* Players Status */}
        <div className="bg-gray-800 rounded-lg p-8 border-2 border-gray-600 mb-6">
          <h2 className="text-2xl font-bold mb-6 text-center">Players</h2>
          
          <div className="space-y-4">
            {/* Player 1 */}
            <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="text-3xl">🎮</div>
                <div>
                  <div className="font-bold text-lg">
                    {currentPlayerId === 'player1' ? currentPlayerName : otherPlayerName}
                    {currentPlayerId === 'player1' && <span className="text-game-highlight ml-2">(You)</span>}
                  </div>
                  <div className="text-sm text-gray-400">Player 1</div>
                </div>
              </div>
              <div>
                {currentPlayerId === 'player1' && currentPlayerReady && (
                  <span className="text-green-400 font-semibold">✓ Deck Ready</span>
                )}
                {currentPlayerId === 'player2' && otherPlayerReady && (
                  <span className="text-green-400 font-semibold">✓ Deck Ready</span>
                )}
              </div>
            </div>

            {/* VS Divider */}
            <div className="text-center text-gray-500 font-bold">VS</div>

            {/* Player 2 */}
            <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="text-3xl">🎮</div>
                <div>
                  <div className="font-bold text-lg">
                    {otherPlayerName ? (
                      <>
                        {currentPlayerId === 'player2' ? currentPlayerName : otherPlayerName}
                        {currentPlayerId === 'player2' && <span className="text-game-highlight ml-2">(You)</span>}
                      </>
                    ) : (
                      <span className="text-gray-500">Waiting for player...</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-400">Player 2</div>
                </div>
              </div>
              <div>
                {currentPlayerId === 'player2' && currentPlayerReady && (
                  <span className="text-green-400 font-semibold">✓ Deck Ready</span>
                )}
                {currentPlayerId === 'player1' && otherPlayerReady && (
                  <span className="text-green-400 font-semibold">✓ Deck Ready</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Status Message */}
        <div className="text-center">
          {phase === 'waiting-for-player' && (
            <div className="text-2xl text-gray-200 font-semibold">
              <div className="mb-3">⏳ Waiting for player 2 to join...</div>
              <div className="text-lg text-gray-300">Share the game code above</div>
            </div>
          )}
          {phase === 'waiting-for-decks' && (
            <div className="text-2xl text-gray-200 font-semibold">
              <div className="mb-3">⏳ Waiting for {currentPlayerId === 'player1' ? 'Player 2' : 'Player 1'} to select their deck...</div>
              <div className="text-lg text-green-400">✅ Your deck is ready!</div>
            </div>
          )}
          {phase === 'starting' && (
            <div className="text-2xl text-game-highlight font-bold">
              <div className="mb-3">🎮 Starting game...</div>
              <div className="text-lg text-gray-300">Get ready to play!</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
