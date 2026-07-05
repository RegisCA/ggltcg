/**
 * LobbyHeader Component
 *
 * Header bar for lobby screens showing:
 * - Back/Leave button
 * - Game code (centered)
 * - Optional spacer for layout balance
 */

import { GameCodeDisplay } from './GameCodeDisplay';

interface LobbyHeaderProps {
  gameCode: string;
  onBack: () => void;
  backLabel?: string;
}

export function LobbyHeader({
  gameCode,
  onBack,
  backLabel = 'Leave Lobby',
}: LobbyHeaderProps) {
  return (
    <div
      style={{
        background: 'var(--desk-top)',
        borderBottom: '1px solid rgba(237,232,222,.15)',
        padding: 'var(--spacing-component-md)',
      }}
    >
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        <button
          onClick={onBack}
          className="flex items-center transition-colors"
          style={{
            gap: 'var(--spacing-component-xs)',
            color: 'var(--ink-muted)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontWeight: 700,
            fontSize: '13px',
          }}
        >
          <span>←</span> {backLabel}
        </button>

        <div className="text-center">
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--ink-faint)', marginBottom: '4px' }}>
            Game Code
          </div>
          <GameCodeDisplay code={gameCode} size="small" showLabel={false} />
        </div>

        <div className="w-24" aria-hidden="true" />
      </div>
    </div>
  );
}
