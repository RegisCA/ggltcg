/**
 * TurnTransition Component
 * 
 * Shows an animated overlay when the turn changes.
 * Displays "Your Turn" or "Opponent's Turn" with a swoosh animation.
 * 
 * Respects user's reduced motion preferences for accessibility (WCAG 2.1).
 */

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';
import { usePreviousValue } from '../hooks/usePreviousValue';
import { useReducedMotion } from '../hooks/useReducedMotion';

interface TurnTransitionProps {
  isPlayerTurn: boolean;
  turnNumber: number;
}

export function TurnTransition({ isPlayerTurn, turnNumber }: TurnTransitionProps) {
  const [showTransition, setShowTransition] = useState(false);
  const previousTurn = usePreviousValue(turnNumber);
  const previousIsPlayerTurn = usePreviousValue(isPlayerTurn);
  const prefersReducedMotion = useReducedMotion();
  
  // Detect turn changes - consolidated timer logic to prevent memory leaks (#115)
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;

    // Only show transition if turn actually changed (not on initial load)
    const turnChanged = previousTurn !== undefined && previousTurn !== turnNumber;
    const playerChanged =
      previousIsPlayerTurn !== undefined &&
      previousIsPlayerTurn !== isPlayerTurn &&
      previousTurn === turnNumber;

    if (turnChanged || playerChanged) {
      setShowTransition(true);
      // Shorter duration for reduced motion preference
      const duration = prefersReducedMotion ? 800 : 1500;
      timer = setTimeout(() => setShowTransition(false), duration);
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [turnNumber, isPlayerTurn, previousTurn, previousIsPlayerTurn, prefersReducedMotion]);
  
  // Animation variants - reduced or full based on preference (#111)
  const containerVariants = prefersReducedMotion
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
      }
    : {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
      };

  const contentVariants = prefersReducedMotion
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
      }
    : {
        initial: { scale: 0.5, y: 50, opacity: 0 },
        animate: { scale: 1, y: 0, opacity: 1 },
        exit: { scale: 1.2, y: -50, opacity: 0 },
      };

  const lineVariants = prefersReducedMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 } }
    : { initial: { scaleX: 0 }, animate: { scaleX: 1 } };
  
  return (
    <AnimatePresence>
      {showTransition && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none"
          variants={containerVariants}
          initial="initial"
          animate="animate"
          exit="exit"
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
            variants={contentVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={prefersReducedMotion 
              ? { duration: 0.2 }
              : { duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }
            }
          >
            <div
              className="rounded-lg"
              style={{
                padding: 'var(--spacing-component-lg) var(--spacing-component-xl)',
                background: isPlayerTurn 
                  ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'
                  : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                boxShadow: isPlayerTurn
                  ? '0 0 60px rgba(34, 197, 94, 0.6)'
                  : '0 0 60px rgba(239, 68, 68, 0.6)',
              }}
            >
              <div className="text-white text-center">
                <div className="text-4xl font-bold\" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
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
              variants={lineVariants}
              initial="initial"
              animate="animate"
              transition={{ duration: 0.3, delay: prefersReducedMotion ? 0 : 0.2 }}
            />
            <motion.div
              className="absolute left-0 right-0 h-1 -bottom-4"
              style={{
                background: isPlayerTurn
                  ? 'linear-gradient(90deg, transparent, #22c55e, transparent)'
                  : 'linear-gradient(90deg, transparent, #ef4444, transparent)',
              }}
              variants={lineVariants}
              initial="initial"
              animate="animate"
              transition={{ duration: 0.3, delay: prefersReducedMotion ? 0 : 0.2 }}
            />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
