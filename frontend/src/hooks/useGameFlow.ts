/**
 * useGameFlow Hook
 * 
 * Manages game flow orchestration including:
 * - AI turn auto-triggering
 * - Winner detection & game end callback
 * - Modal clearing on turn change
 * - Error handling for game not found
 */

import { useEffect, useCallback } from 'react';
import type { GameState } from '../types/game';
import type { ActionResponse } from '../types/api';
import { useAITurn } from './useGame';

interface UseGameFlowOptions {
  gameId: string;
  humanPlayerId: string;
  aiPlayerId?: string;
  onGameEnd: (winner: string, gameState: GameState) => void;
  onAIMessage: (message: string) => void;
  onAIError: (error: Error) => void;
  isProcessing: boolean;
}

interface UseGameFlowReturn {
  isAIThinking: boolean;
  triggerAITurn: () => void;
}

export function useGameFlow(
  gameState: GameState | undefined,
  error: Error | null,
  options: UseGameFlowOptions
): UseGameFlowReturn {
  const { 
    gameId, 
    aiPlayerId, 
    onGameEnd, 
    onAIMessage, 
    onAIError,
    isProcessing 
  } = options;

  const aiTurnMutation = useAITurn(gameId);

  // Handle game not found (404 error)
  useEffect(() => {
    if (error) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const apiError = error as any;
      if (apiError?.response?.status === 404) {
        alert('Game not found. The server may have restarted. Please create a new game.');
        window.location.reload();
      }
    }
  }, [error]);

  // Check for game over
  useEffect(() => {
    if (gameState?.winner) {
      onGameEnd(gameState.winner, gameState);
    }
  }, [gameState?.winner, onGameEnd, gameState]);

  // Auto-trigger AI turn (only for single-player mode)
  useEffect(() => {
    if (
      aiPlayerId &&
      gameState &&
      gameState.active_player_id === aiPlayerId &&
      !gameState.is_game_over &&
      !isProcessing &&
      !aiTurnMutation.isPending
    ) {
      // Delay AI turn slightly for better UX
      const timer = setTimeout(() => {
        aiTurnMutation.mutate(aiPlayerId, {
          onSuccess: (response: ActionResponse) => {
            // Don't add message if game just ended
            if (!response.game_state?.is_game_over) {
              onAIMessage(response.message);
            }
          },
          onError: (error: Error) => {
            console.error('AI turn error:', error);
            onAIError(error);
          },
        });
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [
    gameState,
    aiPlayerId, 
    isProcessing, 
    aiTurnMutation,
    onAIMessage,
    onAIError,
  ]);

  // Manual AI turn trigger (for testing or retry)
  const triggerAITurn = useCallback(() => {
    if (aiPlayerId && !aiTurnMutation.isPending) {
      aiTurnMutation.mutate(aiPlayerId, {
        onSuccess: (response: ActionResponse) => {
          if (!response.game_state?.is_game_over) {
            onAIMessage(response.message);
          }
        },
        onError: (error: Error) => {
          console.error('AI turn error:', error);
          onAIError(error);
        },
      });
    }
  }, [aiPlayerId, aiTurnMutation, onAIMessage, onAIError]);

  return {
    isAIThinking: aiTurnMutation.isPending,
    triggerAITurn,
  };
}
