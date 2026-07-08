/**
 * Shared types for the Admin Data Viewer.
 *
 * Moved verbatim out of AdminDataViewer.tsx as part of the API-service
 * extraction (PR A1) — no shape changes.
 */

export interface SummaryStats {
  users: { total: number };
  games: {
    total: number;
    active: number;
    completed: number;
    recent_24h: number;
  };
  ai_logs: {
    total: number;
    recent_1h: number;
  };
  playbacks: {
    total: number;
  };
}

export interface AILog {
  id: number;
  game_id: string;
  turn_number: number;
  player_id: string;
  model_name: string;
  prompts_version: string;
  prompt: string;
  response: string;
  action_number: number | null;
  reasoning: string | null;
  created_at: string;
  // ai_version is a legacy column, no longer written (kept inert so old rows
  // don't lose their historical label); turn_plan.planner is the current key
  // ("enum" for every live log).
  ai_version: number | null;
  turn_plan: {
    planner?: string | null;
    strategy: string;
    total_actions: number;
    current_action: number;
    charge_start: number;
    charge_after_plan: number;
    expected_cards_broken: number;
    // Full action sequence
    action_sequence?: Array<{
      action_type: string;
      card_name: string | null;
      target_names: string[] | null;
      charge_cost: number;
      reasoning: string;
    }>;
    // Planning prompt/response (alias of selection_prompt/response below —
    // enum has no separate "planning" LLM call, just the one selection call)
    planning_prompt?: string;
    planning_response?: string;
    // Strategic-selection request (the planner's one LLM call)
    selection_prompt?: string | null;
    selection_response?: string | null;
    selection_system_instruction?: string | null;
    // Per-turn enumerator/selection diagnostics
    enum_debug?: unknown;
    // Execution tracking
    execution_log?: Array<{
      action_index: number;
      planned_action: string;
      status: 'success' | 'failed' | 'fallback_to_llm' | 'execution_failed';
      method?: 'heuristic' | 'llm';
      reason?: string;
      execution_confirmed?: boolean;
    }>;
  } | null;
  plan_execution_status: 'complete' | 'fallback' | null;
  fallback_reason: string | null;
  planned_action_index: number | null;
}

export interface GamePlayback {
  id: number;
  game_id: string;
  player1_id: string;
  player1_name: string;
  player2_id: string;
  player2_name: string;
  winner_id: string | null;
  turn_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface GamePlaybackDetail extends GamePlayback {
  first_player_id: string;
  starting_deck_p1: string[];
  starting_deck_p2: string[];
  play_by_play: Array<{
    turn: number;
    player: string;
    action_type: string;
    description: string;
  }>;
  charge_tracking: TurnCharge[] | null;
}

export interface Game {
  id: string;
  status: string;
  player1_id: string;
  player1_name: string;
  player2_id: string;
  player2_name: string;
  game_code: string | null;
  turn_number: number;
  phase: string;
  winner_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface User {
  google_id: string;
  first_name: string;
  display_name: string;
  created_at: string;
  updated_at: string;
  games_played: number;
  games_won: number;
  win_rate: number;
  avg_turns: number;
  avg_game_duration_seconds: number;
  last_game_at: string | null;
  last_game_status: string | null;
  favorite_decks: string[][];
}

// Charge Tracking interface
export interface TurnCharge {
  turn: number;
  player_id: string;
  charge_start: number;
  charge_gained: number;
  charge_spent: number;
  charge_end: number;
}

// Action log interface
export interface ActionLogEntry {
  turn: number;
  player: string;
  action: string;
  card: string | null;
  description: string;
  reasoning: string;
}

export interface SimulationGameDetail {
  game_number: number;
  deck1_name: string;
  deck2_name: string;
  outcome: string;
  winner_deck: string | null;
  turn_count: number;
  duration_ms: number;
  error_message: string | null;
  charge_tracking: TurnCharge[];
  action_log: ActionLogEntry[];
  player1_model: string;
  player2_model: string;
}

// Simulation interfaces
export interface SimulationDeck {
  name: string;
  description: string;
  cards: string[];
}

// Rate-limiter / daily-budget info for a run (values may be null when no
// budget/rpm cap is configured, or not yet known for a not-yet-started run).
export interface SimulationRunBudget {
  used_today: number | null;
  daily_budget: number | null;
  rpm: number | null;
  resets_at: string | null;
}

export interface SimulationRun {
  run_id: number;
  status: string;
  total_games: number;
  completed_games: number;
  config: {
    deck_names: string[];
    player1_model: string;
    player2_model: string;
    iterations_per_matchup: number;
    max_turns: number;
    rpm?: number | null;
    daily_request_budget?: number | null;
    parallel_games?: number;
  };
  created_at: string;
  completed_at: string | null;
  budget?: SimulationRunBudget;
}

export interface MatchupStats {
  deck1_name: string;
  deck2_name: string;
  games_played: number;
  deck1_wins: number;
  deck2_wins: number;
  draws: number;
  deck1_win_rate: number;
  deck2_win_rate: number;
  avg_turns: number;
  avg_duration_ms: number;
}

export interface SimulationResults {
  run_id: number;
  status: string;
  config: SimulationRun['config'];
  total_games: number;
  completed_games: number;
  matchup_stats: Record<string, MatchupStats>;
  aggregate?: {
    max_turns: number;
    avg_turns: number | null;
    turn_limit_hits: number;
    turn_limit_hit_pct: number;
    avg_p1_charge_end_active: number | null;
    avg_p2_charge_end_active: number | null;
  };
  games: Array<{
    game_number: number;
    deck1_name: string;
    deck2_name: string;
    outcome: string;
    winner_deck: string | null;
    turn_count: number;
    duration_ms: number;
    p1_charge_spent: number;
    p2_charge_spent: number;
    p1_charge_gained: number;
    p2_charge_gained: number;
    p1_avg_charge_end_active?: number | null;
    p2_avg_charge_end_active?: number | null;
    hit_turn_limit?: boolean;
    error_message: string | null;
  }>;
  created_at: string;
  completed_at: string | null;
}
