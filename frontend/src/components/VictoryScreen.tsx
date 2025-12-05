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
      className="min-h-screen bg-game-bg flex items-center justify-center relative overflow-auto"
      style={{
        padding: 'var(--spacing-component-lg)',
        backgroundImage: 'url(/ggltcg-logo.svg)',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        backgroundSize: '50%',
        backgroundBlendMode: 'soft-light',
      }}
    >
      {/* Semi-transparent overlay for readability */}
      <div className="absolute inset-0 bg-game-bg bg-opacity-90 pointer-events-none" />

      <div className="relative z-10 w-full max-w-5xl mx-auto">
        {/* Victory Header */}
        <div className="text-center" style={{ marginBottom: 'var(--spacing-component-xl)' }}>
          <h1 className="text-4xl sm:text-6xl font-bold text-game-highlight" style={{ marginBottom: 'var(--spacing-component-md)' }}>
            Game Over!
          </h1>
          <p className="text-2xl sm:text-4xl" style={{ marginBottom: 'var(--spacing-component-lg)' }}>
            {winnerPlayer?.name || gameState.winner} Wins!
          </p>
          {/* Back to Main Menu Button */}
          <Button variant="primary" size="lg" onClick={onPlayAgain}>
            Back to Main Menu
          </Button>
        </div>

        {/* Play-by-Play Summary */}
        {playByPlay.length > 0 && (
          <div className="modal-padding bg-gray-800 bg-opacity-95 rounded-lg shadow-2xl">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-gray-700" 
                 style={{ gap: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-lg)', paddingBottom: 'var(--spacing-component-lg)' }}>
              <h2 className="text-2xl sm:text-3xl font-bold">Game Summary</h2>
              
              {/* Mode Toggle */}
              <div className="flex items-center" style={{ gap: 'var(--spacing-component-md)' }}>
                <button
                  onClick={() => setNarrativeMode(false)}
                  className={`rounded font-semibold transition-all ${
                    !narrativeMode
                      ? 'bg-game-highlight text-white'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }`}
                  style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-lg)' }}
                >
                  📋 Factual
                </button>
                <button
                  onClick={() => setNarrativeMode(true)}
                  disabled={isLoadingNarrative}
                  className={`rounded font-semibold transition-all ${
                    narrativeMode
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  } ${isLoadingNarrative ? 'opacity-50 cursor-wait' : ''}`}
                  style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-lg)' }}
                >
                  {isLoadingNarrative ? '⏳ Loading...' : '📖 Story Mode'}
                </button>
              </div>
            </div>
            
            {/* Narrative Mode */}
            {narrativeMode ? (
              <div className="prose prose-invert max-w-none">
                {isLoadingNarrative ? (
                  <div className="text-center text-gray-400" style={{ paddingTop: 'var(--spacing-component-xl)', paddingBottom: 'var(--spacing-component-xl)' }}>
                    <div className="text-4xl" style={{ marginBottom: 'var(--spacing-component-md)' }}>⏳</div>
                    <p>Generating your epic bedtime story...</p>
                  </div>
                ) : narrative ? (
                  <div className="content-spacing text-gray-100 leading-loose text-base sm:text-lg">
                    {narrative.split('\n\n').map((paragraph, idx) => (
                      <p key={idx} className="text-justify">
                        {paragraph}
                      </p>
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-gray-400" style={{ paddingTop: 'var(--spacing-component-xl)', paddingBottom: 'var(--spacing-component-xl)' }}>
                    <p>No narrative available</p>
                  </div>
                )}
              </div>
            ) : (
              /* Factual Mode */
              <div className="content-spacing">
              {Object.entries(groupedActions).map(([key, actions]) => {
                const firstAction = actions[0];
                const isAI = firstAction.reasoning !== undefined;
                
                return (
                  <div
                    key={key}
                    className={`card-padding rounded-lg border-l-4 ${
                      isAI 
                        ? 'bg-purple-900 bg-opacity-20 border-purple-500' 
                        : 'bg-gray-900 bg-opacity-70 border-game-highlight'
                    }`}
                  >
                    {/* Turn and Player Header */}
                    <div className="flex items-center border-b border-gray-700" style={{ gap: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-sm)', paddingBottom: 'var(--spacing-component-xs)' }}>
                      <span className="bg-gray-700 text-gray-300 text-xs font-mono rounded" style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-xs)' }}>
                        Turn {firstAction.turn}
                      </span>
                      <span className="font-bold text-white text-base sm:text-lg">
                        {firstAction.player}
                      </span>
                    </div>
                    
                    {/* Actions for this turn/player */}
                    <div className="content-spacing">
                      {actions.map((entry, index) => (
                        <div key={index}>
                          {/* Action Description */}
                          <p className="text-gray-100 leading-relaxed" style={{ paddingLeft: 'var(--spacing-component-xs)' }}>
                            • {entry.description}
                          </p>

                          {/* AI Reasoning */}
                          {entry.reasoning && (
                            <div className="border-t border-purple-700 bg-purple-900 bg-opacity-30 rounded" 
                                 style={{ marginTop: 'var(--spacing-component-xs)', marginLeft: 'var(--spacing-component-sm)', paddingTop: 'var(--spacing-component-xs)', padding: 'var(--spacing-component-sm)' }}>
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
              <div className="border-t border-gray-700 text-center" style={{ marginTop: 'var(--spacing-component-xl)', paddingTop: 'var(--spacing-component-lg)' }}>
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
