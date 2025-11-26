/**
 * Main App Component
 * Handles game flow: menu → lobby/deck selection → game → game over
 */

import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LoadingScreen } from './components/LoadingScreen';
import { LobbyHome } from './components/LobbyHome';
import { LobbyCreate } from './components/LobbyCreate';
import { LobbyJoin } from './components/LobbyJoin';
import { LobbyWaiting } from './components/LobbyWaiting';
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

type GamePhase = 
  | 'loading' 
  | 'menu' 
  | 'lobby-create' 
  | 'lobby-join' 
  | 'lobby-waiting' 
  | 'deck-selection-p1' 
  | 'deck-selection-p2' 
  | 'playing' 
  | 'game-over';

type GameMode = 'single-player' | 'multiplayer';

function GameApp() {
  const [gamePhase, setGamePhase] = useState<GamePhase>('loading');
  const [gameMode, setGameMode] = useState<GameMode>('single-player');
  const [player1Deck, setPlayer1Deck] = useState<string[]>([]);
  const [player1Name, setPlayer1Name] = useState('Player');
  const [player2Name, setPlayer2Name] = useState('Opponent');
  const [gameId, setGameId] = useState<string | null>(null);
  const [gameCode, setGameCode] = useState<string>('');
  const [currentPlayerId, setCurrentPlayerId] = useState<'player1' | 'player2'>('player1');
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [hiddenCardsMode, setHiddenCardsMode] = useState(false);

  const createGameMutation = useCreateGame();

  const handleLoadingComplete = (_cards: Card[]) => {
    // Cards are preloaded but DeckSelection fetches them independently
    // TODO: Pass cards to DeckSelection to avoid duplicate fetch
    setGamePhase('menu');
  };

  // Menu handlers
  const handleCreateLobby = () => {
    setGameMode('multiplayer');
    setGamePhase('lobby-create');
  };

  const handleJoinLobby = () => {
    setGameMode('multiplayer');
    setGamePhase('lobby-join');
  };

  const handlePlayVsAI = (hiddenMode: boolean) => {
    setGameMode('single-player');
    setHiddenCardsMode(hiddenMode);
    setGamePhase('deck-selection-p1');
  };

  const handleBackToMenu = () => {
    setGamePhase('menu');
    setGameMode('single-player');
    setPlayer1Deck([]);
    setPlayer1Name('Player');
    setPlayer2Name('AI Opponent');
    setGameId(null);
    setGameCode('');
    setCurrentPlayerId('player1');
    setHiddenCardsMode(false);
  };

  // Lobby handlers
  const handleLobbyCreated = (newGameId: string, newGameCode: string, playerName: string) => {
    setGameId(newGameId);
    setGameCode(newGameCode);
    setPlayer1Name(playerName);
    setCurrentPlayerId('player1');
    setGamePhase('lobby-waiting');
  };

  const handleLobbyJoined = (newGameId: string, newGameCode: string, player1: string, player2: string) => {
    setGameId(newGameId);
    setGameCode(newGameCode);
    setPlayer1Name(player1);
    setPlayer2Name(player2);
    setCurrentPlayerId('player2');
    setGamePhase('lobby-waiting');
  };

  const handleMultiplayerGameStarted = (startedGameId: string, _firstPlayerId: string) => {
    setGameId(startedGameId);
    setGamePhase('playing');
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
    setGamePhase('menu');
    setGameMode('single-player');
    setPlayer1Deck([]);
    setPlayer1Name('Player');
    setPlayer2Name('Opponent');
    setGameId(null);
    setGameCode('');
    setCurrentPlayerId('player1');
    setGameState(null);
    setHiddenCardsMode(false);
  };

  if (gamePhase === 'loading') {
    return <LoadingScreen onReady={handleLoadingComplete} />;
  }

  if (gamePhase === 'menu') {
    return (
      <LobbyHome
        onCreateLobby={handleCreateLobby}
        onJoinLobby={handleJoinLobby}
        onPlayVsAI={handlePlayVsAI}
      />
    );
  }

  if (gamePhase === 'lobby-create') {
    return <LobbyCreate onLobbyCreated={handleLobbyCreated} onBack={handleBackToMenu} />;
  }

  if (gamePhase === 'lobby-join') {
    return <LobbyJoin onLobbyJoined={handleLobbyJoined} onBack={handleBackToMenu} />;
  }

  if (gamePhase === 'lobby-waiting' && gameId && gameCode) {
    return (
      <LobbyWaiting
        gameId={gameId}
        gameCode={gameCode}
        currentPlayerId={currentPlayerId}
        currentPlayerName={currentPlayerId === 'player1' ? player1Name : player2Name}
        otherPlayerName={currentPlayerId === 'player1' ? player2Name : player1Name}
        onGameStarted={handleMultiplayerGameStarted}
        onBack={handleBackToMenu}
      />
    );
  }

  if (gamePhase === 'deck-selection-p1') {
    return <DeckSelection playerName="Player" onDeckSelected={handlePlayer1DeckSelected} hiddenMode={hiddenCardsMode} />;
  }

  if (gamePhase === 'deck-selection-p2') {
    return <DeckSelection playerName="Opponent" onDeckSelected={handlePlayer2DeckSelected} hiddenMode={hiddenCardsMode} />;
  }

  if (gamePhase === 'playing' && gameId) {
    // For multiplayer, use player1/player2 IDs; for single-player use human/ai
    const humanPlayerId = gameMode === 'multiplayer' ? currentPlayerId : 'human';
    const aiPlayerId = gameMode === 'multiplayer' ? (currentPlayerId === 'player1' ? 'player2' : 'player1') : 'ai';

    return (
      <GameBoard
        gameId={gameId}
        humanPlayerId={humanPlayerId}
        aiPlayerId={gameMode === 'single-player' ? aiPlayerId : undefined}
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
