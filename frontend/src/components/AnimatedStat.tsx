/**
 * AnimatedStat Component
 * 
 * Displays a stat value with animation when it changes.
 * - Green flash + scale up when value increases
 * - Red flash + shake when value decreases
 * 
 * Respects user's reduced motion preferences for accessibility (WCAG 2.1).
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePreviousValue } from '../hooks/usePreviousValue';
import { useReducedMotion } from '../hooks/useReducedMotion';

interface AnimatedStatProps {
  value: number | null;
  baseValue?: number | null;
  label: string;
  accentColor: string;
  size: 'small' | 'medium' | 'large';
  /** For stamina: show current/max format */
  currentValue?: number | null;
}

// Animation variants defined outside component for performance (#116)
const statVariants = {
  initial: { scale: 1 },
  increased: {
    scale: [1, 1.3, 1],
    transition: { duration: 0.4, ease: 'easeOut' as const }  // Use 'as const' for proper typing
  },
  decreased: {
    x: [0, -3, 3, -3, 3, 0],
    transition: { duration: 0.4, ease: 'easeOut' as const }
  },
};

// No-animation variants for reduced motion preference
const reducedMotionVariants = {
  initial: { scale: 1 },
  increased: { scale: 1 },
  decreased: { scale: 1 },
};

export function AnimatedStat({
  value,
  baseValue,
  label,
  accentColor,
  size,
  currentValue,
}: AnimatedStatProps) {
  const prefersReducedMotion = useReducedMotion();
  const previousValue = usePreviousValue(value);
  const previousCurrent = usePreviousValue(currentValue);
  
  // State-based flash control for proper AnimatePresence animation (#114)
  const [flashType, setFlashType] = useState<'increase' | 'decrease' | null>(null);
  
  // Determine if value changed and in which direction
  const valueIncreased = previousValue !== undefined && value !== null && previousValue !== null && value > previousValue;
  const valueDecreased = previousValue !== undefined && value !== null && previousValue !== null && value < previousValue;
  
  // For stamina with current/max, also check current value changes
  const currentDecreased = previousCurrent !== undefined && currentValue !== undefined && currentValue !== null && previousCurrent !== null && currentValue < previousCurrent;
  const currentIncreased = previousCurrent !== undefined && currentValue !== undefined && currentValue !== null && previousCurrent !== null && currentValue > previousCurrent;
  
  // Trigger flash effect with proper timing for AnimatePresence (#114)
  useEffect(() => {
    if (prefersReducedMotion) return; // No flash effects for reduced motion
    
    if (valueIncreased || currentIncreased) {
      setFlashType('increase');
      const timer = setTimeout(() => setFlashType(null), 500);
      return () => clearTimeout(timer);
    } else if (valueDecreased || currentDecreased) {
      setFlashType('decrease');
      const timer = setTimeout(() => setFlashType(null), 500);
      return () => clearTimeout(timer);
    }
  }, [valueIncreased, currentIncreased, valueDecreased, currentDecreased, prefersReducedMotion]);
  
  // Determine animation key - changes trigger re-animation
  const animationKey = `${value}-${currentValue}`;
  
  // Is this stat buffed above base?
  const isBuffed = value !== null && baseValue !== undefined && baseValue !== null && value > baseValue;
  
  // Determine display color
  let displayColor = accentColor;
  if (currentValue !== null && currentValue !== undefined && currentValue !== value) {
    // Damaged - show in red
    displayColor = '#f87171'; // red-400
  } else if (isBuffed) {
    // Buffed - show in green
    displayColor = '#4ade80'; // green-400
  }
  
  // Determine which animation to play
  let animateState: 'initial' | 'increased' | 'decreased' = 'initial';
  if (valueIncreased || currentIncreased) {
    animateState = 'increased';
  } else if (valueDecreased || currentDecreased) {
    animateState = 'decreased';
  }
  
  // Format display value
  const displayValue = currentValue !== null && currentValue !== undefined && currentValue !== value
    ? `${currentValue}/${value}`
    : String(value);

  // Calculate buff amount for accessibility (colorblind users)
  const buffAmount = isBuffed && value !== null && baseValue !== null ? value - baseValue : 0;

  // Use reduced motion variants if user prefers (#111)
  const variants = prefersReducedMotion ? reducedMotionVariants : statVariants;
  
  return (
    <div className="flex-1 bg-black bg-opacity-30 rounded px-1 py-1 text-center relative overflow-hidden">
      <div 
        className="text-gray-400" 
        style={{ fontSize: size === 'small' ? '0.5rem' : '0.625rem' }}
      >
        {label}
      </div>
      <AnimatePresence mode="wait">
        <motion.div
          key={animationKey}
          className="font-bold"
          style={{ 
            color: displayColor,
            fontSize: size === 'small' ? '0.875rem' : '1rem',
          }}
          variants={variants}
          initial="initial"
          animate={animateState}
        >
          {displayValue}
          {isBuffed && buffAmount > 0 && (
            <span className="text-xs ml-0.5" title={`Buffed from ${baseValue} (+${buffAmount})`}>
              ↑
            </span>
          )}
        </motion.div>
      </AnimatePresence>
      
      {/* Flash overlay for dramatic effect - using state-based timing (#114) */}
      <AnimatePresence>
        {flashType === 'increase' && (
          <motion.div
            key="flash-increase"
            className="absolute inset-0 rounded pointer-events-none"
            style={{ backgroundColor: '#4ade80' }}
            initial={{ opacity: 0.6 }}
            animate={{ opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          />
        )}
        {flashType === 'decrease' && (
          <motion.div
            key="flash-decrease"
            className="absolute inset-0 rounded pointer-events-none"
            style={{ backgroundColor: '#f87171' }}
            initial={{ opacity: 0.6 }}
            animate={{ opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
