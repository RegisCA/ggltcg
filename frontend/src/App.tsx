/**
 * Main App Component
 * Handles game flow: deck selection → game → game over
 */

import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DeckSelection } from './components/DeckSelection';
import { GameBoard } from './components/GameBoard';
import { useCreateGame } from './hooks/useGame';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

type GamePhase = 'deck-selection-p1' | 'deck-selection-p2' | 'playing' | 'game-over';

function GameApp() {
  const [gamePhase, setGamePhase] = useState<GamePhase>('deck-selection-p1');
  const [player1Deck, setPlayer1Deck] = useState<string[]>([]);
  const [player2Deck, _setPlayer2Deck] = useState<string[]>([]);
  const [gameId, setGameId] = useState<string | null>(null);
  const [winner, setWinner] = useState<string | null>(null);

  const createGameMutation = useCreateGame();

  const handlePlayer1DeckSelected = (deck: string[]) => {
    setPlayer1Deck(deck);
    setGamePhase('deck-selection-p2');
  };

  const handlePlayer2DeckSelected = (deck: string[]) => {
    _setPlayer2Deck(deck);
    
    // Create the game
    createGameMutation.mutate(
      {
        player1: {
          player_id: 'human',
          name: 'Player',
          deck: player1Deck,
        },
        player2: {
          player_id: 'ai',
          name: 'AI Opponent',
          deck,
        },
      },
      {
        onSuccess: (response) => {
          setGameId(response.game_id);
          setGamePhase('playing');
        },
        onError: (error) => {
          console.error('Failed to create game:', error);
          alert('Failed to create game. Please try again.');
          setGamePhase('deck-selection-p1');
        },
      }
    );
  };

  const handleGameEnd = (winnerName: string) => {
    setWinner(winnerName);
    setGamePhase('game-over');
  };

  const handlePlayAgain = () => {
    setGamePhase('deck-selection-p1');
    setPlayer1Deck([]);
    _setPlayer2Deck([]);
    setGameId(null);
    setWinner(null);
  };

  // Debug output
  console.log('GameApp rendering, phase:', gamePhase);

  if (gamePhase === 'deck-selection-p1') {
    return <DeckSelection playerName="Player 1" onDeckSelected={handlePlayer1DeckSelected} />;
  }

  if (gamePhase === 'deck-selection-p2') {
    return <DeckSelection playerName="AI Opponent" onDeckSelected={handlePlayer2DeckSelected} />;
  }

  if (gamePhase === 'playing' && gameId) {
    return (
      <GameBoard
        gameId={gameId}
        humanPlayerId="human"
        aiPlayerId="ai"
        onGameEnd={handleGameEnd}
      />
    );
  }

  if (gamePhase === 'game-over' && winner) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#1a1a2e', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'white' }}>
          <h1 style={{ fontSize: '3.75rem', fontWeight: 'bold', marginBottom: '1rem' }}>Game Over!</h1>
          <p style={{ fontSize: '1.875rem', marginBottom: '2rem' }}>{winner} Wins!</p>
          <button
            onClick={handlePlayAgain}
            style={{
              padding: '1rem 2rem',
              backgroundColor: '#e94560',
              borderRadius: '0.5rem',
              fontSize: '1.25rem',
              fontWeight: 'bold',
              border: 'none',
              color: 'white',
              cursor: 'pointer'
            }}
          >
            Play Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#1a1a2e', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
      <div style={{ fontSize: '1.5rem' }}>Loading...</div>
    </div>
  );
}

function App() {
  console.log('App component rendering');
  return (
    <QueryClientProvider client={queryClient}>
      <GameApp />
    </QueryClientProvider>
  );
}

export default App;
