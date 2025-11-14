/**
 * Main App Component
 * Handles game flow: loading → deck selection → game → game over
 */

import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LoadingScreen } from './components/LoadingScreen';
import { DeckSelection } from './components/DeckSelection';
import { GameBoard } from './components/GameBoard';
import { VictoryScreen } from './components/VictoryScreen';
import { useCreateGame } from './hooks/useGame';
import type { GameState, Card } from './types/game';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

type GamePhase = 'loading' | 'deck-selection-p1' | 'deck-selection-p2' | 'playing' | 'game-over';

function GameApp() {
  const [gamePhase, setGamePhase] = useState<GamePhase>('loading');
  const [player1Deck, setPlayer1Deck] = useState<string[]>([]);
  const [player1Name, setPlayer1Name] = useState('Player');
  const [player2Name, setPlayer2Name] = useState('AI Opponent');
  const [gameId, setGameId] = useState<string | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);

  const createGameMutation = useCreateGame();

  const handleLoadingComplete = (_cards: Card[]) => {
    // Cards are preloaded but DeckSelection fetches them independently
    // TODO: Pass cards to DeckSelection to avoid duplicate fetch
    setGamePhase('deck-selection-p1');
  };

  const handlePlayer1DeckSelected = (deck: string[], customName?: string) => {
    setPlayer1Deck(deck);
    if (customName) {
      setPlayer1Name(customName);
    }
    setGamePhase('deck-selection-p2');
  };

  const handlePlayer2DeckSelected = (deck: string[], customName?: string) => {
    if (customName) {
      setPlayer2Name(customName);
    }
    
    // Create the game
    createGameMutation.mutate(
      {
        player1: {
          player_id: 'human',
          name: player1Name,
          deck: player1Deck,
        },
        player2: {
          player_id: 'ai',
          name: customName || player2Name,
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

  const handleGameEnd = (_winnerName: string, finalGameState: GameState) => {
    setGameState(finalGameState);
    setGamePhase('game-over');
  };

  const handlePlayAgain = () => {
    setGamePhase('deck-selection-p1');
    setPlayer1Deck([]);
    setPlayer1Name('Player');
    setPlayer2Name('AI Opponent');
    setGameId(null);
    setGameState(null);
  };

  if (gamePhase === 'loading') {
    return <LoadingScreen onReady={handleLoadingComplete} />;
  }

  if (gamePhase === 'deck-selection-p1') {
    return <DeckSelection playerName="Player" onDeckSelected={handlePlayer1DeckSelected} />;
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

  if (gamePhase === 'game-over' && gameState) {
    return <VictoryScreen gameState={gameState} onPlayAgain={handlePlayAgain} />;
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#1a1a2e', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
      <div style={{ fontSize: '1.5rem' }}>Loading...</div>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <GameApp />
    </QueryClientProvider>
  );
}

export default App;
