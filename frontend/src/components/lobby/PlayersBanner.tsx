/**
 * PlayersBanner Component
 * 
 * Compact banner showing both players in a VS format.
 * Used during deck selection to show who's playing.
 */

interface PlayersBannerProps {
  player1Name: string;
  player2Name: string;
  currentPlayerId: 'player1' | 'player2';
}

export function PlayersBanner({ 
  player1Name, 
  player2Name, 
  currentPlayerId 
}: PlayersBannerProps) {
  return (
    <div className="bg-purple-900/20 border-b-2 border-purple-500/50" style={{ padding: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-md)' }}>
      <div className="max-w-7xl mx-auto grid grid-cols-[1fr_auto_1fr] items-center" style={{ gap: 'var(--spacing-component-lg)' }}>
        {/* Player 1 - Right aligned */}
        <div className="text-right">
          <div className="text-sm text-gray-400" style={{ marginBottom: '4px' }}>Player 1</div>
          <div className="font-bold text-lg">
            {player1Name} {currentPlayerId === 'player1' && <span className="text-game-highlight">(You)</span>}
          </div>
        </div>
        
        {/* VS divider */}
        <div className="text-2xl font-bold text-gray-500" style={{ paddingLeft: 'var(--spacing-component-md)', paddingRight: 'var(--spacing-component-md)' }}>VS</div>
        
        {/* Player 2 - Left aligned */}
        <div className="text-left">
          <div className="text-sm text-gray-400" style={{ marginBottom: '4px' }}>Player 2</div>
          <div className="font-bold text-lg">
            {player2Name} {currentPlayerId === 'player2' && <span className="text-game-highlight">(You)</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
