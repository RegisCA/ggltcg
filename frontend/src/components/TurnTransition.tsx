/**
 * TurnTransition Component
 * 
 * Shows an animated overlay when the turn changes.
 * Displays "Your Turn" or "Opponent's Turn" with a swoosh animation.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';
import { usePreviousValue } from '../hooks/usePreviousValue';

interface TurnTransitionProps {
  isPlayerTurn: boolean;
  turnNumber: number;
}

export function TurnTransition({ isPlayerTurn, turnNumber }: TurnTransitionProps) {
  const [showTransition, setShowTransition] = useState(false);
  const previousTurn = usePreviousValue(turnNumber);
  const previousIsPlayerTurn = usePreviousValue(isPlayerTurn);
  
  // Detect turn changes
  useEffect(() => {
    // Only show transition if turn actually changed (not on initial load)
    if (previousTurn !== undefined && previousTurn !== turnNumber) {
      setShowTransition(true);
      const timer = setTimeout(() => setShowTransition(false), 1500);
      return () => clearTimeout(timer);
    }
    // Also trigger if active player changed mid-turn (shouldn't happen but just in case)
    if (previousIsPlayerTurn !== undefined && previousIsPlayerTurn !== isPlayerTurn && previousTurn === turnNumber) {
      setShowTransition(true);
      const timer = setTimeout(() => setShowTransition(false), 1500);
      return () => clearTimeout(timer);
    }
  }, [turnNumber, isPlayerTurn, previousTurn, previousIsPlayerTurn]);
  
  return (
    <AnimatePresence>
      {showTransition && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0"
            style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
          
          {/* Turn indicator */}
          <motion.div
            className="relative"
            initial={{ scale: 0.5, y: 50, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 1.2, y: -50, opacity: 0 }}
            transition={{ 
              duration: 0.4,
              ease: [0.34, 1.56, 0.64, 1], // Spring-like ease
            }}
          >
            <div
              className="px-12 py-6 rounded-lg"
              style={{
                background: isPlayerTurn 
                  ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'
                  : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                boxShadow: isPlayerTurn
                  ? '0 0 60px rgba(34, 197, 94, 0.6)'
                  : '0 0 60px rgba(239, 68, 68, 0.6)',
              }}
            >
              <div className="text-white text-center">
                <div className="text-4xl font-bold mb-1">
                  {isPlayerTurn ? "Your Turn" : "Opponent's Turn"}
                </div>
                <div className="text-xl opacity-80">
                  Turn {turnNumber}
                </div>
              </div>
            </div>
            
            {/* Decorative lines */}
            <motion.div
              className="absolute left-0 right-0 h-1 -top-4"
              style={{
                background: isPlayerTurn
                  ? 'linear-gradient(90deg, transparent, #22c55e, transparent)'
                  : 'linear-gradient(90deg, transparent, #ef4444, transparent)',
              }}
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: 0.3, delay: 0.2 }}
            />
            <motion.div
              className="absolute left-0 right-0 h-1 -bottom-4"
              style={{
                background: isPlayerTurn
                  ? 'linear-gradient(90deg, transparent, #22c55e, transparent)'
                  : 'linear-gradient(90deg, transparent, #ef4444, transparent)',
              }}
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: 0.3, delay: 0.2 }}
            />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
