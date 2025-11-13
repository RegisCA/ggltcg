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
    <div className={`flex items-center gap-2 ${isActive ? 'font-bold' : ''}`}>
      <span className="text-lg">{player.name}</span>
      <span className="text-sm text-gray-400">Hand ({handCount})</span>
      <span className="text-sm text-gray-400">|</span>
      <span className="text-lg">{player.cc} CC</span>
    </div>
  );
}
