/**
 * CardDisplay Component
 * Renders a single card with GGLTCG design system
 * Supports multiple sizes and states according to UX spec
 * 
 * Uses Framer Motion for animations:
 * - layoutId enables smooth transitions when cards move between zones
 * - Entrance/exit animations
 * - Hover/tap feedback
 * 
 * Respects user's reduced motion preferences for accessibility (WCAG 2.1).
 */

import { motion } from 'framer-motion';
import { useState } from 'react';
import type { Card } from '../types/game';
import { AnimatedStat } from './AnimatedStat';
import { useReducedMotion } from '../hooks/useReducedMotion';
import { useResponsive } from '../hooks/useResponsive';
import { CardDetailModal } from './CardDetailModal';

interface CardDisplayProps {
  card: Card;
  onClick?: () => void;
  isSelected?: boolean;
  isClickable?: boolean;
  isHighlighted?: boolean;
  isDisabled?: boolean;
  isUnplayable?: boolean;  // Card cannot be played this turn (not enough CC, restricted, etc.)
  isTussling?: boolean;
  isCopy?: boolean;  // Card created by Copy effect
  size?: 'small' | 'medium' | 'large';
  /** Enable layout animations for zone transitions (uses card.id as layoutId) */
  enableLayoutAnimation?: boolean;
  /** Disable the mobile detail modal (e.g. when shown inside the modal itself) */
  disableDetailModal?: boolean;
}

