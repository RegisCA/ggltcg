/**
 * Game API service functions
 * All API calls to the GGLTCG backend
 */

import { apiClient } from './client';
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

// ============================================================================
// GAME MANAGEMENT
// ============================================================================

export async function createGame(data: GameCreateRequest): Promise<GameCreateResponse> {
  const response = await apiClient.post<GameCreateResponse>('/games', data);
  return response.data;
}

export async function getGameState(gameId: string, playerId?: string): Promise<GameState> {
  const params = playerId ? { player_id: playerId } : {};
  const response = await apiClient.get<GameState>(`/games/${gameId}`, { params });
  return response.data;
}

export async function deleteGame(gameId: string): Promise<void> {
  await apiClient.delete(`/games/${gameId}`);
}

// ============================================================================
// PLAYER ACTIONS
// ============================================================================

export async function playCard(gameId: string, data: PlayCardRequest): Promise<ActionResponse> {
  const response = await apiClient.post<ActionResponse>(`/games/${gameId}/play-card`, data);
  return response.data;
}

export async function initiateTussle(gameId: string, data: TussleRequest): Promise<ActionResponse> {
  const response = await apiClient.post<ActionResponse>(`/games/${gameId}/tussle`, data);
  return response.data;
}

export async function endTurn(gameId: string, data: EndTurnRequest): Promise<ActionResponse> {
  const response = await apiClient.post<ActionResponse>(`/games/${gameId}/end-turn`, data);
  return response.data;
}

export async function aiTakeTurn(gameId: string, aiPlayerId: string): Promise<ActionResponse> {
  const response = await apiClient.post<ActionResponse>(
    `/games/${gameId}/ai-turn`,
    {},
    { params: { player_id: aiPlayerId } }
  );
  return response.data;
}

export async function getValidActions(
  gameId: string,
  playerId: string
): Promise<ValidActionsResponse> {
  const response = await apiClient.get<ValidActionsResponse>(
    `/games/${gameId}/valid-actions`,
    { params: { player_id: playerId } }
  );
  return response.data;
}
