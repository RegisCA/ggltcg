/**
 * Small colored pill for game/run/playback status strings. Centralizes the
 * status -> color mapping that was previously duplicated inline per tab
 * (GamesTab's status pill, etc.) so new tabs get consistent styling.
 */

import React from 'react';

const STATUS_COLOR_CLASSES: Record<string, string> = {
  active: 'bg-green-600',
  running: 'bg-green-600',
  in_progress: 'bg-green-600',
  completed: 'bg-blue-600',
  finished: 'bg-blue-600',
  pending: 'bg-yellow-600',
  fallback: 'bg-yellow-600',
  failed: 'bg-red-600',
  error: 'bg-red-600',
  cancelled: 'bg-white/10',
  abandoned: 'bg-white/10',
};

const colorClassFor = (status: string): string =>
  STATUS_COLOR_CLASSES[status.toLowerCase()] ?? 'bg-white/10';

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className }) => (
  <span
    className={`text-xs rounded ${colorClassFor(status)} ${className ?? ''}`}
    style={{ padding: '4px var(--spacing-component-xs)' }}
  >
    {status}
  </span>
);

export default StatusBadge;
