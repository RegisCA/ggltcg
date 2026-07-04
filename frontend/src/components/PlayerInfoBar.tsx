/**
 * PlayerInfoBar Component
 * Compact player info for header display
 */

import type { Player } from '../types/game';

interface PlayerInfoBarProps {
  player: Player;
  isActive: boolean;
  isCompact?: boolean;  // Tighter type/spacing so two bars fit side by side at phone widths
}

export function PlayerInfoBar({ player, isActive, isCompact = false }: PlayerInfoBarProps) {
  // Use hand_count if available (for AI player), otherwise count hand array
  const handCount = player.hand_count ?? player.hand?.length ?? 0;

  return (
    // We keep the parent flex container and items-center for vertical alignment
    <div
      className={`flex items-center ${isActive ? 'font-extrabold' : ''}`}
      style={{ gap: isCompact ? 'var(--spacing-component-xs)' : 'var(--spacing-component-md)', minWidth: 0 }}
    >

      {/* 1. Player Name (truncates instead of overlapping neighbors,
          but always keeps a few characters visible for identity) */}
      <span className={`${isCompact ? 'text-sm' : 'text-lg'} truncate`} style={{ minWidth: '4ch' }}>
        {player.name}
      </span>

      {/* 2. Hand Count (Bigger Number, Smaller Label) */}
      <div className="flex items-end leading-none flex-shrink-0" style={{ gap: 'var(--spacing-component-xs)' }}>
        <span className={`${isCompact ? 'text-lg' : 'text-2xl'} font-bold`}>({handCount})</span>
        <span className={`${isCompact ? 'text-xs' : 'text-sm'} text-gray-400`}>Hand</span>
      </div>

      <span className={`${isCompact ? 'text-xs' : 'text-sm'} text-gray-400 flex-shrink-0`}>|</span>

      {/* 3. Charge Count (Bigger Number, Smaller Label) */}
      <div className="flex items-end leading-none flex-shrink-0" style={{ gap: 'var(--spacing-component-xs)' }}>
        <span className={`${isCompact ? 'text-lg' : 'text-2xl'} font-bold`}>{player.charge}</span>
        <span className={`${isCompact ? 'text-xs' : 'text-sm'} text-gray-400`}>Charge</span>
      </div>
    </div>
  );
}
