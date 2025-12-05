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
  backLabel = 'Leave Lobby' 
}: LobbyHeaderProps) {
  return (
    <div className="bg-gray-800 border-b-2 border-gray-600" style={{ padding: 'var(--spacing-component-md)' }}>
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        <button
          onClick={onBack}
          className="text-gray-400 hover:text-game-highlight transition-colors flex items-center"
          style={{ gap: 'var(--spacing-component-xs)' }}
        >
          <span>←</span> {backLabel}
        </button>

        <div className="text-center">
          <div className="text-sm text-gray-400" style={{ marginBottom: '4px' }}>Game Code</div>
          <GameCodeDisplay code={gameCode} size="small" showLabel={false} />
        </div>

        <div className="w-24"></div> {/* Spacer for centering */}
      </div>
    </div>
  );
}
