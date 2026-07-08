/**
 * Admin data viewer for GGLTCG database.
 *
 * Shell component: header, summary stat cards, tab navigation, and the
 * cross-tab "view AI logs for game X" handoff. Tab content lives in
 * ./tabs/*; queries live in the useAdminData / useSimulationRuns hooks.
 * Split out of AdminDataViewer.tsx (PR A2) — behavior-preserving.
 *
 * PR A3 adds: URL-hash-backed tab/filter state (useHashTab, so deep links
 * survive a refresh), per-tab manual refresh controls, and clickable
 * summary stat cards that jump to the corresponding tab.
 */

import React from 'react';
import {
  useSummary,
  useAiLogs,
  useGames,
  usePlaybacks,
  useUsers,
} from '../../hooks/useAdminData';
import { useHashTab } from '../../hooks/useHashTab';
import SummaryTab from './tabs/SummaryTab';
import AiLogsTab from './tabs/AiLogsTab';
import GamesTab from './tabs/GamesTab';
import PlaybacksTab from './tabs/PlaybacksTab';
import UsersTab from './tabs/UsersTab';
import SimulationTab from './tabs/SimulationTab';
import RefreshBar from './shared/RefreshBar';

type AdminTab = 'summary' | 'ai-logs' | 'games' | 'playbacks' | 'users' | 'simulation';

const ADMIN_TABS: readonly AdminTab[] = ['summary', 'ai-logs', 'games', 'playbacks', 'users', 'simulation'];

