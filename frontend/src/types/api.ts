/**
 * Type definitions for API requests and responses
 */

import type { ValidAction } from './game';

// Game Creation
export interface PlayerCreate {
  player_id: string;
  name: string;
  deck: string[];
}

export interface GameCreateRequest {
  player1: PlayerCreate;
  player2: PlayerCreate;
  first_player_id?: string;
}

export interface GameCreateResponse {
  game_id: string;
  message: string;
}

// Player Actions
export interface PlayCardRequest {
  player_id: string;
  card_id: string;  // Unique card instance ID
  target_card_id?: string;  // Target card ID for single-target effects
  target_card_ids?: string[];  // Multiple target card IDs (e.g., Sun)
  alternative_cost_card_id?: string;  // Card ID to sleep for alternative cost (e.g., Ballaber)
}

export interface TussleRequest {
  player_id: string;
  attacker_id: string;  // ID of attacking card
  defender_id?: string;  // ID of defending card (undefined for direct attack)
}

export interface EndTurnRequest {
  player_id: string;
}

export interface ActivateAbilityRequest {
  player_id: string;
  card_id: string;  // ID of card with the ability
  target_id?: string;  // Optional target card ID (e.g., for Archer)
  amount?: number;  // Optional amount parameter (default: 1)
}

export interface ActionResponse {
  success: boolean;
  message: string;
  game_state?: Record<string, unknown>;
}

// Valid Actions
export interface ValidActionsResponse {
  game_id: string;
  player_id: string;
  valid_actions: ValidAction[];
}

// Error Response
export interface ErrorResponse {
  error: string;
  details?: string;
}

// Card Data
export interface CardDataResponse {
  name: string;
  card_type: 'Toy' | 'Action';
  cost: number; // -1 for variable cost
  effect: string;
  speed: number | null;
  strength: number | null;
  stamina: number | null;
  primary_color: string;
  accent_color: string;
}

// Lobby / Multiplayer
export interface CreateLobbyRequest {
  player1_id: string;  // Google ID for authenticated users
  player1_name: string;
}

export interface CreateLobbyResponse {
  game_id: string;
  game_code: string;
  player1_id: string;
  player1_name: string;
  status: string;
}

export interface JoinLobbyRequest {
  player2_id: string;  // Google ID for authenticated users
  player2_name: string;
}

export interface JoinLobbyResponse {
  game_id: string;
  game_code: string;
  player1_id: string;
  player1_name: string;
  player2_id: string;
  player2_name: string;
  status: string;
}

export interface LobbyStatusResponse {
  game_id: string;
  game_code: string;
  player1_id: string;
  player1_name: string;
  player2_id: string | null;
  player2_name: string | null;
  status: string;
  ready_to_start: boolean;
}

export interface StartGameRequest {
  player_id: string;
  deck: string[];
}

export interface StartGameResponse {
  game_id: string;
  status: string;
  first_player_id: string;
  game_state: unknown;
}

// ============================================================================
// STATS AND LEADERBOARD
// ============================================================================

export interface CardStats {
  card_name: string;
  games_played: number;
  games_won: number;
  win_rate: number;
}

export interface PlayerStats {
  player_id: string;
  display_name: string;
  games_played: number;
  games_won: number;
  win_rate: number;
  total_tussles: number;
  tussles_won: number;
  tussle_win_rate: number;
  card_stats: CardStats[];
}

export interface LeaderboardEntry {
  rank: number;
  player_id: string;
  display_name: string;
  games_played: number;
  games_won: number;
  win_rate: number;
}

export interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  total_players: number;
  min_games_required: number;
  card_name?: string;
}
