/**
 * PlayersStatusCard Component
 * 
 * Displays both players' status in a lobby:
 * - Player names with "You" indicator
 * - Ready/waiting states
 * - Deck submission status
 */

interface PlayerInfo {
  name: string | null;
  isCurrentPlayer: boolean;
  isReady: boolean;
}

interface PlayersStatusCardProps {
  player1: PlayerInfo;
  player2: PlayerInfo;
}

function PlayerRow({ player, label }: { player: PlayerInfo; label: string }) {
  return (
    <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
      <div className="flex items-center gap-3">
        <div className="text-3xl">🎮</div>
        <div>
          <div className="font-bold text-lg">
            {player.name ? (
              <>
                {player.name}
                {player.isCurrentPlayer && (
                  <span className="text-game-highlight ml-2">(You)</span>
                )}
              </>
            ) : (
              <span className="text-gray-500">Waiting for player...</span>
            )}
          </div>
          <div className="text-sm text-gray-400">{label}</div>
        </div>
      </div>
      <div>
        {player.isReady && (
          <span className="text-green-400 font-semibold">✓ Deck Ready</span>
        )}
      </div>
    </div>
  );
}

export function PlayersStatusCard({ player1, player2 }: PlayersStatusCardProps) {
  return (
    <div className="bg-gray-800 rounded-lg p-8 border-2 border-gray-600">
      <h2 className="text-2xl font-bold mb-6 text-center">Players</h2>
      
      <div className="space-y-4">
        <PlayerRow player={player1} label="Player 1" />
        
        {/* VS Divider */}
        <div className="text-center text-gray-500 font-bold">VS</div>
        
        <PlayerRow player={player2} label="Player 2" />
      </div>
    </div>
  );
}
