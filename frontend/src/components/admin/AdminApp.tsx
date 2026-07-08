/**
 * Admin data viewer for GGLTCG database.
 *
 * Shell component: header, summary stat cards, tab navigation, and the
 * cross-tab "view AI logs for game X" handoff. Tab content lives in
 * ./tabs/*; queries live in the useAdminData / useSimulationRuns hooks.
 * Split out of AdminDataViewer.tsx (PR A2) — behavior-preserving.
 */

import React, { useState } from 'react';
import {
  useSummary,
  useAiLogs,
  useGames,
  usePlaybacks,
  useUsers,
} from '../../hooks/useAdminData';
import SummaryTab from './tabs/SummaryTab';
import AiLogsTab from './tabs/AiLogsTab';
import GamesTab from './tabs/GamesTab';
import PlaybacksTab from './tabs/PlaybacksTab';
import UsersTab from './tabs/UsersTab';
import SimulationTab from './tabs/SimulationTab';
import MaintenanceTab from './tabs/MaintenanceTab';

type AdminTab = 'summary' | 'ai-logs' | 'games' | 'playbacks' | 'users' | 'simulation' | 'maintenance';

const AdminApp: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AdminTab>('summary');
  const [aiLogsGameIdFilter, setAiLogsGameIdFilter] = useState<string | null>(null);

  const { data: summary } = useSummary();
  const { data: aiLogsData } = useAiLogs(aiLogsGameIdFilter, activeTab === 'ai-logs');
  const { data: gamesData } = useGames(activeTab === 'games');
  const { data: playbacksData } = usePlaybacks(activeTab === 'playbacks');
  const { data: usersData } = useUsers(activeTab === 'users');

  const viewAILogsForGame = (gameId: string) => {
    setAiLogsGameIdFilter(gameId);
    setActiveTab('ai-logs');
  };

  const clearAILogsFilter = () => {
    setAiLogsGameIdFilter(null);
  };

  const tabButtonClass = (tab: AdminTab) =>
    `px-4 py-2 font-semibold ${
      activeTab === tab
        ? 'text-[var(--gold)] border-b-2 border-[var(--gold)]'
        : 'text-[var(--ink-faint)] hover:text-[var(--ink-text)]'
    }`;

  return (
    <div className="min-h-screen bg-desk text-[var(--ink-text)]" style={{ padding: 'var(--spacing-component-lg)' }}>
      <div className="max-w-7xl mx-auto">
        <h1
          className="text-3xl text-[var(--gold)]"
          style={{ marginBottom: 'var(--spacing-component-lg)', fontFamily: 'var(--font-card-name)' }}
        >
          GGLTCG Admin Data Viewer
        </h1>

        {/* Summary Stats */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4" style={{ gap: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-lg)' }}>
            <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>Total Users</h3>
              <p className="text-2xl font-bold">{summary.users.total}</p>
            </div>
            <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>Games</h3>
              <p className="text-2xl font-bold">{summary.games.total}</p>
              <p className="text-xs text-[var(--ink-faint)]" style={{ marginTop: '4px' }}>
                {summary.games.active} active · {summary.games.completed} completed
              </p>
            </div>
            <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>AI Logs</h3>
              <p className="text-2xl font-bold">{summary.ai_logs.total}</p>
              <p className="text-xs text-[var(--ink-faint)]" style={{ marginTop: '4px' }}>
                {summary.ai_logs.recent_1h} in last hour
              </p>
            </div>
            <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>Playbacks</h3>
              <p className="text-2xl font-bold">{summary.playbacks.total}</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-white/10" style={{ gap: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-lg)' }}>
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
          <button className={tabButtonClass('maintenance')} onClick={() => setActiveTab('maintenance')}>
            Maintenance
          </button>
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
        {activeTab === 'maintenance' && <MaintenanceTab />}
      </div>
    </div>
  );
};

export default AdminApp;
