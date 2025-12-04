/**
 * Main App Component
 * Handles game flow: login → menu → lobby/deck selection → game → game over
 */

import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuth } from './contexts/AuthContext';
import { LoadingScreen } from './components/LoadingScreen';
import LoginPage from './components/LoginPage';
import { LobbyHome } from './components/LobbyHome';
import { LobbyCreate } from './components/LobbyCreate';
import { LobbyJoin } from './components/LobbyJoin';
import { LobbyWaiting } from './components/LobbyWaiting';
import { DeckSelection } from './components/DeckSelection';
import { GameBoard } from './components/GameBoard';
import { VictoryScreen } from './components/VictoryScreen';
import { PrivacyPolicy } from './pages/PrivacyPolicy';
import { TermsOfService } from './pages/TermsOfService';
import { useCreateGame } from './hooks/useGame';
import type { GameState } from './types/game';

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
  | 'game-over'
  | 'privacy-policy'
  | 'terms-of-service';

type GameMode = 'single-player' | 'multiplayer';

function GameApp() {
  // Auth context provides the authenticated user's Google ID for consistent stats tracking
  const { user } = useAuth();
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
  // Store actual player IDs for games
  // For single-player: { human: google_id, ai: 'ai-gemiknight' }
  // For multiplayer: { human: google_id, opponent: opponent_google_id }
  const [playerIds, setPlayerIds] = useState<{ human: string; other: string } | null>(null);

  const createGameMutation = useCreateGame();

  const handleLoadingComplete = () => {
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

  const handleQuickPlay = async () => {
    if (!user?.google_id) {
      alert('You must be logged in to play Quick Play');
      return;
    }

    try {
      const { quickPlay } = await import('./api/gameService');
      const response = await quickPlay(user.google_id, user.display_name || 'Player');
      
      // Set game state and jump directly to playing
      setGameMode('single-player');
      setGameId(response.game_id);
      setPlayer1Name(user.display_name || 'Player');
      setPlayer2Name('Gemiknight');
      setPlayerIds({ human: user.google_id, other: 'ai-gemiknight' });
      setGamePhase('playing');
    } catch (error) {
      console.error('Failed to start Quick Play:', error);
      alert('Failed to start Quick Play. Please try again.');
    }
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
    setPlayerIds(null);
  };

  // Lobby handlers
  const handleLobbyCreated = (newGameId: string, newGameCode: string) => {
    setGameId(newGameId);
    setGameCode(newGameCode);
    setCurrentPlayerId('player1');
    // Store the current user's Google ID as player 1
    if (user?.google_id) {
      setPlayerIds({ human: user.google_id, other: '' });
    }
    setGamePhase('lobby-waiting');
  };

  const handleLobbyJoined = (newGameId: string, newGameCode: string, opponentName: string, opponentId: string) => {
    setGameId(newGameId);
    setGameCode(newGameCode);
    setPlayer1Name(opponentName);  // player1 is the opponent in this case
    setCurrentPlayerId('player2');
    // Store both player IDs - we're player2, opponent (player1) ID from response
    if (user?.google_id) {
      setPlayerIds({ human: user.google_id, other: opponentId });
    }
    setGamePhase('lobby-waiting');
  };

  const handleMultiplayerGameStarted = (startedGameId: string) => {
    setGameId(startedGameId);
    setGamePhase('playing');
  };

  const handlePlayer1DeckSelected = (deck: string[], playerName: string) => {
    setPlayer1Deck(deck);
    setPlayer1Name(playerName);
    setGamePhase('deck-selection-p2');
  };

  const handlePlayer2DeckSelected = (deck: string[], playerName: string) => {
    setPlayer2Name(playerName);
    
    // Use Google ID for authenticated user, ensures stats aggregate correctly
    // AI always uses a consistent ID so AI stats are tracked separately
    const humanPlayerId = user?.google_id || `guest-${crypto.randomUUID()}`;
    const aiPlayerId = 'ai-gemiknight';
    
    // Store the IDs so GameBoard can use them
    setPlayerIds({ human: humanPlayerId, other: aiPlayerId });
    
    // Create the game
    createGameMutation.mutate(
      {
        player1: {
          player_id: humanPlayerId,
          name: player1Name,
          deck: player1Deck,
        },
        player2: {
          player_id: aiPlayerId,
          name: playerName,
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
    setPlayerIds(null);
  };

  const handleShowPrivacyPolicy = () => {
    setGamePhase('privacy-policy');
  };

  const handleShowTermsOfService = () => {
    setGamePhase('terms-of-service');
  };

  const handleBackFromLegal = () => {
    setGamePhase('menu');
  };

  if (gamePhase === 'privacy-policy') {
    return <PrivacyPolicy onBack={handleBackFromLegal} />;
  }

  if (gamePhase === 'terms-of-service') {
    return <TermsOfService onBack={handleBackFromLegal} />;
  }

  if (gamePhase === 'loading') {
    return <LoadingScreen onReady={handleLoadingComplete} />;
  }

  if (gamePhase === 'menu') {
    return (
      <LobbyHome
        onCreateLobby={handleCreateLobby}
        onJoinLobby={handleJoinLobby}
        onPlayVsAI={handlePlayVsAI}
        onQuickPlay={handleQuickPlay}
        onShowPrivacyPolicy={handleShowPrivacyPolicy}
        onShowTermsOfService={handleShowTermsOfService}
      />
    );
  }

  if (gamePhase === 'lobby-create') {
    return <LobbyCreate onLobbyCreated={handleLobbyCreated} onBack={handleBackToMenu} />;
  }

  if (gamePhase === 'lobby-join') {
    return <LobbyJoin onLobbyJoined={handleLobbyJoined} onBack={handleBackToMenu} />;
  }

  if (gamePhase === 'lobby-waiting' && gameId && gameCode && playerIds) {
    return (
      <LobbyWaiting
        gameId={gameId}
        gameCode={gameCode}
        actualPlayerId={playerIds.human}
        currentPlayerId={currentPlayerId}
        currentPlayerName={currentPlayerId === 'player1' ? player1Name : player2Name}
        otherPlayerName={currentPlayerId === 'player1' ? player2Name : player1Name}
        onGameStarted={handleMultiplayerGameStarted}
        onBack={handleBackToMenu}
      />
    );
  }

  if (gamePhase === 'deck-selection-p1') {
    return <DeckSelection onDeckSelected={handlePlayer1DeckSelected} hiddenMode={hiddenCardsMode} />;
  }

  if (gamePhase === 'deck-selection-p2') {
    // For AI games (single-player), use "Gemiknight" as the AI's name
    const aiDefaultName = gameMode === 'single-player' ? 'Gemiknight' : undefined;
    return <DeckSelection onDeckSelected={handlePlayer2DeckSelected} hiddenMode={hiddenCardsMode} defaultPlayerName={aiDefaultName} />;
  }

  if (gamePhase === 'playing' && gameId && playerIds) {
    // Use actual player IDs (Google IDs for humans, 'ai-gemiknight' for AI)
    const humanPlayerId = playerIds.human;
    const otherPlayerId = playerIds.other;

    return (
      <GameBoard
        gameId={gameId}
        humanPlayerId={humanPlayerId}
        aiPlayerId={gameMode === 'single-player' ? otherPlayerId : undefined}
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
      <AuthWrapper />
    </QueryClientProvider>
  );
}

function AuthWrapper() {
  const { isAuthenticated, isLoading } = useAuth();
  const [authPhase, setAuthPhase] = useState<'login' | 'privacy-policy' | 'terms-of-service'>('login');

  // Show loading while checking auth state
  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#1a1a2e', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
        <div style={{ fontSize: '1.5rem' }}>Loading...</div>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!isAuthenticated) {
    if (authPhase === 'privacy-policy') {
      return <PrivacyPolicy onBack={() => setAuthPhase('login')} />;
    }
    
    if (authPhase === 'terms-of-service') {
      return <TermsOfService onBack={() => setAuthPhase('login')} />;
    }
    
    return (
      <LoginPage 
        onShowPrivacyPolicy={() => setAuthPhase('privacy-policy')}
        onShowTermsOfService={() => setAuthPhase('terms-of-service')}
      />
    );
  }

  // Show game app if authenticated
  return <GameApp />;
}

export default App;
