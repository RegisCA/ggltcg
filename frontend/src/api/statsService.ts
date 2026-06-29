/**
 * Stats API service functions
 * API calls for leaderboards and player statistics
 */

import { apiClient } from './client';
import type {
  PlayerStats,
  LeaderboardResponse,
  CardAggregateResponse,
} from '../types/api';

// ============================================================================
// PLAYER STATS
// ============================================================================

/**
 * Get statistics for a specific player
 */
export async function getPlayerStats(playerId: string): Promise<PlayerStats> {
  const response = await apiClient.get<PlayerStats>(`/stats/players/${encodeURIComponent(playerId)}`);
  return response.data;
}

// ============================================================================
// LEADERBOARD
// ============================================================================

/**
 * Get the overall leaderboard
 */
export async function getLeaderboard(
  limit: number = 10,
  minGames: number = 3
): Promise<LeaderboardResponse> {
  const response = await apiClient.get<LeaderboardResponse>('/stats/leaderboard', {
    params: {
      limit,
      min_games: minGames,
    },
  });
  return response.data;
}

// ============================================================================
// CARD STATS (AGGREGATE)
// ============================================================================

/**
 * Get per-card statistics aggregated across all players
 */
export async function getCardStats(
  limit: number = 50,
  minGames: number = 1
): Promise<CardAggregateResponse> {
  const response = await apiClient.get<CardAggregateResponse>('/stats/cards', {
    params: {
      limit,
      min_games: minGames,
    },
  });
  return response.data;
}
// ============================================================================
// AI LOGS
// ============================================================================

/**
 * AI Log data returned from the admin API
 */
export interface AILogData {
  turn_number: number;
  player_id: string;
  ai_version: number | null; // legacy column, unused for current (enum) logs
  turn_plan: {
    strategy: string;
    planner?: string | null;
  } | null;
  plan_execution_status: 'complete' | 'fallback' | null;
  fallback_reason: string | null;
}

interface AILogsResponse {
  count: number;
  logs: AILogData[];
}

/**
 * Get AI decision logs for a specific game
 */
export async function fetchAILogsForGame(gameId: string): Promise<AILogData[]> {
  const response = await apiClient.get<AILogsResponse>('/admin/ai-logs', {
    params: {
      game_id: gameId,
      limit: 50, // Should be enough for any game
    },
  });
  // Extract the logs array from the response object
  return response.data.logs || [];
}