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

import { useState, useEffect } from 'react';

export function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    // SSR-safe: default to false (animations enabled) on server
    if (typeof window === 'undefined') {
      return false;
    }
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    
    // Set initial value
    setPrefersReducedMotion(mediaQuery.matches);

    // Listen for changes (user may toggle setting while app is open)
    const handleChange = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };

    // Modern browsers use addEventListener, older use addListener
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } else {
      // Fallback for older browsers
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, []);

  return prefersReducedMotion;
}
