/**
 * Type definitions for GGLTCG game entities
 */

export type CardType = 'TOY' | 'ACTION';
export type Zone = 'HAND' | 'IN_PLAY' | 'SLEEP';
export type Phase = 'START' | 'MAIN' | 'END';

export interface Card {
  name: string;
  card_type: CardType;
  cost: number;
  zone: Zone;
  owner: string;
  controller: string;
  speed: number | null;
  strength: number | null;
  stamina: number | null;
  current_stamina: number | null;
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

export interface GameState {
  game_id: string;
  turn_number: number;
  phase: Phase;
  active_player_id: string;
  first_player_id: string;
  players: Record<string, Player>;
  winner: string | null;
  is_game_over: boolean;
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