export function CardDisplay({
  card,
  onClick,
  isSelected = false,
  isClickable = false,
  isHighlighted = false,
  isDisabled = false,
  isUnplayable = false,
  isTussling = false,
  isCopy = false,
  size = 'medium',
  enableLayoutAnimation = false,
  disableDetailModal = false,
}: CardDisplayProps) {
  const prefersReducedMotion = useReducedMotion();
  const { isMobile } = useResponsive();
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  
  // Track touch/mouse position to differentiate tap from scroll
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  
  // Combine disabled states - isUnplayable is a specific kind of disabled
  const effectivelyDisabled = isDisabled || isUnplayable;
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
  let borderWidth = '2px';  // Default border width
  
  if (isTussling) {
    effectiveBorderColor = 'var(--ggltcg-red)';
    boxShadow = '0 0 16px rgba(199, 68, 68, 0.8)';
    animation = 'tussle-shake 0.3s ease-in-out infinite';
    borderWidth = '3px';  // Thicker border for tussling
  } else if (isSelected) {
    effectiveBorderColor = '#FFD700'; // Gold color for selection
    boxShadow = '0 0 12px rgba(255, 215, 0, 0.9), 0 0 24px rgba(255, 215, 0, 0.5)';
    borderWidth = '3px';  // Thicker border for selection
  } else if (isHighlighted) {
    // Subtle green glow for actionable cards (can tussle or use ability)
    // Thicker border + icon badge for colorblind accessibility
    effectiveBorderColor = '#22c55e'; // Green border
    boxShadow = '0 0 8px rgba(34, 197, 94, 0.5)';
    borderWidth = '4px';  // Significantly thicker border for highlighted state
  }

  // Logic for mobile detail view
  const shouldEnableMobileDetail = isMobile && !disableDetailModal;

  const handleInteraction = () => {
    if (shouldEnableMobileDetail) {
      setIsDetailOpen(true);
    } else if (isClickable && !effectivelyDisabled && onClick) {
      onClick();
    }
  };
  
  // Handle touch start - record position
  const handleTouchStart = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    setTouchStart({ x: touch.clientX, y: touch.clientY });
  };
  
  // Handle touch end - only open modal if it was a tap (not scroll)
  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStart || !shouldEnableMobileDetail) {
      setTouchStart(null);
      return;
    }
    
    const touch = e.changedTouches[0];
    const deltaX = Math.abs(touch.clientX - touchStart.x);
    const deltaY = Math.abs(touch.clientY - touchStart.y);
    
    // If movement is less than 10px, consider it a tap
    const TAP_THRESHOLD = 10;
    if (deltaX < TAP_THRESHOLD && deltaY < TAP_THRESHOLD) {
      setIsDetailOpen(true);
    }
    
    setTouchStart(null);
  };

  // Keyboard event handler for accessibility
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && (shouldEnableMobileDetail || (isClickable && !effectivelyDisabled && onClick))) {
      e.preventDefault();
      handleInteraction();
    }
  };

  return (
    <>
      <motion.div
        layoutId={enableLayoutAnimation ? `card-${card.id}` : undefined}
        onClick={!shouldEnableMobileDetail && (isClickable && !effectivelyDisabled) ? onClick : undefined}
        onTouchStart={shouldEnableMobileDetail ? handleTouchStart : undefined}
        onTouchEnd={shouldEnableMobileDetail ? handleTouchEnd : undefined}
        onKeyDown={handleKeyDown}
        tabIndex={shouldEnableMobileDetail || (isClickable && !effectivelyDisabled) ? 0 : undefined}
        role="button"
        aria-label={isClickable ? `${card.name} card` : undefined}
        className={`
          rounded relative
          ${shouldEnableMobileDetail || (isClickable && !effectivelyDisabled) ? 'cursor-pointer' : ''}
          ${effectivelyDisabled && !shouldEnableMobileDetail ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        style={{
          width: `${config.width}px`,
          height: `${config.height}px`,
          padding: `${config.padding}px`,
          backgroundColor: 'var(--ui-card-bg)',
          border: `${borderWidth} solid ${effectiveBorderColor}`,
          boxShadow,
          animation,
          // Apply grayscale filter for sleeped cards, but not opacity (handled by animate)
          filter: card.is_sleeped && !isSelected ? 'grayscale(100%)' : undefined,
        }}
        initial={enableLayoutAnimation ? false : { opacity: 0, scale: prefersReducedMotion ? 1 : 0.9 }}
        animate={{ 
          opacity: effectivelyDisabled ? 0.5 : (card.is_sleeped && !isSelected ? 0.6 : 1), 
          scale: 1 
        }}
        transition={{ 
          duration: prefersReducedMotion ? 0.1 : 0.3,
          layout: { duration: prefersReducedMotion ? 0.1 : 0.4, ease: 'easeInOut' }
        }}
        whileHover={isClickable && !effectivelyDisabled && !prefersReducedMotion ? { scale: 1.05 } : undefined}
        whileTap={isClickable && !effectivelyDisabled && !prefersReducedMotion ? { scale: 0.98 } : undefined}
      >
        {/* Colorblind-Accessible Visual Indicators */}
        {/* Available Action Badge - top-right corner */}
        {isHighlighted && !effectivelyDisabled && (
          <div
            className="absolute top-1 right-1 bg-green-500 text-white rounded-full flex items-center justify-center font-bold shadow-lg"
            style={{
              width: size === 'small' ? '20px' : size === 'medium' ? '24px' : '32px',
              height: size === 'small' ? '20px' : size === 'medium' ? '24px' : '32px',
              fontSize: size === 'small' ? '0.75rem' : size === 'medium' ? '0.875rem' : '1.125rem',
              zIndex: 10,
            }}
            title="Available action"
          >
            ⚡
          </div>
        )}

        {/* Copy Badge - top-left corner */}
        {isCopy && (
          <div
            className="absolute top-1 left-1 bg-purple-600 text-white rounded px-1 font-bold shadow-lg"
            style={{
              fontSize: size === 'small' ? '0.625rem' : size === 'medium' ? '0.75rem' : '0.875rem',
              zIndex: 10,
            }}
            title="Copy of another card"
          >
            COPY
          </div>
        )}

        {/* Card Header: Cost + Name + Type Badge */}
        <div className="flex justify-between items-start" style={{ marginBottom: 'var(--spacing-component-xs)', position: 'relative', zIndex: 1 }}>
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
              marginLeft: size === 'small' ? '6px' : size === 'medium' ? '8px' : '12px',
              marginRight: size === 'small' ? '6px' : size === 'medium' ? '8px' : '12px',
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
          <div className="flex" style={{ gap: '4px', marginBottom: '4px', fontSize: config.fontSize, position: 'relative', zIndex: 1 }}>
            <AnimatedStat
              value={card.speed}
              baseValue={card.base_speed}
              label="SPD"
              accentColor={accentColor}
              size={size}
            />
            <AnimatedStat
              value={card.strength}
              baseValue={card.base_strength}
              label="STR"
              accentColor={accentColor}
              size={size}
            />
            <AnimatedStat
              value={card.stamina}
              baseValue={card.base_stamina}
              label="STA"
              accentColor={accentColor}
              size={size}
              currentValue={card.current_stamina}
            />
          </div>
        )}

        {/* Effect Text - Only show on medium and large cards */}
        {size !== 'small' && card.effect_text && (
          <div 
            className="text-gray-300 italic"
            style={{
              fontSize: size === 'medium' ? '0.75rem' : '0.875rem',
              lineHeight: '1.3',
              overflow: 'hidden',
              display: '-webkit-box',
              WebkitBoxOrient: 'vertical',
              WebkitLineClamp: size === 'medium' ? 3 : 8,
              position: 'relative',
              zIndex: 1,
              marginTop: size === 'medium' ? '8px' : '12px',
            }}
          >
            {card.effect_text}
          </div>
        )}

        {/* Sleeped Indicator */}
        {card.is_sleeped && (
          <div 
            className="text-center font-bold text-red-400"
            style={{ marginTop: 'var(--spacing-component-xs)', fontSize: size === 'small' ? '0.625rem' : '0.75rem', position: 'relative', zIndex: 1 }}
          >
            SLEEPED
          </div>
        )}
      </motion.div>

      {/* Mobile Detail Modal */}
      {shouldEnableMobileDetail && (
        <CardDetailModal
          card={card}
          isOpen={isDetailOpen}
          onClose={() => setIsDetailOpen(false)}
          onAction={isClickable && !effectivelyDisabled ? onClick : undefined}
          actionLabel="Select"
        />
      )}
    </>
  );
}
