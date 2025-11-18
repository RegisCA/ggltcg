/**
 * Type definitions for GGLTCG game entities
 */

export type CardType = 'Toy' | 'Action';  // Match backend CardType enum values
export type Zone = 'Hand' | 'InPlay' | 'Sleep';  // Match backend Zone enum values
export type Phase = 'Start' | 'Main' | 'End';  // Match backend Phase enum values

export interface Card {
  name: string;
  card_type: CardType;
  cost: number;
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
  card_name?: string;
  target_options?: string[];
  cost_cc?: number;
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
