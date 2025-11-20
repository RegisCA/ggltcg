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

export interface ActionResponse {
  success: boolean;
  message: string;
  game_state?: Record<string, any>;
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
