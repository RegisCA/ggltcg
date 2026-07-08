/**
 * Small ink-toned pill for game/run/playback status strings. Centralizes the
 * status -> tone mapping so all tabs style statuses consistently, using the
 * Paper & Ink theme tokens from index.css (--gold, --danger, --ink-*) rather
 * than saturated Tailwind palette colors that clash with the theme.
 */

import React from 'react';

type StatusTone = 'active' | 'done' | 'warn' | 'danger' | 'neutral';

const STATUS_TONES: Record<string, StatusTone> = {
  active: 'active',
  running: 'active',
  in_progress: 'active',
  completed: 'done',
  finished: 'done',
  pending: 'warn',
  fallback: 'warn',
  failed: 'danger',
  error: 'danger',
  cancelled: 'neutral',
  abandoned: 'neutral',
};

// Muted, on-ink styles: faint tinted text + hairline border on a translucent
// panel background, matching how the main UI colors secondary state.
const TONE_STYLES: Record<StatusTone, React.CSSProperties> = {
  active: { color: 'var(--gold)', borderColor: 'var(--gold)' },
  done: { color: 'var(--ink-muted)', borderColor: 'var(--ink-faint)' },
  warn: { color: 'var(--gold)', borderColor: 'var(--ink-faint)' },
  danger: { color: 'var(--danger)', borderColor: 'var(--danger)' },
  neutral: { color: 'var(--ink-faint)', borderColor: 'var(--ink-faint)' },
};

const toneFor = (status: string): StatusTone => STATUS_TONES[status.toLowerCase()] ?? 'neutral';

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className }) => (
  <span
    className={`text-xs rounded border bg-black/20 ${className ?? ''}`}
    style={{ padding: '2px var(--spacing-component-xs)', ...TONE_STYLES[toneFor(status)] }}
  >
    {status}
  </span>
);

export default StatusBadge;
