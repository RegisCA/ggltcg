/**
 * Victory Screen Component
 * Displays game winner with play-by-play summary and AI reasoning
 */

import { useState, useEffect, useMemo } from 'react';
import { Button } from './ui/Button';
import type { GameState } from '../types/game';
import { generateNarrative } from '../api/gameService';

interface VictoryScreenProps {
  gameState: GameState;
  onPlayAgain: () => void;
}

export function VictoryScreen({ gameState, onPlayAgain }: VictoryScreenProps) {
  const winnerPlayer = gameState.players[gameState.winner || ''];
  const playByPlay = useMemo(() => gameState.play_by_play || [], [gameState.play_by_play]);
  const [narrativeMode, setNarrativeMode] = useState(false);
  const [narrative, setNarrative] = useState<string>('');
  const [isLoadingNarrative, setIsLoadingNarrative] = useState(false);

  // Load narrative when mode is switched
  useEffect(() => {
    if (narrativeMode && !narrative && playByPlay.length > 0) {
      setIsLoadingNarrative(true);
      generateNarrative(playByPlay)
        .then((narrativeText) => {
          setNarrative(narrativeText);
        })
        .catch((error) => {
          console.error('Failed to generate narrative:', error);
          alert('Failed to generate narrative story. Please try again.');
          setNarrativeMode(false); // Fall back to factual mode
        })
        .finally(() => {
          setIsLoadingNarrative(false);
        });
    }
  }, [narrativeMode, narrative, playByPlay]);

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
      className="min-h-screen bg-game-bg flex items-center justify-center p-4 sm:p-8 relative overflow-auto"
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
      <div className="absolute top-4 sm:top-8 right-4 sm:right-8 z-20">
        <Button variant="primary" size="lg" onClick={onPlayAgain}>
          Play Again
        </Button>
      </div>

      <div className="relative z-10 w-full max-w-5xl mx-auto px-4 sm:px-6">
        {/* Victory Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl sm:text-6xl font-bold mb-4 text-game-highlight">
            Game Over!
          </h1>
          <p className="text-2xl sm:text-4xl mb-6">
            {winnerPlayer?.name || gameState.winner} Wins!
          </p>
        </div>

        {/* Play-by-Play Summary */}
        {playByPlay.length > 0 && (
          <div className="bg-gray-800 bg-opacity-95 rounded-lg p-6 sm:p-8 shadow-2xl">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 pb-4 border-b border-gray-700">
              <h2 className="text-2xl sm:text-3xl font-bold">Game Summary</h2>
              
              {/* Mode Toggle */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setNarrativeMode(false)}
                  className={`px-4 py-2 rounded font-semibold transition-all ${
                    !narrativeMode
                      ? 'bg-game-highlight text-white'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }`}
                >
                  📋 Factual
                </button>
                <button
                  onClick={() => setNarrativeMode(true)}
                  disabled={isLoadingNarrative}
                  className={`px-4 py-2 rounded font-semibold transition-all ${
                    narrativeMode
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  } ${isLoadingNarrative ? 'opacity-50 cursor-wait' : ''}`}
                >
                  {isLoadingNarrative ? '⏳ Loading...' : '📖 Story Mode'}
                </button>
              </div>
            </div>
            
            {/* Narrative Mode */}
            {narrativeMode ? (
              <div className="prose prose-invert max-w-none">
                {isLoadingNarrative ? (
                  <div className="text-center py-8 text-gray-400">
                    <div className="text-4xl mb-4">⏳</div>
                    <p>Generating your epic bedtime story...</p>
                  </div>
                ) : narrative ? (
                  <div className="text-gray-100 leading-loose space-y-4 text-base sm:text-lg px-2">
                    {narrative.split('\n\n').map((paragraph, idx) => (
                      <p key={idx} className="text-justify">
                        {paragraph}
                      </p>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <p>No narrative available</p>
                  </div>
                )}
              </div>
            ) : (
              /* Factual Mode */
              <div className="space-y-4">
              {Object.entries(groupedActions).map(([key, actions]) => {
                const firstAction = actions[0];
                const isAI = firstAction.reasoning !== undefined;
                
                return (
                  <div
                    key={key}
                    className={`rounded-lg p-4 sm:p-6 border-l-4 ${
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
                      <span className="font-bold text-white text-base sm:text-lg">
                        {firstAction.player}
                      </span>
                    </div>
                    
                    {/* Actions for this turn/player */}
                    <div className="space-y-2 px-2">
                      {actions.map((entry, index) => (
                        <div key={index}>
                          {/* Action Description */}
                          <p className="text-gray-100 leading-relaxed pl-2">
                            • {entry.description}
                          </p>

                          {/* AI Reasoning */}
                          {entry.reasoning && (
                            <div className="mt-2 ml-2 sm:ml-4 pt-2 border-t border-purple-700 bg-purple-900 bg-opacity-30 p-3 rounded">
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
            )}

            {/* AI Endpoint Summary - Only show in factual mode */}
            {!narrativeMode && playByPlay.some(entry => entry.ai_endpoint) && (
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
