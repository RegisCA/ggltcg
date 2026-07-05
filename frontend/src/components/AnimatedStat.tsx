/**
 * AnimatedStat — a single stat box in a card's left stat rail (Paper & Ink §4).
 *
 * Box: 1.5px identity-crayon border, faint uppercase label (7px/900), value 900.
 * Value color is material-aware: buffed → gold (gold-on-paper on cream), damaged
 * → danger red, otherwise the card's normal text. Damaged stamina shows
 * `current/max` with the "/max" faint. Colors are passed in by CardDisplay from
 * the owner material + identity crayon; this component owns only the box + the
 * transient flash when a value changes.
 *
 * Respects reduced-motion (WCAG 2.1).
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePreviousValue } from '../hooks/usePreviousValue';
import { useReducedMotion } from '../hooks/useReducedMotion';

interface AnimatedStatProps {
  value: number | null;
  baseValue?: number | null;
  label: string;
  /** For stamina: show current/max and color as damaged when current < value. */
  currentValue?: number | null;
  size: 'small' | 'medium' | 'large';
  /** Identity crayon — the box border. */
  crayonColor: string;
  /** Faint label + "/max" color (material text-faint). */
  labelColor: string;
  /** Normal value color (material text). */
  valueColor: string;
  /** Buffed value color (material buffed: gold / gold-on-paper). */
  buffedColor: string;
  /** Damaged value color (material danger). */
  damagedColor: string;
}

// Box geometry per size (§4 rail is sized for the medium board card).
const BOX = {
  small: { width: 26, label: 6, value: 11, max: 7 },
  medium: { width: 30, label: 7, value: 13, max: 8 },
  large: { width: 44, label: 10, value: 20, max: 12 },
} as const;

const statVariants = {
  initial: { scale: 1 },
  increased: { scale: [1, 1.3, 1], transition: { duration: 0.4, ease: 'easeOut' as const } },
  decreased: { x: [0, -3, 3, -3, 3, 0], transition: { duration: 0.4, ease: 'easeOut' as const } },
};
const reducedMotionVariants = {
  initial: { scale: 1 },
  increased: { scale: 1 },
  decreased: { scale: 1 },
};

export function AnimatedStat({
  value,
  baseValue,
  label,
  currentValue,
  size,
  crayonColor,
  labelColor,
  valueColor,
  buffedColor,
  damagedColor,
}: AnimatedStatProps) {
  const prefersReducedMotion = useReducedMotion();
  const previousValue = usePreviousValue(value);
  const previousCurrent = usePreviousValue(currentValue);
  const box = BOX[size];

  const [flashType, setFlashType] = useState<'increase' | 'decrease' | null>(null);

  const valueIncreased = previousValue !== undefined && value !== null && previousValue !== null && value > previousValue;
  const valueDecreased = previousValue !== undefined && value !== null && previousValue !== null && value < previousValue;
  const currentDecreased = previousCurrent !== undefined && currentValue !== undefined && currentValue !== null && previousCurrent !== null && currentValue < previousCurrent;
  const currentIncreased = previousCurrent !== undefined && currentValue !== undefined && currentValue !== null && previousCurrent !== null && currentValue > previousCurrent;

  useEffect(() => {
    if (prefersReducedMotion) return;
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

  const animationKey = `${value}-${currentValue}`;

  // Is stamina damaged (current below effective max)?
  const isDamaged = currentValue !== null && currentValue !== undefined && currentValue !== value;
  // Is this stat buffed above its printed base?
  const isBuffed = !isDamaged && value !== null && baseValue !== undefined && baseValue !== null && value > baseValue;

  const displayColor = isDamaged ? damagedColor : isBuffed ? buffedColor : valueColor;

  let animateState: 'initial' | 'increased' | 'decreased' = 'initial';
  if (valueIncreased || currentIncreased) animateState = 'increased';
  else if (valueDecreased || currentDecreased) animateState = 'decreased';

  const variants = prefersReducedMotion ? reducedMotionVariants : statVariants;

  return (
    <div
      style={{
        border: `1.5px solid ${crayonColor}`,
        borderRadius: '3px',
        width: `${box.width}px`,
        textAlign: 'center',
        padding: '1px 0',
        position: 'relative',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          fontSize: `${box.label}px`,
          fontWeight: 900,
          letterSpacing: '.05em',
          color: labelColor,
          lineHeight: 1.1,
        }}
      >
        {label}
      </div>
      <AnimatePresence mode="wait">
        <motion.div
          key={animationKey}
          style={{ fontWeight: 900, fontSize: `${box.value}px`, color: displayColor, lineHeight: 1.1 }}
          variants={variants}
          initial="initial"
          animate={animateState}
        >
          {isDamaged ? currentValue : value}
          {isDamaged && (
            <span style={{ fontSize: `${box.max}px`, color: labelColor }}>/{value}</span>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Transient change flash — gold up / danger down, on-palette (§2). */}
      <AnimatePresence>
        {flashType === 'increase' && (
          <motion.div
            key="flash-increase"
            style={{ position: 'absolute', inset: 0, borderRadius: '3px', pointerEvents: 'none', backgroundColor: 'var(--gold)' }}
            initial={{ opacity: 0.5 }}
            animate={{ opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          />
        )}
        {flashType === 'decrease' && (
          <motion.div
            key="flash-decrease"
            style={{ position: 'absolute', inset: 0, borderRadius: '3px', pointerEvents: 'none', backgroundColor: 'var(--danger)' }}
            initial={{ opacity: 0.5 }}
            animate={{ opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
