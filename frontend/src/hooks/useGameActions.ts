/**
 * useGameActions Hook
 * 
 * Consolidates all game action execution:
 * - Play card
 * - Tussle
 * - End turn
 * - Activate ability
 * 
 * Provides a unified interface for executing actions with consistent
 * success/error handling and message callbacks.
 */

import { useCallback } from 'react';
import type { ValidAction } from '../types/game';
import { usePlayCard, useTussle, useEndTurn, useActivateAbility } from './useGame';

interface UseGameActionsOptions {
  gameId: string;
  humanPlayerId: string;
  onMessage: (msg: string, response?: any) => void;
  onActionComplete?: () => void;
}

interface UseGameActionsReturn {
  executeAction: (
    action: ValidAction, 
    selectedTargets: string[], 
    alternativeCostCard?: string
  ) => void;
  isProcessing: boolean;
}

export function useGameActions(options: UseGameActionsOptions): UseGameActionsReturn {
  const { gameId, humanPlayerId, onMessage, onActionComplete } = options;

  // Mutations
  const playCardMutation = usePlayCard(gameId);
  const tussleMutation = useTussle(gameId);
  const endTurnMutation = useEndTurn(gameId);
  const activateAbilityMutation = useActivateAbility(gameId);

  const isProcessing =
    playCardMutation.isPending ||
    tussleMutation.isPending ||
    endTurnMutation.isPending ||
    activateAbilityMutation.isPending;

  const executeAction = useCallback((
    action: ValidAction,
    selectedTargets: string[],
    alternativeCostCard?: string
  ) => {
    const handleSuccess = (response: any) => {
      onMessage(response.message, response);
      onActionComplete?.();
    };

    const handleError = (error: Error) => {
      onMessage(`Error: ${error.message}`);
      onActionComplete?.();
    };

    if (action.action_type === 'end_turn') {
      endTurnMutation.mutate(
        { player_id: humanPlayerId },
        {
          onSuccess: handleSuccess,
          onError: handleError,
        }
      );
    } else if (action.action_type === 'play_card' && action.card_id) {
      playCardMutation.mutate(
        {
          player_id: humanPlayerId,
          card_id: action.card_id,
          target_card_id: selectedTargets.length === 1 ? selectedTargets[0] : undefined,
          target_card_ids: selectedTargets.length > 1 ? selectedTargets : undefined,
          alternative_cost_card_id: alternativeCostCard,
        },
        {
          onSuccess: handleSuccess,
          onError: handleError,
        }
      );
    } else if (action.action_type === 'tussle' && action.card_id) {
      const defenderId = action.target_options?.[0] === 'direct_attack'
        ? undefined
        : action.target_options?.[0];

      tussleMutation.mutate(
        {
          player_id: humanPlayerId,
          attacker_id: action.card_id,
          defender_id: defenderId,
        },
        {
          onSuccess: handleSuccess,
          onError: handleError,
        }
      );
    } else if (action.action_type === 'activate_ability' && action.card_id) {
      activateAbilityMutation.mutate(
        {
          player_id: humanPlayerId,
          card_id: action.card_id,
          target_id: selectedTargets.length === 1 ? selectedTargets[0] : undefined,
          amount: 1,
        },
        {
          onSuccess: handleSuccess,
          onError: handleError,
        }
      );
    }
  }, [
    humanPlayerId,
    playCardMutation,
    tussleMutation,
    endTurnMutation,
    activateAbilityMutation,
    onMessage,
    onActionComplete,
  ]);

  return {
    executeAction,
    isProcessing,
  };
}
