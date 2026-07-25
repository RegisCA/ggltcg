/**
 * useReducedMotion Hook
 * 
 * Detects if the user prefers reduced motion based on system settings.
 * This is important for accessibility (WCAG 2.1) - users with vestibular
 * disorders may experience discomfort from animations.
 * 
 * Usage:
 *   const prefersReducedMotion = useReducedMotion();
 *   
 *   // Disable animations if user prefers reduced motion
 *   const animationProps = prefersReducedMotion ? {} : { whileHover: { scale: 1.05 } };
 */

import { useSyncExternalStore } from 'react';

const QUERY = '(prefers-reduced-motion: reduce)';

function subscribe(onChange: () => void): () => void {
  const mediaQuery = window.matchMedia(QUERY);

  // Modern browsers use addEventListener, older use addListener
  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener('change', onChange);
    return () => mediaQuery.removeEventListener('change', onChange);
  }
  mediaQuery.addListener(onChange);
  return () => mediaQuery.removeListener(onChange);
}

export function useReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(QUERY).matches,
    // SSR-safe: default to false (animations enabled) on server
    () => false,
  );
}
