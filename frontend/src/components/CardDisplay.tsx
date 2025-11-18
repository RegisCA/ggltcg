/**
 * CardDisplay Component
 * Renders a single card with GGLTCG design system
 * Supports multiple sizes and states according to UX spec
 */

import { useState, useEffect } from 'react';
import type { Card } from '../types/game';
import type { CardDataResponse } from '../types/api';
import { getAllCards } from '../api/gameService';

interface CardDisplayProps {
  card: Card;
  onClick?: () => void;
  isSelected?: boolean;
  isClickable?: boolean;
  isHighlighted?: boolean;
  isDisabled?: boolean;
  isTussling?: boolean;
  size?: 'small' | 'medium' | 'large';
}

// Cache for card data to avoid repeated API calls
let cardDataCache: CardDataResponse[] | null = null;

export function CardDisplay({
  card,
  onClick,
  isSelected = false,
  isClickable = false,
  isHighlighted = false,
  isDisabled = false,
  isTussling = false,
  size = 'medium',
}: CardDisplayProps) {
  const [cardData, setCardData] = useState<CardDataResponse | null>(null);

  // Load card data from API (with caching)
  useEffect(() => {
    const loadCardData = async () => {
      if (cardDataCache === null) {
        cardDataCache = await getAllCards();
      }
      const data = cardDataCache.find((c) => c.name === card.name);
      setCardData(data || null);
    };
    
    loadCardData();
  }, [card.name]);

  const isToy = card.card_type === 'Toy';  // Match backend enum value

  // Size configurations (px values from UX spec)
  const sizeConfig = {
    small: { width: 120, height: 164, padding: 8, fontSize: 'xs', statSize: 'xs' },
    medium: { width: 165, height: 225, padding: 12, fontSize: 'sm', statSize: 'sm' },
    large: { width: 330, height: 450, padding: 24, fontSize: 'base', statSize: 'lg' },
  };

  const config = sizeConfig[size];
  
  // Use card's color attributes from backend (faction/type based)
  const borderColor = card.primary_color || (isToy ? '#C74444' : '#8B5FA8');
  const accentColor = card.accent_color || (isToy ? '#C74444' : '#8B5FA8');

  // Determine border and effects based on state
  let effectiveBorderColor = borderColor;
  let boxShadow = undefined;
  let animation = undefined;
  let borderWidth = '2px';
  
  if (isTussling) {
    effectiveBorderColor = 'var(--ggltcg-red)';
    boxShadow = '0 0 16px rgba(199, 68, 68, 0.8)';
    animation = 'tussle-shake 0.3s ease-in-out infinite';
  } else if (isSelected) {
    effectiveBorderColor = '#FFD700'; // Gold color for selection
    boxShadow = '0 0 20px rgba(255, 215, 0, 0.8), 0 0 40px rgba(255, 215, 0, 0.4)';
    borderWidth = '3px';
  } else if (isHighlighted) {
    effectiveBorderColor = 'var(--ui-highlight)';
    boxShadow = '0 0 12px rgba(74, 123, 255, 0.4)';
  }

  return (
    <div
      onClick={isClickable && !isDisabled ? onClick : undefined}
      className={`
        transition-all duration-200 rounded
        ${isClickable && !isDisabled ? 'cursor-pointer hover:scale-105 hover:shadow-xl' : ''}
        ${isDisabled ? 'opacity-40 cursor-not-allowed' : ''}
        ${isSelected ? 'scale-105 shadow-xl' : ''}
        ${card.is_sleeped ? 'opacity-50 grayscale' : ''}
      `}
      style={{
        width: `${config.width}px`,
        height: `${config.height}px`,
        padding: `${config.padding}px`,
        backgroundColor: 'var(--ui-card-bg)',
        border: `${borderWidth} solid ${effectiveBorderColor}`,
        boxShadow,
        animation,
      }}
    >
      {/* Card Header: Cost + Name + Type Badge */}
      <div className="flex justify-between items-start mb-2" style={{ position: 'relative', zIndex: 1 }}>
        {/* Cost Indicator */}
        <div 
          className="font-bold"
          style={{
            width: size === 'small' ? '24px' : size === 'medium' ? '32px' : '48px',
            height: size === 'small' ? '24px' : size === 'medium' ? '32px' : '48px',
            backgroundColor: accentColor,
            color: 'white',
            borderRadius: '4px',
            fontSize: size === 'small' ? '0.75rem' : size === 'medium' ? '1rem' : '1.5rem',
            boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          {card.cost}
        </div>

        {/* Card Name */}
        <h3 
          className="flex-1 font-bold truncate"
          style={{
            fontFamily: 'var(--font-body)',
            fontSize: size === 'small' ? '0.75rem' : size === 'medium' ? '0.875rem' : '1.25rem',
            lineHeight: '1.2',
            fontWeight: 700,
            marginLeft: size === 'small' ? '4px' : size === 'medium' ? '6px' : '8px',
            marginRight: size === 'small' ? '4px' : size === 'medium' ? '6px' : '8px',
          }}
        >
          {card.name}
        </h3>

        {/* Type Badge */}
        <span 
          className="font-bold text-white"
          style={{
            padding: size === 'small' ? '2px 6px' : size === 'medium' ? '4px 8px' : '6px 12px',
            borderRadius: '4px',
            fontSize: size === 'small' ? '0.625rem' : size === 'medium' ? '0.75rem' : '0.875rem',
            backgroundColor: isToy ? 'var(--ui-toy-badge)' : 'var(--ui-action-badge)',
            whiteSpace: 'nowrap',
            boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
          }}
        >
          {card.card_type}
        </span>
      </div>

      {/* Artwork Placeholder (for future) - Only show on large cards */}
      {size === 'large' && (
        <div
          style={{
            width: '100%',
            height: '120px',
            backgroundColor: 'rgba(0,0,0,0.2)',
            borderRadius: '4px',
            marginBottom: '8px',
            border: `1px solid ${borderColor}`,
            opacity: 0.3,
          }}
        />
      )}

      {/* Toy Stats */}
      {isToy && (
        <div className="flex gap-1 mb-1" style={{ fontSize: config.fontSize, position: 'relative', zIndex: 1 }}>
          <div className="flex-1 bg-black bg-opacity-30 rounded px-1 py-1 text-center">
            <div className="text-gray-400" style={{ fontSize: size === 'small' ? '0.5rem' : '0.625rem' }}>SPD</div>
            <div className="font-bold" style={{ 
              color: (card.speed !== null && card.base_speed !== null && card.speed > card.base_speed) ? '#4ade80' : accentColor,
              fontSize: size === 'small' ? '0.875rem' : '1rem' 
            }}>
              {card.speed}
              {card.speed !== null && card.base_speed !== null && card.speed > card.base_speed && (
                <span className="text-xs ml-0.5">↑</span>
              )}
            </div>
          </div>
          <div className="flex-1 bg-black bg-opacity-30 rounded px-1 py-1 text-center">
            <div className="text-gray-400" style={{ fontSize: size === 'small' ? '0.5rem' : '0.625rem' }}>STR</div>
            <div className="font-bold" style={{ 
              color: (card.strength !== null && card.base_strength !== null && card.strength > card.base_strength) ? '#4ade80' : accentColor,
              fontSize: size === 'small' ? '0.875rem' : '1rem' 
            }}>
              {card.strength}
              {card.strength !== null && card.base_strength !== null && card.strength > card.base_strength && (
                <span className="text-xs ml-0.5">↑</span>
              )}
            </div>
          </div>
          <div className="flex-1 bg-black bg-opacity-30 rounded px-1 py-1 text-center">
            <div className="text-gray-400" style={{ fontSize: size === 'small' ? '0.5rem' : '0.625rem' }}>STA</div>
            <div className="font-bold" style={{ fontSize: size === 'small' ? '0.875rem' : '1rem' }}>
              {card.current_stamina !== null && card.current_stamina !== card.stamina ? (
                <span className="text-red-400">
                  {card.current_stamina}/{card.stamina}
                  {card.stamina !== null && card.base_stamina !== null && card.stamina > card.base_stamina && (
                    <span className="text-xs ml-0.5">↑</span>
                  )}
                </span>
              ) : (
                <>
                  <span style={{ 
                    color: (card.stamina !== null && card.base_stamina !== null && card.stamina > card.base_stamina) ? '#4ade80' : accentColor 
                  }}>
                    {card.stamina}
                  </span>
                  {card.stamina !== null && card.base_stamina !== null && card.stamina > card.base_stamina && (
                    <span className="text-green-400 text-xs ml-0.5">↑</span>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Effect Text - Only show on medium and large cards */}
      {cardData && size !== 'small' && (
        <div 
          className="text-gray-300 italic mt-2"
          style={{
            fontSize: size === 'medium' ? '0.75rem' : '0.875rem',
            lineHeight: '1.3',
            overflow: 'hidden',
            display: '-webkit-box',
            WebkitBoxOrient: 'vertical',
            WebkitLineClamp: size === 'medium' ? 3 : 8,
            position: 'relative',
            zIndex: 1,
          }}
        >
          {cardData.effect}
        </div>
      )}

      {/* Sleeped Indicator */}
      {card.is_sleeped && (
        <div 
          className="mt-2 text-center font-bold text-red-400"
          style={{ fontSize: size === 'small' ? '0.625rem' : '0.75rem', position: 'relative', zIndex: 1 }}
        >
          SLEEPED
        </div>
      )}
    </div>
  );
}
