/**
 * useResponsive Hook
 * 
 * Provides responsive breakpoint detection for adaptive layouts.
 * Based on common breakpoints: mobile (<640), tablet (640-1024), desktop (>1024)
 */

import { useState, useEffect } from 'react';

interface ResponsiveState {
  isMobile: boolean;      // < 640px
  isTablet: boolean;      // 640-1024px
  isDesktop: boolean;     // > 1024px
  width: number;
}

export function useResponsive(): ResponsiveState {
  const [state, setState] = useState<ResponsiveState>(() => {
    // SSR-safe initial state
    if (typeof window === 'undefined') {
      return { isMobile: false, isTablet: false, isDesktop: true, width: 1200 };
    }
    const width = window.innerWidth;
    return {
      isMobile: width < 640,
      isTablet: width >= 640 && width <= 1024,
      isDesktop: width > 1024,
      width,
    };
  });

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      setState({
        isMobile: width < 640,
        isTablet: width >= 640 && width <= 1024,
        isDesktop: width > 1024,
        width,
      });
    };

    // Set initial state
    handleResize();

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return state;
}
