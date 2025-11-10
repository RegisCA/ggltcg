/**
 * GameBoard Component
 * Main game interface that orchestrates all game components
 */

import { useState, useEffect } from 'react';
import type { ValidAction } from '../types/game';
import { useGameState, useValidActions, usePlayCard, useTussle, useEndTurn, useAITurn } from '../hooks/useGame';
import { PlayerZone } from './PlayerZone';
import { ActionPanel } from './ActionPanel';

interface GameBoardProps {
  gameId: string;
  humanPlayerId: string;
  aiPlayerId: string;
  onGameEnd: (winner: string) => void;
}

export function GameBoard({ gameId, humanPlayerId, aiPlayerId, onGameEnd }: GameBoardProps) {
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [message, setMessage] = useState<string>('');

  // Fetch game state with polling
  const { data: gameState, isLoading, error } = useGameState(gameId, humanPlayerId, {
    refetchInterval: 2000, // Poll every 2 seconds
  });

  // Handle game not found (404 error)
  useEffect(() => {
    if (error) {
      const apiError = error as any;
      if (apiError?.response?.status === 404) {
        alert('Game not found. The server may have restarted. Please create a new game.');
        window.location.reload(); // Reload to go back to deck selection
      }
    }
  }, [error]);

  // Fetch valid actions
  const { data: validActionsData } = useValidActions(gameId, humanPlayerId, {
    enabled: gameState?.active_player_id === humanPlayerId,
  });

  // Mutations
  const playCardMutation = usePlayCard(gameId);
  const tussleMutation = useTussle(gameId);
  const endTurnMutation = useEndTurn(gameId);
  const aiTurnMutation = useAITurn(gameId);

  const isProcessing =
    playCardMutation.isPending ||
    tussleMutation.isPending ||
    endTurnMutation.isPending ||
    aiTurnMutation.isPending;

  // Check for game over
  useEffect(() => {
    if (gameState?.winner) {
      onGameEnd(gameState.winner);
    }
  }, [gameState?.winner, onGameEnd]);

  // Auto-trigger AI turn
  useEffect(() => {
    if (
      gameState &&
      gameState.active_player_id === aiPlayerId &&
      !gameState.is_game_over &&
      !isProcessing &&
      !aiTurnMutation.isPending
    ) {
      // Delay AI turn slightly for better UX
      const timer = setTimeout(() => {
        console.log(`Triggering AI turn for turn ${gameState.turn_number}`);
        aiTurnMutation.mutate(aiPlayerId, {
          onSuccess: (response) => {
            setMessage(response.message);
          },
          onError: (error) => {
            console.error('AI turn error:', error);
            setMessage(`AI Error: ${error.message}`);
          },
        });
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [gameState?.active_player_id, gameState?.turn_number, aiPlayerId, isProcessing, aiTurnMutation.isPending]);

  const handleAction = (action: ValidAction) => {
    setMessage('');
    
    if (action.action_type === 'end_turn') {
      endTurnMutation.mutate(
        { player_id: humanPlayerId },
        {
          onSuccess: (response) => setMessage(response.message),
          onError: (error) => setMessage(`Error: ${error.message}`),
        }
      );
    } else if (action.action_type === 'play_card' && action.card_name) {
      playCardMutation.mutate(
        { player_id: humanPlayerId, card_name: action.card_name },
        {
          onSuccess: (response) => {
            setMessage(response.message);
            setSelectedCard(null);
          },
          onError: (error) => setMessage(`Error: ${error.message}`),
        }
      );
    } else if (action.action_type === 'tussle' && action.card_name) {
      const defenderName = action.target_options?.[0] === 'direct_attack' 
        ? undefined 
        : action.target_options?.[0];
      
      tussleMutation.mutate(
        {
          player_id: humanPlayerId,
          attacker_name: action.card_name,
          defender_name: defenderName,
        },
        {
          onSuccess: (response) => {
            setMessage(response.message);
            setSelectedCard(null);
          },
          onError: (error) => setMessage(`Error: ${error.message}`),
        }
      );
    }
  };

  if (isLoading || !gameState) {
    return (
      <div className="min-h-screen bg-game-bg flex items-center justify-center">
        <div className="text-2xl">Loading game...</div>
      </div>
    );
  }

  const humanPlayer = gameState.players[humanPlayerId];
  const aiPlayer = gameState.players[aiPlayerId];

  if (!humanPlayer || !aiPlayer) {
    return (
      <div className="min-h-screen bg-game-bg flex items-center justify-center">
        <div className="text-2xl text-red-500">Error: Players not found</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-game-bg p-4">
      <div className="max-w-7xl mx-auto">
        {/* Game Header */}
        <div className="mb-4 p-4 bg-game-card rounded-lg border-2 border-game-accent">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold">GGLTCG</h1>
            <div className="text-center">
              <div className="text-sm text-gray-400">Turn {gameState.turn_number}</div>
              <div className="text-xl font-bold">{gameState.phase} PHASE</div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-400">Active Player</div>
              <div className="font-bold">
                {gameState.active_player_id === humanPlayerId ? humanPlayer.name : aiPlayer.name}
              </div>
            </div>
          </div>
        </div>

        {/* Message Display */}
        {message && (
          <div className="mb-4 p-3 bg-blue-900 rounded-lg border border-blue-600 animate-fade-in">
            {message}
          </div>
        )}

        {/* AI Processing Indicator */}
        {isProcessing && gameState.active_player_id === aiPlayerId && (
          <div className="mb-4 p-3 bg-purple-900 rounded-lg border border-purple-600 animate-pulse">
            AI is thinking...
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left Column - AI Player */}
          <div className="lg:col-span-2">
            <PlayerZone
              player={aiPlayer}
              isActive={gameState.active_player_id === aiPlayerId}
              isHuman={false}
            />
          </div>

          {/* Right Column - Action Panel */}
          <div>
            <ActionPanel
              validActions={validActionsData?.valid_actions || []}
              onAction={handleAction}
              isProcessing={isProcessing}
              currentCC={humanPlayer.cc}
            />
          </div>

          {/* Bottom - Human Player */}
          <div className="lg:col-span-3">
            <PlayerZone
              player={humanPlayer}
              isActive={gameState.active_player_id === humanPlayerId}
              isHuman={true}
              selectedCard={selectedCard || undefined}
              onCardClick={(cardName) => setSelectedCard(cardName)}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
