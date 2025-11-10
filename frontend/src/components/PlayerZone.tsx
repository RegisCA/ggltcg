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
  onCardClick?: (cardName: string, zone: 'hand' | 'in_play') => void;
  selectedCard?: string;
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
      p-4 rounded-lg border-2 transition-all
      ${isActive ? 'border-game-highlight bg-game-accent' : 'border-game-card bg-game-card'}
    `}>
      {/* Player Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-2xl font-bold">{player.name}</h2>
          {isActive && (
            <span className="text-sm text-game-highlight font-bold">ACTIVE TURN</span>
          )}
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold">{player.cc} CC</div>
          <div className="text-sm text-gray-400">Command Counters</div>
        </div>
      </div>

      {/* In Play Zone */}
      <div className="mb-4">
        <h3 className="text-sm font-bold text-gray-400 mb-2">
          IN PLAY ({player.in_play.length})
        </h3>
        <div className="flex gap-2 flex-wrap min-h-[200px] p-2 bg-black bg-opacity-20 rounded">
          {player.in_play.length === 0 ? (
            <div className="text-gray-500 italic text-sm m-auto">No cards in play</div>
          ) : (
            player.in_play.map((card) => (
              <CardDisplay
                key={`${card.name}-${card.owner}`}
                card={card}
                size="small"
                isClickable={isHuman && isActive}
                isSelected={selectedCard === card.name}
                onClick={() => onCardClick?.(card.name, 'in_play')}
              />
            ))
          )}
        </div>
      </div>

      {/* Hand Zone */}
      <div className="mb-4">
        <h3 className="text-sm font-bold text-gray-400 mb-2">
          HAND ({player.hand ? player.hand.length : player.hand_count})
        </h3>
        <div className="flex gap-2 flex-wrap min-h-[180px] p-2 bg-black bg-opacity-20 rounded">
          {player.hand ? (
            player.hand.length === 0 ? (
              <div className="text-gray-500 italic text-sm m-auto">No cards in hand</div>
            ) : (
              player.hand.map((card) => (
                <CardDisplay
                  key={`${card.name}-${card.owner}`}
                  card={card}
                  size="small"
                  isClickable={isHuman && isActive}
                  isSelected={selectedCard === card.name}
                  onClick={() => onCardClick?.(card.name, 'hand')}
                />
              ))
            )
          ) : (
            <div className="flex gap-2">
              {Array.from({ length: player.hand_count }).map((_, i) => (
                <div
                  key={i}
                  className="w-32 h-40 bg-gray-700 rounded border-2 border-gray-600 flex items-center justify-center"
                >
                  <span className="text-gray-500 text-4xl">?</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Sleep Zone */}
      <div>
        <h3 className="text-sm font-bold text-gray-400 mb-2">
          SLEEP ZONE ({player.sleep_zone.length})
        </h3>
        <div className="flex gap-2 flex-wrap min-h-[100px] p-2 bg-black bg-opacity-20 rounded">
          {player.sleep_zone.length === 0 ? (
            <div className="text-gray-500 italic text-sm m-auto">No sleeping cards</div>
          ) : (
            player.sleep_zone.map((card) => (
              <CardDisplay
                key={`${card.name}-${card.owner}-sleep`}
                card={card}
                size="small"
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
