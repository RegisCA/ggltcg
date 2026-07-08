/**
 * Admin API service functions
 * API calls backing the AdminDataViewer (/admin/* endpoints, excluding
 * /admin/simulation/* which lives in simulationService.ts)
 */

import { apiClient } from './client';
import type {
  SummaryStats,
  AILog,
  Game,
  GamePlayback,
  GamePlaybackDetail,
  User,
} from '../components/admin/types';

export interface AiLogsResponse {
  count: number;
  logs: AILog[];
}

export interface AdminGamesResponse {
  count: number;
  games: Game[];
}

export interface AdminPlaybacksResponse {
  count: number;
  games: GamePlayback[];
}

export interface AdminUsersResponse {
  count: number;
  users: User[];
}

/**
 * Get top-level admin summary stats (users/games/ai_logs/playbacks counts)
 */
export async function getAdminSummary(): Promise<SummaryStats> {
  const response = await apiClient.get<SummaryStats>('/admin/stats/summary');
  return response.data;
}

/**
 * Get AI decision logs, optionally filtered to a single game
 */
export async function getAiLogs(params: { limit: number; gameId?: string | null }): Promise<AiLogsResponse> {
  const query = new URLSearchParams({ limit: String(params.limit) });
  if (params.gameId) {
    query.append('game_id', params.gameId);
  }
  const response = await apiClient.get<AiLogsResponse>(`/admin/ai-logs?${query}`);
  return response.data;
}

/**
 * Get the most recent games
 */
export async function getAdminGames(limit: number = 50): Promise<AdminGamesResponse> {
  const response = await apiClient.get<AdminGamesResponse>(`/admin/games?limit=${limit}`);
  return response.data;
}

/**
 * Get the most recent completed-game playbacks (list view)
 */
export async function getGamePlaybacks(limit: number = 30): Promise<AdminPlaybacksResponse> {
  const response = await apiClient.get<AdminPlaybacksResponse>(`/admin/game-playbacks?limit=${limit}`);
  return response.data;
}

/**
 * Get full playback detail (play-by-play, decks, charge tracking) for one game
 */
export async function getPlaybackDetail(gameId: string): Promise<GamePlaybackDetail> {
  const response = await apiClient.get<GamePlaybackDetail>(`/admin/game-playbacks/${gameId}`);
  return response.data;
}

/**
 * Get registered users with aggregate stats
 */
export async function getAdminUsers(limit: number = 50): Promise<AdminUsersResponse> {
  const response = await apiClient.get<AdminUsersResponse>(`/admin/users?limit=${limit}`);
  return response.data;
}
