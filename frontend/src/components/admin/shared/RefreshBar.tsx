/**
 * Per-tab manual refresh control: a "Refresh" button plus "updated Xs ago"
 * text driven by the query's dataUpdatedAt. Ticks its own display once a
 * second so the "ago" text stays fresh without needing a query refetch.
 */

import React, { useEffect, useState } from 'react';

interface RefreshBarProps {
  dataUpdatedAt: number | undefined;
  onRefresh: () => void;
  isFetching?: boolean;
}

const formatSecondsAgo = (updatedAt: number | undefined, now: number): string => {
  if (!updatedAt) return 'never';
  const diffSec = Math.max(0, Math.floor((now - updatedAt) / 1000));
  if (diffSec < 1) return 'just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.floor(diffMin / 60);
  return `${diffHour}h ago`;
};

const RefreshBar: React.FC<RefreshBarProps> = ({ dataUpdatedAt, onRefresh, isFetching }) => {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
      <span className="text-xs text-[var(--ink-faint)]">
        updated {formatSecondsAgo(dataUpdatedAt, now)}
      </span>
      <button
        onClick={onRefresh}
        disabled={isFetching}
        className="bg-white/10 hover:bg-white/15 disabled:opacity-50 text-[var(--ink-text)] rounded text-xs"
        style={{ padding: '4px var(--spacing-component-sm)' }}
      >
        {isFetching ? 'Refreshing…' : 'Refresh'}
      </button>
    </div>
  );
};

export default RefreshBar;
