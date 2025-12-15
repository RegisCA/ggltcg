/**
 * Type definitions for GGLTCG game entities
 */

export type CardType = 'Toy' | 'Action';  // Match backend CardType enum values
export type Zone = 'Hand' | 'InPlay' | 'Sleep';  // Match backend Zone enum values
export type Phase = 'Start' | 'Main' | 'End';  // Match backend Phase enum values

export interface Card {
  id: string;  // Unique card instance ID
  name: string;
  card_type: CardType;
  cost: number;
  effective_cost: number | null;  // Current cost after modifications (null if same as base)
  effect_text: string;  // Card effect description
  zone: Zone;
  owner: string;
  controller: string;
  speed: number | null;  // Current effective speed (with buffs)
  strength: number | null;  // Current effective strength (with buffs)
  stamina: number | null;  // Current effective max stamina (with buffs)
  current_stamina: number | null;  // Actual current stamina (can be damaged)
  base_speed: number | null;  // Original speed from card definition
  base_strength: number | null;  // Original strength from card definition
  base_stamina: number | null;  // Original stamina from card definition
  is_sleeped: boolean;
  primary_color: string;
  accent_color: string;
}

export interface Player {
  player_id: string;
  name: string;
  cc: number;
  hand_count: number;
  hand: Card[] | null;
  in_play: Card[];
  sleep_zone: Card[];
  direct_attacks_this_turn: number;
}

export interface PlayByPlayEntry {
  turn: number;
  player: string;
  action_type: string;
  description: string;
  reasoning?: string;
  ai_endpoint?: string;
}

export interface GameState {
  game_id: string;
  turn_number: number;
  phase: Phase;
  active_player_id: string;
  first_player_id: string;
  players: Record<string, Player>;
  winner: string | null;
  is_game_over: boolean;
  play_by_play?: PlayByPlayEntry[];
}

export interface ValidAction {
  action_type: 'play_card' | 'tussle' | 'end_turn' | 'activate_ability';
  card_id?: string;  // Unique ID of the card for this action
  card_name?: string;  // Display name (for UI convenience)
  target_options?: string[];  // List of valid target card IDs
  max_targets?: number;  // Maximum number of targets to select (e.g., 2 for Sun)
  min_targets?: number;  // Minimum number of targets required (0 for optional)
  cost_cc?: number;
  alternative_cost_available?: boolean;  // Whether alternative cost is available (e.g., Ballaber)
  alternative_cost_options?: string[];  // Card IDs that can be used for alternative cost
  description: string;
}

// Card data from CSV
export interface CardData {
  name: string;
  status: string;
  cost: number | string; // "?" for Copy
  effect: string;
  speed: number | null;
  strength: number | null;
  stamina: number | null;
  faction: string;
  quote: string;
}
