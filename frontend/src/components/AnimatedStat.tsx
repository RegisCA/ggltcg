/**
 * AnimatedStat Component
 * 
 * Displays a stat value with animation when it changes.
 * - Green flash + scale up when value increases
 * - Red flash + shake when value decreases
 */

import { motion, AnimatePresence, type Easing } from 'framer-motion';
import { usePreviousValue } from '../hooks/usePreviousValue';

interface AnimatedStatProps {
  value: number | null;
  baseValue?: number | null;
  label: string;
  accentColor: string;
  size: 'small' | 'medium' | 'large';
  /** For stamina: show current/max format */
  currentValue?: number | null;
}

export function AnimatedStat({
  value,
  baseValue,
  label,
  accentColor,
  size,
  currentValue,
}: AnimatedStatProps) {
  const previousValue = usePreviousValue(value);
  const previousCurrent = usePreviousValue(currentValue);
  
  // Determine if value changed and in which direction
  const valueIncreased = previousValue !== undefined && value !== null && previousValue !== null && value > previousValue;
  const valueDecreased = previousValue !== undefined && value !== null && previousValue !== null && value < previousValue;
  
  // For stamina with current/max, also check current value changes
  const currentDecreased = previousCurrent !== undefined && currentValue !== undefined && currentValue !== null && previousCurrent !== null && currentValue < previousCurrent;
  const currentIncreased = previousCurrent !== undefined && currentValue !== undefined && currentValue !== null && previousCurrent !== null && currentValue > previousCurrent;
  
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
  
  // Animation variants with proper typing
  const easeOut: Easing = 'easeOut';
  const statVariants = {
    initial: { scale: 1 },
    increased: {
      scale: [1, 1.3, 1],
      transition: { duration: 0.4, ease: easeOut }
    },
    decreased: {
      x: [0, -3, 3, -3, 3, 0],
      transition: { duration: 0.4, ease: easeOut }
    },
  };
  
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
          variants={statVariants}
          initial="initial"
          animate={animateState}
        >
          {displayValue}
          {isBuffed && (
            <span className="text-xs ml-0.5">↑</span>
          )}
        </motion.div>
      </AnimatePresence>
      
      {/* Flash overlay for dramatic effect */}
      <AnimatePresence>
        {(valueIncreased || currentIncreased) && (
          <motion.div
            className="absolute inset-0 rounded pointer-events-none"
            style={{ backgroundColor: '#4ade80' }}
            initial={{ opacity: 0.6 }}
            animate={{ opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          />
        )}
        {(valueDecreased || currentDecreased) && (
          <motion.div
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
