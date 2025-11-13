/**
 * Victory Screen Component
 * Displays game winner with play-by-play summary and AI reasoning
 */

import type { GameState } from '../types/game';

interface VictoryScreenProps {
  gameState: GameState;
  onPlayAgain: () => void;
}

export function VictoryScreen({ gameState, onPlayAgain }: VictoryScreenProps) {
  const winnerPlayer = gameState.players[gameState.winner || ''];
  const playByPlay = gameState.play_by_play || [];

  // Debug: Log the play-by-play data
  console.log('VictoryScreen - playByPlay:', playByPlay);
  console.log('VictoryScreen - playByPlay.length:', playByPlay.length);
  console.log('VictoryScreen - full gameState:', gameState);

  // Group actions by turn and player
  const groupedActions: Record<string, typeof playByPlay> = {};
  playByPlay.forEach((entry) => {
    const key = `${entry.turn}-${entry.player}`;
    if (!groupedActions[key]) {
      groupedActions[key] = [];
    }
    groupedActions[key].push(entry);
  });

  return (
    <div 
      className="min-h-screen bg-game-bg p-8 relative overflow-auto"
      style={{
        backgroundImage: 'url(/ggltcg-logo.svg)',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        backgroundSize: '50%',
        backgroundBlendMode: 'soft-light',
      }}
    >
      {/* Semi-transparent overlay for readability */}
      <div className="absolute inset-0 bg-game-bg bg-opacity-90 pointer-events-none" />

      {/* Play Again Button - Top Right Corner */}
      <button
        onClick={onPlayAgain}
        className="absolute top-8 right-8 z-20 px-6 py-3 bg-game-highlight hover:bg-red-600 rounded text-xl font-bold transition-all shadow-lg"
      >
        Play Again
      </button>

      <div className="relative z-10 max-w-5xl mx-auto">
        {/* Victory Header */}
        <div className="text-center mb-8">
          <h1 className="text-6xl font-bold mb-4 text-game-highlight">
            Game Over!
          </h1>
          <p className="text-4xl mb-6">
            {winnerPlayer?.name || gameState.winner} Wins!
          </p>
        </div>

        {/* Play-by-Play Summary */}
        {playByPlay.length > 0 && (
          <div className="bg-gray-800 bg-opacity-95 rounded-lg p-8 shadow-2xl max-w-3xl mx-auto">
            <h2 className="text-3xl font-bold mb-6 text-center border-b border-gray-700 pb-4">Game Summary</h2>
            
            <div className="space-y-4">
              {Object.entries(groupedActions).map(([key, actions]) => {
                const firstAction = actions[0];
                const isAI = firstAction.reasoning !== undefined;
                
                return (
                  <div
                    key={key}
                    className={`rounded-lg p-4 border-l-4 ${
                      isAI 
                        ? 'bg-purple-900 bg-opacity-20 border-purple-500' 
                        : 'bg-gray-900 bg-opacity-70 border-game-highlight'
                    }`}
                  >
                    {/* Turn and Player Header */}
                    <div className="flex items-center gap-3 mb-3 pb-2 border-b border-gray-700">
                      <span className="bg-gray-700 text-gray-300 text-xs font-mono px-2 py-1 rounded">
                        Turn {firstAction.turn}
                      </span>
                      <span className="font-bold text-white text-lg">
                        {firstAction.player}
                      </span>
                    </div>
                    
                    {/* Actions for this turn/player */}
                    <div className="space-y-2">
                      {actions.map((entry, index) => (
                        <div key={index}>
                          {/* Action Description */}
                          <p className="text-gray-100 leading-relaxed pl-2">
                            • {entry.description}
                          </p>

                          {/* AI Reasoning */}
                          {entry.reasoning && (
                            <div className="mt-2 ml-4 pt-2 border-t border-purple-700 bg-purple-900 bg-opacity-30 p-3 rounded">
                              <p className="text-sm text-purple-200 italic leading-relaxed">
                                <span className="text-purple-300 font-semibold not-italic">💭 AI Strategy:</span> {entry.reasoning}
                              </p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* AI Endpoint Summary */}
            {playByPlay.some(entry => entry.ai_endpoint) && (
              <div className="mt-8 pt-6 border-t border-gray-700 text-center">
                <p className="text-sm text-gray-400">
                  🤖 AI decisions powered by{' '}
                  <span className="text-purple-300 font-semibold">
                    {Array.from(new Set(playByPlay.filter(e => e.ai_endpoint).map(e => e.ai_endpoint))).join(', ')}
                  </span>
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
