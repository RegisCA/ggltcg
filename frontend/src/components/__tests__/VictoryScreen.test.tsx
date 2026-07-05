/**
 * Smoke tests for VictoryScreen pinning the content that must survive the
 * Paper & Ink restyle verbatim: the PR #371 AI persona nickname badge and
 * the "Improvised" fallback badge (docs/plans/PAPER_AND_INK_PHASE3_HANDOFF.md
 * §4). Uses the same canned aiLogs payload style as the /design.html
 * harness fixtures (aiLogsOverride skips the network fetch).
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VictoryScreen } from '../VictoryScreen';
import type { GameState, PlayByPlayEntry } from '../../types/game';
import type { AILogData } from '../../api/statsService';

const HUMAN_ID = 'human-1';
const AI_ID = 'ai-1';

function makeGameState(overrides: Partial<GameState> = {}): GameState {
  const playByPlay: PlayByPlayEntry[] = [
    { turn: 1, player: 'You', action_type: 'play_card', description: 'Played Knight (1 Charge)' },
    { turn: 1, player: 'You', action_type: 'end_turn', description: 'Ended turn' },
    {
      turn: 2,
      player: 'Gemiknight',
      action_type: 'tussle',
      description: 'Ka direct attacked (2 Charge)',
      reasoning: 'Redirected the attack after the planned target broke early.',
    },
  ];
  return {
    game_id: 'game-1',
    turn_number: 2,
    phase: 'Main',
    active_player_id: HUMAN_ID,
    first_player_id: HUMAN_ID,
    players: {
      [HUMAN_ID]: { player_id: HUMAN_ID, name: 'You', charge: 1, hand_count: 0, hand: null, in_play: [], break_zone: [], direct_attacks_this_turn: 0 },
      [AI_ID]: { player_id: AI_ID, name: 'Gemiknight', charge: 0, hand_count: 0, hand: null, in_play: [], break_zone: [], direct_attacks_this_turn: 0 },
    },
    winner: HUMAN_ID,
    is_game_over: true,
    play_by_play: playByPlay,
    ...overrides,
  };
}

const AI_LOGS: AILogData[] = [
  {
    turn_number: 2,
    player_id: AI_ID,
    ai_version: null,
    turn_plan: { strategy: 'Trade Ka into the weakest target available.', planner: 'enum' },
    plan_execution_status: 'fallback',
    fallback_reason: 'Planned target broke before Ka could act.',
  },
];

describe('VictoryScreen', () => {
  it('shows the winner name and the AI persona nickname badge', () => {
    render(<VictoryScreen gameState={makeGameState()} onPlayAgain={() => {}} aiLogsOverride={AI_LOGS} />);
    expect(screen.getByText('You Wins!')).toBeInTheDocument();
    // plannerDisplayName('enum') => 'Mastermind' (src/utils/plannerMode.ts)
    expect(screen.getByText(/Mastermind/)).toBeInTheDocument();
  });

  it('shows the Improvised badge when plan_execution_status is fallback', () => {
    render(<VictoryScreen gameState={makeGameState()} onPlayAgain={() => {}} aiLogsOverride={AI_LOGS} />);
    expect(screen.getByText(/Improvised/)).toBeInTheDocument();
  });

  it('renders AI reasoning text for entries that have it', () => {
    render(<VictoryScreen gameState={makeGameState()} onPlayAgain={() => {}} aiLogsOverride={AI_LOGS} />);
    expect(screen.getByText(/Redirected the attack after the planned target broke early\./)).toBeInTheDocument();
  });

  it('renders without AI logs (human vs human / no AI recap data)', () => {
    render(<VictoryScreen gameState={makeGameState()} onPlayAgain={() => {}} aiLogsOverride={[]} />);
    expect(screen.getByText('You Wins!')).toBeInTheDocument();
    expect(screen.queryByText(/Improvised/)).not.toBeInTheDocument();
  });

  it('colors identities viewer-relative when localPlayerId is provided (human vs human)', () => {
    // No AI logs and no reasoning entries: without localPlayerId both sides
    // would fall back to --you. With it, the opponent must still be --them.
    const state = makeGameState({
      play_by_play: [
        { turn: 1, player: 'You', action_type: 'play_card', description: 'Played Knight (1 Charge)' },
        { turn: 2, player: 'Gemiknight', action_type: 'play_card', description: 'Played Ka (2 Charge)' },
      ],
    });
    render(
      <VictoryScreen gameState={state} onPlayAgain={() => {}} aiLogsOverride={[]} localPlayerId={HUMAN_ID} />
    );
    const you = screen.getByText('You', { selector: 'span,div,p,h3' });
    const them = screen.getByText('Gemiknight', { selector: 'span,div,p,h3' });
    expect(you).toHaveStyle({ color: 'var(--you)' });
    expect(them).toHaveStyle({ color: 'var(--them)' });
  });
});
