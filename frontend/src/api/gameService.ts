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
  ActivateAbilityRequest,
  ActionResponse,
  ValidActionsResponse,
  CardDataResponse,
  CreateLobbyRequest,
  CreateLobbyResponse,
  JoinLobbyRequest,
  JoinLobbyResponse,
  LobbyStatusResponse,
  StartGameRequest,
  StartGameResponse,
} from '../types/api';
import type { GameState } from '../types/game';

// ============================================================================
// CARD DATA
// ============================================================================

export async function getAllCards(): Promise<CardDataResponse[]> {
  const response = await apiClient.get<CardDataResponse[]>('/games/cards');
  return response.data;
}

// ============================================================================
// GAME MANAGEMENT
// ============================================================================

export async function createGame(data: GameCreateRequest): Promise<GameCreateResponse> {
  const response = await apiClient.post<GameCreateResponse>('/games', data);
  return response.data;
}

export async function getRandomDeck(numToys: number, numActions: number): Promise<string[]> {
  const response = await apiClient.post<{ deck: string[]; num_toys: number; num_actions: number }>(
    '/games/random-deck',
    { num_toys: numToys, num_actions: numActions }
  );
  return response.data.deck;
}

export interface QuickPlayResponse {
  game_id: string;
  player_deck: string[];
  ai_deck: string[];
  first_player_id: string;
  message: string;
}

export async function quickPlay(playerId: string, playerName: string): Promise<QuickPlayResponse> {
  const response = await apiClient.post<QuickPlayResponse>('/games/quick-play', {
    player_id: playerId,
    player_name: playerName,
  });
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

export async function activateAbility(
  gameId: string, 
  data: ActivateAbilityRequest
): Promise<ActionResponse> {
  const response = await apiClient.post<ActionResponse>(
    `/games/${gameId}/activate-ability`,
    data
  );
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

export async function generateNarrative(playByPlay: unknown[]): Promise<string> {
  const response = await apiClient.post<{ narrative: string }>(
    '/games/narrative',
    { play_by_play: playByPlay }
  );
  return response.data.narrative;
}

// ============================================================================
// MULTIPLAYER LOBBY
// ============================================================================

export async function createLobby(data: CreateLobbyRequest): Promise<CreateLobbyResponse> {
  const response = await apiClient.post<CreateLobbyResponse>('/games/lobby/create', data);
  return response.data;
}

export async function joinLobby(gameCode: string, data: JoinLobbyRequest): Promise<JoinLobbyResponse> {
  const response = await apiClient.post<JoinLobbyResponse>(`/games/lobby/${gameCode}/join`, data);
  return response.data;
}

export async function getLobbyStatus(gameCode: string): Promise<LobbyStatusResponse> {
  const response = await apiClient.get<LobbyStatusResponse>(`/games/lobby/${gameCode}/status`);
  return response.data;
}

export async function startLobbyGame(gameCode: string, data: StartGameRequest): Promise<StartGameResponse> {
  const response = await apiClient.post<StartGameResponse>(`/games/lobby/${gameCode}/start`, data);
  return response.data;
}
