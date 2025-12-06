/**
 * PlayerZone Component
 * Displays a player's zones (hand, in play, sleep zone) and stats
 */

import type { Player } from '../types/game';
import { CardDisplay } from './CardDisplay';
import { useResponsive } from '../hooks/useResponsive';

interface PlayerZoneProps {
  player: Player;
  isActive: boolean;
  isHuman: boolean;
  onCardClick?: (cardId: string, zone: 'hand' | 'in_play') => void;
  selectedCard?: string;  // Now expects card ID instead of card name
}

export function PlayerZone({
  player,
  isActive,
  isHuman,
  onCardClick,
  selectedCard,
}: PlayerZoneProps) {
  const { isMobile } = useResponsive();
  
  // Use small cards on mobile for better fit
  const cardSize = isMobile ? 'small' : 'medium';
  
  return (
    <div 
      className={`
        rounded transition-all
        ${isActive ? 'bg-game-accent border-2 border-game-highlight' : 'bg-game-card border border-gray-700'}
      `}
      style={{ padding: 'var(--spacing-component-sm)' }}
    >
      {/* Player Header */}
      <div 
        className="flex justify-between items-center" 
        style={{ 
          marginBottom: 'var(--spacing-component-sm)',
          flexWrap: isMobile ? 'wrap' : 'nowrap',
          gap: isMobile ? 'var(--spacing-component-xs)' : '0',
        }}
      >
        <div style={{ flexShrink: 0 }}>
          <h2 style={{ fontSize: isMobile ? 'var(--font-size-base)' : 'var(--font-size-xl)', fontWeight: 'bold' }}>{player.name}</h2>
          {isActive && (
            <span className="text-xs text-game-highlight font-bold">ACTIVE TURN</span>
          )}
        </div>
        <div className="text-right" style={{ flexShrink: 0 }}>
          <div style={{ fontSize: isMobile ? 'var(--font-size-xl)' : 'var(--font-size-2xl)', fontWeight: 'bold' }}>{player.cc} CC</div>
          <div className="text-xs text-gray-400">Command Counters</div>
        </div>
      </div>

      {/* Content Grid - Zones on left, Sleep on right */}
      <div className="flex" style={{ gap: 'var(--spacing-component-sm)' }}>
        {/* Left side - Main zones (80% width) */}
        <div className="flex-1 flex flex-col" style={{ minWidth: 0, gap: 'var(--spacing-component-sm)' }}>
          {/* For AI: Hand first, then In Play */}
          {/* For Human: In Play first, then Hand */}
          
          {isHuman ? (
            <>
              {/* In Play Zone */}
              <div>
                <h3 className="text-sm font-bold text-gray-400" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
                  IN PLAY ({player.in_play.length})
                </h3>
                <div 
                  className="flex flex-wrap min-h-[180px] bg-black bg-opacity-20 rounded"
                  style={{ gap: 'var(--spacing-component-xs)', padding: 'var(--spacing-component-xs)' }}
                >
                  {player.in_play.length === 0 ? (
                    <div className="text-gray-500 italic text-sm m-auto">No cards in play</div>
                  ) : (
                    player.in_play.map((card) => (
                      <CardDisplay
                        key={card.id}
                        card={card}
                        size={cardSize}
                        isClickable={isHuman && isActive}
                        isSelected={selectedCard === card.id}
                        onClick={() => onCardClick?.(card.id, 'in_play')}
                      />
                    ))
                  )}
                </div>
              </div>

              {/* Hand Zone */}
              <div>
                <h3 className="text-sm font-bold text-gray-400" style={{ marginBottom: 'var(--spacing-component-xs)', paddingLeft: 'var(--spacing-component-xs)', paddingRight: 'var(--spacing-component-xs)' }}>
                  HAND ({player.hand ? player.hand.length : player.hand_count})
                </h3>
                <div 
                  className="flex flex-wrap min-h-[230px] bg-black bg-opacity-20 rounded"
                  style={{ gap: 'var(--spacing-component-xs)', padding: 'var(--spacing-component-md)' }}
                >
                  {player.hand ? (
                    player.hand.length === 0 ? (
                      <div className="text-gray-500 italic text-sm m-auto">No cards in hand</div>
                    ) : (
                      player.hand.map((card) => (
                        <CardDisplay
                          key={card.id}
                          card={card}
                          size={cardSize}
                          isClickable={isHuman && isActive}
                          isSelected={selectedCard === card.id}
                          onClick={() => onCardClick?.(card.id, 'hand')}
                        />
                      ))
                    )
                  ) : (
                    <div className="flex" style={{ gap: 'var(--spacing-component-xs)' }}>
                      {Array.from({ length: player.hand_count }).map((_, i) => (
                        <div
                          key={i}
                          className="w-32 h-40 bg-gray-700 rounded border-2 border-gray-600 flex items-center justify-center"
                          style={{ padding: 'var(--spacing-component-xs)' }}
                        >
                          <img 
                            src="/ggltcg-logo.svg" 
                            alt="Hidden card" 
                            className="w-full h-full object-contain opacity-40"
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Hand Zone (AI shows first) */}
              <div>
                <h3 className="text-sm font-bold text-gray-400" style={{ marginBottom: 'var(--spacing-component-xs)', paddingLeft: 'var(--spacing-component-xs)', paddingRight: 'var(--spacing-component-xs)' }}>
                  HAND ({player.hand ? player.hand.length : player.hand_count})
                </h3>
                <div 
                  className="flex flex-wrap min-h-[140px] bg-black bg-opacity-20 rounded"
                  style={{ gap: 'var(--spacing-component-xs)', padding: 'var(--spacing-component-md)' }}
                >
                  {player.hand ? (
                    player.hand.length === 0 ? (
                      <div className="text-gray-500 italic text-sm m-auto">No cards in hand</div>
                    ) : (
                      player.hand.map((card) => (
                        <CardDisplay
                          key={card.id}
                          card={card}
                          size={cardSize}
                        />
                      ))
                    )
                  ) : (
                    <div className="flex" style={{ gap: 'var(--spacing-component-xs)' }}>
                      {Array.from({ length: player.hand_count }).map((_, i) => (
                        <div
                          key={i}
                          className="w-32 h-40 bg-gray-700 rounded border-2 border-gray-600 flex items-center justify-center"
                          style={{ padding: 'var(--spacing-component-xs)' }}
                        >
                          <img 
                            src="/ggltcg-logo.svg" 
                            alt="Hidden card" 
                            className="w-full h-full object-contain opacity-40"
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* In Play Zone */}
              <div>
                <h3 className="text-sm font-bold text-gray-400" style={{ marginBottom: 'var(--spacing-component-xs)', paddingLeft: 'var(--spacing-component-xs)', paddingRight: 'var(--spacing-component-xs)' }}>
                  IN PLAY ({player.in_play.length})
                </h3>
                <div 
                  className="flex flex-wrap min-h-[180px] bg-black bg-opacity-20 rounded"
                  style={{ gap: 'var(--spacing-component-xs)', padding: 'var(--spacing-component-md)' }}
                >
                  {player.in_play.length === 0 ? (
                    <div className="text-gray-500 italic text-sm m-auto">No cards in play</div>
                  ) : (
                    player.in_play.map((card) => (
                      <CardDisplay
                        key={card.id}
                        card={card}
                        size={cardSize}
                      />
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Right side - Sleep Zone (fixed width) */}
        <div className="w-40 flex-shrink-0">
          <h3 className="text-sm font-bold text-gray-400" style={{ marginBottom: 'var(--spacing-component-xs)', paddingLeft: 'var(--spacing-component-xs)', paddingRight: 'var(--spacing-component-xs)' }}>
            SLEEP ZONE ({player.sleep_zone.length})
          </h3>
          <div 
            className="flex flex-col min-h-[340px] bg-black bg-opacity-20 rounded"
            style={{ gap: 'var(--spacing-component-xs)', padding: 'var(--spacing-component-md)' }}
          >
            {player.sleep_zone.length === 0 ? (
              <div className="text-gray-500 italic text-sm m-auto text-center">No sleeping cards</div>
            ) : (
              player.sleep_zone.map((card) => (
                <CardDisplay
                  key={card.id}
                  card={card}
                  size="small"
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
