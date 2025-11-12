/**
 * CardHoverPreview Component
 * Shows an enlarged preview of a card on hover with dimmed background
 */

import { useState, useEffect } from 'react';
import type { Card } from '../types/game';
import { CardDisplay } from './CardDisplay';

interface CardHoverPreviewProps {
  card: Card | null;
}

export function CardHoverPreview({ card }: CardHoverPreviewProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (card) {
      // Small delay before showing to avoid flicker
      const timer = setTimeout(() => setVisible(true), 200);
      return () => clearTimeout(timer);
    } else {
      setVisible(false);
    }
  }, [card]);

  if (!card || !visible) {
    return null;
  }

  return (
    <>
      {/* Dimmed background overlay */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          zIndex: 9998,
          pointerEvents: 'none',
          animation: 'fadeIn 0.2s ease-in',
        }}
      />
      
      {/* Centered card preview */}
      <div
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 9999,
          pointerEvents: 'none',
          animation: 'fadeIn 0.2s ease-in',
        }}
      >
        <CardDisplay card={card} size="large" />
      </div>
    </>
  );
}
