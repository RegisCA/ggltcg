/**
 * PlayerInfoBar Component
 * Compact player info for header display
 */

import type { Player } from '../types/game';

interface PlayerInfoBarProps {
  player: Player;
  isActive: boolean;
}

export function PlayerInfoBar({ player, isActive }: PlayerInfoBarProps) {
  // Use hand_count if available (for AI player), otherwise count hand array
  const handCount = player.hand_count ?? player.hand?.length ?? 0;
  
  return (
    // We keep the parent flex container and items-center for vertical alignment
    <div className={`flex items-center ${isActive ? 'font-extrabold' : ''}`} style={{ gap: 'var(--spacing-component-md)' }}>
      
      {/* 1. Player Name (Standard Size) */}
      <span className="text-lg">{player.name}</span>

      {/* 2. Hand Count (Bigger Number, Smaller Label) */}
      <div className="flex items-end leading-none" style={{ gap: 'var(--spacing-component-xs)' }}>
        <span className="text-2xl font-bold">({handCount})</span>
        <span className="text-sm text-gray-400">Hand</span>
      </div>

      <span className="text-sm text-gray-400">|</span>
      
      {/* 3. CC Count (Bigger Number, Smaller Label) */}
      <div className="flex items-end leading-none" style={{ gap: 'var(--spacing-component-xs)' }}>
        <span className="text-2xl font-bold">{player.cc}</span>
        <span className="text-sm text-gray-400">CC</span>
      </div>
    </div>
  );
}
