/**
 * CardDisplay Component
 * Renders a single card with all its stats and effects
 */

import type { Card } from '../types/game';
import { getCardByName } from '../data/cards';

interface CardDisplayProps {
  card: Card;
  onClick?: () => void;
  isSelected?: boolean;
  isClickable?: boolean;
  size?: 'small' | 'medium' | 'large';
}

export function CardDisplay({
  card,
  onClick,
  isSelected = false,
  isClickable = false,
  size = 'medium',
}: CardDisplayProps) {
  const cardData = getCardByName(card.name);
  const isToy = card.card_type === 'TOY';

  const sizeClasses = {
    small: 'w-32 p-2 text-xs',
    medium: 'w-48 p-3 text-sm',
    large: 'w-64 p-4 text-base',
  };

  return (
    <div
      onClick={isClickable ? onClick : undefined}
      className={`
        ${sizeClasses[size]}
        rounded-lg border-2 transition-all duration-200
        ${isClickable ? 'cursor-pointer hover:scale-105 hover:shadow-xl' : ''}
        ${isSelected ? 'border-yellow-400 shadow-xl scale-105' : 'border-gray-600'}
        ${isToy ? 'bg-gradient-to-br from-blue-900 to-blue-800' : 'bg-gradient-to-br from-purple-900 to-purple-800'}
        ${card.is_sleeped ? 'opacity-50 grayscale' : ''}
      `}
    >
      {/* Card Header */}
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-bold truncate flex-1">{card.name}</h3>
        <span className={`
          px-1.5 py-0.5 rounded text-xs font-bold ml-1
          ${isToy ? 'bg-blue-600' : 'bg-purple-600'}
        `}>
          {card.card_type}
        </span>
      </div>

      {/* Cost */}
      <div className="text-xs text-gray-300 mb-2">
        Cost: {card.cost} CC
      </div>

      {/* Toy Stats */}
      {isToy && (
        <div className="flex gap-2 mb-2 text-xs">
          <div className="flex-1 bg-black bg-opacity-30 rounded px-1.5 py-1">
            <div className="text-gray-400">SPD</div>
            <div className="font-bold">{card.speed}</div>
          </div>
          <div className="flex-1 bg-black bg-opacity-30 rounded px-1.5 py-1">
            <div className="text-gray-400">STR</div>
            <div className="font-bold">{card.strength}</div>
          </div>
          <div className="flex-1 bg-black bg-opacity-30 rounded px-1.5 py-1">
            <div className="text-gray-400">STA</div>
            <div className="font-bold">
              {card.current_stamina !== null && card.current_stamina !== card.stamina ? (
                <span className="text-red-400">
                  {card.current_stamina}/{card.stamina}
                </span>
              ) : (
                card.stamina
              )}
            </div>
          </div>
        </div>
      )}

      {/* Effect Text */}
      {cardData && (
        <p className="text-xs text-gray-300 italic line-clamp-4 mt-2">
          {cardData.effect}
        </p>
      )}

      {/* Sleeped Indicator */}
      {card.is_sleeped && (
        <div className="mt-2 text-center text-xs font-bold text-red-400">
          SLEEPED
        </div>
      )}
    </div>
  );
}
