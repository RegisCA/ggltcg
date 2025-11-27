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
    <div className="bg-purple-900/20 border-b-2 border-purple-500/50 p-3 mb-4">
      <div className="max-w-7xl mx-auto grid grid-cols-[1fr_auto_1fr] gap-6 items-center">
        {/* Player 1 - Right aligned */}
        <div className="text-right">
          <div className="text-sm text-gray-400 mb-1">Player 1</div>
          <div className="font-bold text-lg">
            {player1Name} {currentPlayerId === 'player1' && <span className="text-game-highlight">(You)</span>}
          </div>
        </div>
        
        {/* VS divider */}
        <div className="text-2xl font-bold text-gray-500 px-4">VS</div>
        
        {/* Player 2 - Left aligned */}
        <div className="text-left">
          <div className="text-sm text-gray-400 mb-1">Player 2</div>
          <div className="font-bold text-lg">
            {player2Name} {currentPlayerId === 'player2' && <span className="text-game-highlight">(You)</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
