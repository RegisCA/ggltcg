/**
 * React Query hooks for game state and actions
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseMutationResult, UseQueryResult } from '@tanstack/react-query';
import type {
  GameCreateRequest,
  GameCreateResponse,
  PlayCardRequest,
  TussleRequest,
  EndTurnRequest,
  ActionResponse,
  ValidActionsResponse,
} from '../types/api';
import type { GameState } from '../types/game';
import * as gameService from '../api/gameService';

// ============================================================================
// QUERY KEYS
// ============================================================================

export const gameKeys = {
  all: ['games'] as const,
  game: (id: string) => [...gameKeys.all, id] as const,
  gameState: (id: string, playerId?: string) => 
    [...gameKeys.game(id), 'state', playerId] as const,
  validActions: (id: string, playerId: string) => 
    [...gameKeys.game(id), 'actions', playerId] as const,
};

// ============================================================================
// GAME STATE QUERIES
// ============================================================================

export function useGameState(
  gameId: string | null,
  playerId?: string,
  options?: { enabled?: boolean; refetchInterval?: number }
): UseQueryResult<GameState, Error> {
  return useQuery({
    queryKey: gameKeys.gameState(gameId || '', playerId),
    queryFn: () => gameService.getGameState(gameId!, playerId),
    enabled: !!gameId && (options?.enabled !== false),
    refetchInterval: options?.refetchInterval || false,
    staleTime: 0, // Always fetch fresh data
  });
}

export function useValidActions(
  gameId: string | null,
  playerId: string | null,
  options?: { enabled?: boolean }
): UseQueryResult<ValidActionsResponse, Error> {
  return useQuery({
    queryKey: gameKeys.validActions(gameId || '', playerId || ''),
    queryFn: () => gameService.getValidActions(gameId!, playerId!),
    enabled: !!gameId && !!playerId && (options?.enabled !== false),
    staleTime: 0,
  });
}

// ============================================================================
// GAME MUTATIONS
// ============================================================================

export function useCreateGame(): UseMutationResult<
  GameCreateResponse,
  Error,
  GameCreateRequest
> {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: gameService.createGame,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gameKeys.all });
    },
  });
}

export function usePlayCard(
  gameId: string
): UseMutationResult<ActionResponse, Error, PlayCardRequest> {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data) => gameService.playCard(gameId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gameKeys.game(gameId) });
    },
  });
}

export function useTussle(
  gameId: string
): UseMutationResult<ActionResponse, Error, TussleRequest> {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data) => gameService.initiateTussle(gameId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gameKeys.game(gameId) });
    },
  });
}

export function useEndTurn(
  gameId: string
): UseMutationResult<ActionResponse, Error, EndTurnRequest> {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data) => gameService.endTurn(gameId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gameKeys.game(gameId) });
    },
  });
}

export function useAITurn(
  gameId: string
): UseMutationResult<ActionResponse, Error, string> {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (aiPlayerId) => gameService.aiTakeTurn(gameId, aiPlayerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gameKeys.game(gameId) });
    },
  });
}

export function useDeleteGame(): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: gameService.deleteGame,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gameKeys.all });
    },
  });
}
