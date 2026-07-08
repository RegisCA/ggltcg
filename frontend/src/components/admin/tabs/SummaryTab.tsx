/**
 * Summary tab — database overview. JSX moved verbatim from AdminDataViewer.tsx.
 */

import React from 'react';
import type { SummaryStats } from '../types';

interface SummaryTabProps {
  summary: SummaryStats | undefined;
}

const SummaryTab: React.FC<SummaryTabProps> = ({ summary }) => (
  <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-lg)' }}>
    <h2 className="text-2xl font-bold" style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-md)' }}>Database Overview</h2>
    <p className="text-[var(--ink-faint)]" style={{ marginBottom: 'var(--spacing-component-md)' }}>
      Use the tabs above to view AI decision logs, game data, and playback recordings.
    </p>
    <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
      <div>
        <h3 className="font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>Recent Activity (Last 24h)</h3>
        <p className="text-[var(--ink-faint)]">{summary?.games.recent_24h || 0} games started</p>
      </div>
      <div>
        <h3 className="font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>AI Activity (Last Hour)</h3>
        <p className="text-[var(--ink-faint)]">{summary?.ai_logs.recent_1h || 0} AI decisions logged</p>
      </div>
    </div>
  </div>
);

export default SummaryTab;
