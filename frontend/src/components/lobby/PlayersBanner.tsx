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
    <div className="bg-purple-900/20 border-b-2 border-purple-500/50 p-3">
      <div className="max-w-7xl mx-auto flex justify-center gap-8 text-center">
        <div>
          <div className="text-sm text-gray-400">Player 1</div>
          <div className="font-bold text-lg">
            {player1Name} {currentPlayerId === 'player1' && '(You)'}
          </div>
        </div>
        <div className="text-2xl text-gray-600">vs</div>
        <div>
          <div className="text-sm text-gray-400">Player 2</div>
          <div className="font-bold text-lg">
            {player2Name} {currentPlayerId === 'player2' && '(You)'}
          </div>
        </div>
      </div>
    </div>
  );
}