const AdminApp: React.FC = () => {
  const { tab: activeTab, filter: aiLogsGameIdFilter, setTab: setActiveTab, setTabAndFilter, setFilter } =
    useHashTab<AdminTab>(ADMIN_TABS, 'summary', 'game_id', 'ai-logs');

  const summaryQuery = useSummary();
  const aiLogsQuery = useAiLogs(aiLogsGameIdFilter, activeTab === 'ai-logs');
  const gamesQuery = useGames(activeTab === 'games');
  const playbacksQuery = usePlaybacks(activeTab === 'playbacks');
  const usersQuery = useUsers(activeTab === 'users');

  const summary = summaryQuery.data;
  const aiLogsData = aiLogsQuery.data;
  const gamesData = gamesQuery.data;
  const playbacksData = playbacksQuery.data;
  const usersData = usersQuery.data;

  const viewAILogsForGame = (gameId: string) => {
    setTabAndFilter('ai-logs', gameId);
  };

  const clearAILogsFilter = () => {
    setFilter(null);
  };

  const tabButtonClass = (tab: AdminTab) =>
    `px-4 py-2 font-semibold ${
      activeTab === tab
        ? 'text-[var(--gold)] border-b-2 border-[var(--gold)]'
        : 'text-[var(--ink-faint)] hover:text-[var(--ink-text)]'
    }`;

  const statCardClass =
    'bg-panel rounded-lg border border-white/10 text-left hover:border-[var(--gold)]/50 hover:bg-white/5 cursor-pointer transition-colors w-full';

  // Per-active-tab refresh control, shown next to the tab content.
  const activeRefresh = (() => {
    switch (activeTab) {
      case 'summary':
        return { dataUpdatedAt: summaryQuery.dataUpdatedAt, isFetching: summaryQuery.isFetching, onRefresh: summaryQuery.refetch };
      case 'ai-logs':
        return { dataUpdatedAt: aiLogsQuery.dataUpdatedAt, isFetching: aiLogsQuery.isFetching, onRefresh: aiLogsQuery.refetch };
      case 'games':
        return { dataUpdatedAt: gamesQuery.dataUpdatedAt, isFetching: gamesQuery.isFetching, onRefresh: gamesQuery.refetch };
      case 'playbacks':
        return { dataUpdatedAt: playbacksQuery.dataUpdatedAt, isFetching: playbacksQuery.isFetching, onRefresh: playbacksQuery.refetch };
      case 'users':
        return { dataUpdatedAt: usersQuery.dataUpdatedAt, isFetching: usersQuery.isFetching, onRefresh: usersQuery.refetch };
      default:
        return null;
    }
  })();

  return (
    <div className="min-h-screen bg-desk text-[var(--ink-text)]" style={{ padding: 'var(--spacing-component-lg)' }}>
      <div className="max-w-7xl mx-auto">
        <h1
          className="text-3xl text-[var(--gold)]"
          style={{ marginBottom: 'var(--spacing-component-lg)', fontFamily: 'var(--font-card-name)' }}
        >
          GGLTCG Admin Data Viewer
        </h1>

        {/* Summary Stats — clickable, navigate to the corresponding tab */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4" style={{ gap: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-lg)' }}>
            <button className={statCardClass} style={{ padding: 'var(--spacing-component-md)' }} onClick={() => setActiveTab('users')}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>Total Users</h3>
              <p className="text-2xl font-bold">{summary.users.total}</p>
            </button>
            <button className={statCardClass} style={{ padding: 'var(--spacing-component-md)' }} onClick={() => setActiveTab('games')}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>Games</h3>
              <p className="text-2xl font-bold">{summary.games.total}</p>
              <p className="text-xs text-[var(--ink-faint)]" style={{ marginTop: '4px' }}>
                {summary.games.active} active · {summary.games.completed} completed
              </p>
            </button>
            <button className={statCardClass} style={{ padding: 'var(--spacing-component-md)' }} onClick={() => setActiveTab('ai-logs')}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>AI Logs</h3>
              <p className="text-2xl font-bold">{summary.ai_logs.total}</p>
              <p className="text-xs text-[var(--ink-faint)]" style={{ marginTop: '4px' }}>
                {summary.ai_logs.recent_1h} in last hour
              </p>
            </button>
            <button className={statCardClass} style={{ padding: 'var(--spacing-component-md)' }} onClick={() => setActiveTab('playbacks')}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>Playbacks</h3>
              <p className="text-2xl font-bold">{summary.playbacks.total}</p>
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex justify-between items-center border-b border-white/10" style={{ marginBottom: 'var(--spacing-component-lg)' }}>
          <div className="flex" style={{ gap: 'var(--spacing-component-md)' }}>
            <button className={tabButtonClass('summary')} onClick={() => setActiveTab('summary')}>
              Summary
            </button>
            <button className={tabButtonClass('ai-logs')} onClick={() => setActiveTab('ai-logs')}>
              AI Logs ({aiLogsData?.count || 0})
            </button>
            <button className={tabButtonClass('games')} onClick={() => setActiveTab('games')}>
              Games ({gamesData?.count || 0})
            </button>
            <button className={tabButtonClass('playbacks')} onClick={() => setActiveTab('playbacks')}>
              Playbacks ({playbacksData?.count || 0})
            </button>
            <button className={tabButtonClass('users')} onClick={() => setActiveTab('users')}>
              Users ({usersData?.count || 0})
            </button>
            <button className={tabButtonClass('simulation')} onClick={() => setActiveTab('simulation')}>
              Simulation
            </button>
          </div>
          {activeRefresh && (
            <RefreshBar
              dataUpdatedAt={activeRefresh.dataUpdatedAt}
              isFetching={activeRefresh.isFetching}
              onRefresh={() => activeRefresh.onRefresh()}
            />
          )}
        </div>

        {/* Content */}
        {activeTab === 'summary' && <SummaryTab summary={summary} />}
        {activeTab === 'ai-logs' && (
          <AiLogsTab
            aiLogsData={aiLogsData}
            gameIdFilter={aiLogsGameIdFilter}
            onClearFilter={clearAILogsFilter}
          />
        )}
        {activeTab === 'games' && <GamesTab gamesData={gamesData} />}
        {activeTab === 'playbacks' && (
          <PlaybacksTab playbacksData={playbacksData} onNavigateToAiLogs={viewAILogsForGame} />
        )}
        {activeTab === 'users' && <UsersTab usersData={usersData} />}
        {activeTab === 'simulation' && <SimulationTab />}
      </div>
    </div>
  );
};

export default AdminApp;
