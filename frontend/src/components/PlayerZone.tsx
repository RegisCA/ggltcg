/**
 * PlayerZone Component
 * Displays a player's zones (hand, in play, sleep zone) and stats
 */

import type { Player } from '../types/game';
import { CardDisplay } from './CardDisplay';

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
  return (
    <div className={`
      p-3 rounded transition-all
      ${isActive ? 'bg-game-accent border-2 border-game-highlight' : 'bg-game-card border border-gray-700'}
    `}>
      {/* Player Header */}
      <div className="flex justify-between items-center mb-3">
        <div>
          <h2 className="text-xl font-bold">{player.name}</h2>
          {isActive && (
            <span className="text-xs text-game-highlight font-bold">ACTIVE TURN</span>
          )}
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold">{player.cc} CC</div>
          <div className="text-xs text-gray-400">Command Counters</div>
        </div>
      </div>

      {/* Content Grid - Zones on left, Sleep on right */}
      <div className="flex gap-3">
        {/* Left side - Main zones (80% width) */}
        <div className="flex-1 space-y-3" style={{ minWidth: 0 }}>
          {/* For AI: Hand first, then In Play */}
          {/* For Human: In Play first, then Hand */}
          
          {isHuman ? (
            <>
              {/* In Play Zone */}
              <div>
                <h3 className="text-sm font-bold text-gray-400 mb-2">
                  IN PLAY ({player.in_play.length})
                </h3>
                <div className="flex gap-2 flex-wrap min-h-[180px] p-2 bg-black bg-opacity-20 rounded">
                  {player.in_play.length === 0 ? (
                    <div className="text-gray-500 italic text-sm m-auto">No cards in play</div>
                  ) : (
                    player.in_play.map((card) => (
                      <CardDisplay
                        key={card.id}
                        card={card}
                        size="medium"
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
                <h3 className="text-sm font-bold text-gray-400 mb-2">
                  HAND ({player.hand ? player.hand.length : player.hand_count})
                </h3>
                <div className="flex gap-2 flex-wrap min-h-[230px] p-2 bg-black bg-opacity-20 rounded">
                  {player.hand ? (
                    player.hand.length === 0 ? (
                      <div className="text-gray-500 italic text-sm m-auto">No cards in hand</div>
                    ) : (
                      player.hand.map((card) => (
                        <CardDisplay
                          key={card.id}
                          card={card}
                          size="medium"
                          isClickable={isHuman && isActive}
                          isSelected={selectedCard === card.id}
                          onClick={() => onCardClick?.(card.id, 'hand')}
                        />
                      ))
                    )
                  ) : (
                    <div className="flex gap-2">
                      {Array.from({ length: player.hand_count }).map((_, i) => (
                        <div
                          key={i}
                          className="w-32 h-40 bg-gray-700 rounded border-2 border-gray-600 flex items-center justify-center p-2"
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
                <h3 className="text-sm font-bold text-gray-400 mb-2">
                  HAND ({player.hand ? player.hand.length : player.hand_count})
                </h3>
                <div className="flex gap-2 flex-wrap min-h-[140px] p-2 bg-black bg-opacity-20 rounded">
                  {player.hand ? (
                    player.hand.length === 0 ? (
                      <div className="text-gray-500 italic text-sm m-auto">No cards in hand</div>
                    ) : (
                      player.hand.map((card) => (
                        <CardDisplay
                          key={card.id}
                          card={card}
                          size="small"
                        />
                      ))
                    )
                  ) : (
                    <div className="flex gap-2">
                      {Array.from({ length: player.hand_count }).map((_, i) => (
                        <div
                          key={i}
                          className="w-32 h-40 bg-gray-700 rounded border-2 border-gray-600 flex items-center justify-center p-2"
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
                <h3 className="text-sm font-bold text-gray-400 mb-2">
                  IN PLAY ({player.in_play.length})
                </h3>
                <div className="flex gap-2 flex-wrap min-h-[180px] p-2 bg-black bg-opacity-20 rounded">
                  {player.in_play.length === 0 ? (
                    <div className="text-gray-500 italic text-sm m-auto">No cards in play</div>
                  ) : (
                    player.in_play.map((card) => (
                      <CardDisplay
                        key={card.id}
                        card={card}
                        size="medium"
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
          <h3 className="text-sm font-bold text-gray-400 mb-2">
            SLEEP ZONE ({player.sleep_zone.length})
          </h3>
          <div className="flex flex-col gap-2 min-h-[340px] p-2 bg-black bg-opacity-20 rounded">
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
