/**
 * Smoke render tests for the admin tab components split out of
 * AdminDataViewer.tsx (PR A2). Services are mocked; each tab renders
 * with canned data and shows its expected headline content.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SummaryTab from '../tabs/SummaryTab';
import AiLogsTab from '../tabs/AiLogsTab';
import GamesTab from '../tabs/GamesTab';
import PlaybacksTab from '../tabs/PlaybacksTab';
import UsersTab from '../tabs/UsersTab';
import SimulationTab from '../tabs/SimulationTab';
import type { Game, GamePlayback, SummaryStats, User } from '../types';

vi.mock('../../../api/adminService', async (importOriginal) => ({
  ...(await importOriginal<object>()),
  getAiLogs: vi.fn().mockResolvedValue({ count: 0, logs: [] }),
  getPlaybackDetail: vi.fn(),
}));

vi.mock('../../../api/simulationService', () => ({
  getSimulationDecks: vi.fn().mockResolvedValue([
    { name: 'Aggro', description: 'Fast deck', cards: ['A', 'B', 'C'] },
  ]),
  getSupportedModels: vi.fn().mockResolvedValue(['gemini-2.5-flash-lite']),
  listSimulationRuns: vi.fn().mockResolvedValue([]),
  startSimulation: vi.fn(),
  getRunStatus: vi.fn(),
  getRunResults: vi.fn(),
  getGameDetail: vi.fn(),
  cancelRun: vi.fn(),
  resumeRun: vi.fn(),
  pauseRun: vi.fn(),
}));

const renderWithQuery = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

const SUMMARY: SummaryStats = {
  users: { total: 12 },
  games: { total: 40, active: 3, completed: 37, recent_24h: 5 },
  ai_logs: { total: 900, recent_1h: 7 },
  playbacks: { total: 30 },
};

describe('SummaryTab', () => {
  it('renders recent activity from summary stats', () => {
    render(<SummaryTab summary={SUMMARY} />);
    expect(screen.getByText('Database Overview')).toBeInTheDocument();
    expect(screen.getByText('5 games started')).toBeInTheDocument();
    expect(screen.getByText('7 AI decisions logged')).toBeInTheDocument();
  });
});

describe('AiLogsTab', () => {
  it('renders the unfiltered header', () => {
    render(<AiLogsTab aiLogsData={{ count: 3, logs: [] }} gameIdFilter={null} onClearFilter={vi.fn()} />);
    expect(screen.getByText(/Showing 3 most recent AI decisions/)).toBeInTheDocument();
  });

  it('renders the game filter banner with a clear button', () => {
    const onClear = vi.fn();
    render(<AiLogsTab aiLogsData={{ count: 1, logs: [] }} gameIdFilter="game-xyz" onClearFilter={onClear} />);
    expect(screen.getByText('game-xyz')).toBeInTheDocument();
    screen.getByText('Clear Filter').click();
    expect(onClear).toHaveBeenCalled();
  });
});

describe('GamesTab', () => {
  it('renders a game row', () => {
    const game: Game = {
      id: 'g1', status: 'active', player1_id: 'p1', player1_name: 'Régis',
      player2_id: 'p2', player2_name: 'Gemiknight', game_code: 'ABCD',
      turn_number: 4, phase: 'Action', winner_id: null,
      created_at: '2026-07-01T10:00:00Z', updated_at: '2026-07-01T10:05:00Z',
    };
    render(<GamesTab gamesData={{ count: 1, games: [game] }} />);
    expect(screen.getByText(/Régis vs Gemiknight/)).toBeInTheDocument();
    expect(screen.getByText(/Turn 4 · Action Phase/)).toBeInTheDocument();
  });
});

describe('PlaybacksTab', () => {
  it('renders the playback list', () => {
    const playback: GamePlayback = {
      id: 1, game_id: 'g1', player1_id: 'p1', player1_name: 'Régis',
      player2_id: 'p2', player2_name: 'Gemiknight', winner_id: 'p1',
      turn_count: 9, created_at: '2026-07-01T10:00:00Z', completed_at: '2026-07-01T10:07:00Z',
    };
    renderWithQuery(
      <PlaybacksTab playbacksData={{ count: 1, games: [playback] }} onNavigateToAiLogs={vi.fn()} />
    );
    expect(screen.getByText(/Showing 1 most recent completed games/)).toBeInTheDocument();
    expect(screen.getByText(/9 turns · 7m 0s/)).toBeInTheDocument();
    expect(screen.getByText('View Playback Details')).toBeInTheDocument();
  });
});

describe('UsersTab', () => {
  it('renders a user row with win rate', () => {
    const user: User = {
      google_id: 'u1', first_name: 'Régis', display_name: 'RegisCA',
      created_at: '2026-06-01T10:00:00Z', updated_at: '2026-06-01T10:00:00Z',
      games_played: 10, games_won: 6, win_rate: 60, avg_turns: 8.4,
      avg_game_duration_seconds: 300, last_game_at: null, last_game_status: null,
      favorite_decks: [],
    };
    render(<UsersTab usersData={{ count: 1, users: [user] }} />);
    expect(screen.getByText('RegisCA')).toBeInTheDocument();
    expect(screen.getByText('60.0%')).toBeInTheDocument();
  });
});

describe('SimulationTab', () => {
  it('renders the configuration panel with fetched decks', async () => {
    renderWithQuery(<SimulationTab />);
    expect(screen.getByText('New Simulation')).toBeInTheDocument();
    expect(await screen.findByText('Aggro')).toBeInTheDocument();
    expect(screen.getByText('Start Simulation')).toBeInTheDocument();
  });

  it('shows a Pause button for a running run in the past-runs list', async () => {
    const { listSimulationRuns } = await import('../../../api/simulationService');
    vi.mocked(listSimulationRuns).mockResolvedValueOnce([
      {
        run_id: 1,
        status: 'running',
        total_games: 20,
        completed_games: 5,
        config: { deck_names: ['Aggro'], player1_model: 'm1', player2_model: 'm2', iterations_per_matchup: 5, max_turns: 20 },
        created_at: '2026-07-01T00:00:00Z',
        completed_at: null,
      },
    ]);
    renderWithQuery(<SimulationTab />);
    expect(await screen.findByText('Pause')).toBeInTheDocument();
    expect(screen.queryByText('Resume')).not.toBeInTheDocument();
  });

  it('shows budget info and a Resume button for a budget_exhausted run', async () => {
    const { listSimulationRuns } = await import('../../../api/simulationService');
    vi.mocked(listSimulationRuns).mockResolvedValueOnce([
      {
        run_id: 2,
        status: 'budget_exhausted',
        total_games: 20,
        completed_games: 8,
        config: { deck_names: ['Aggro'], player1_model: 'm1', player2_model: 'm2', iterations_per_matchup: 5, max_turns: 20 },
        created_at: '2026-07-01T00:00:00Z',
        completed_at: null,
        budget: { used_today: 100, daily_budget: 100, rpm: null, resets_at: '2099-01-01T00:00:00Z' },
      },
    ]);
    renderWithQuery(<SimulationTab />);
    expect(await screen.findByText('Resume')).toBeInTheDocument();
    expect(screen.getByText(/Budget used: 100\/100/)).toBeInTheDocument();
    expect(screen.queryByText('Pause')).not.toBeInTheDocument();
  });

  it('shows no pause/resume buttons for a completed run', async () => {
    const { listSimulationRuns } = await import('../../../api/simulationService');
    vi.mocked(listSimulationRuns).mockResolvedValueOnce([
      {
        run_id: 3,
        status: 'completed',
        total_games: 20,
        completed_games: 20,
        config: { deck_names: ['Aggro'], player1_model: 'm1', player2_model: 'm2', iterations_per_matchup: 5, max_turns: 20 },
        created_at: '2026-07-01T00:00:00Z',
        completed_at: '2026-07-01T01:00:00Z',
      },
    ]);
    renderWithQuery(<SimulationTab />);
    expect(await screen.findByText(/Run #3/)).toBeInTheDocument();
    expect(screen.queryByText('Pause')).not.toBeInTheDocument();
    expect(screen.queryByText('Resume')).not.toBeInTheDocument();
  });
});
