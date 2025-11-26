/**
 * useResponsive Hook
 * 
 * Provides responsive breakpoint detection for adaptive layouts.
 * Based on common breakpoints: mobile (<640), tablet (640-1024), desktop (>1024)
 * Also detects landscape orientation for tablets.
 */

import { useState, useEffect } from 'react';

interface ResponsiveState {
  isMobile: boolean;      // < 640px width
  isTablet: boolean;      // 640-1024px width
  isDesktop: boolean;     // > 1024px width
  isLandscape: boolean;   // width > height
  width: number;
  height: number;
}

export function useResponsive(): ResponsiveState {
  const [state, setState] = useState<ResponsiveState>(() => {
    // SSR-safe initial state
    if (typeof window === 'undefined') {
      return { isMobile: false, isTablet: false, isDesktop: true, isLandscape: true, width: 1200, height: 800 };
    }
    const width = window.innerWidth;
    const height = window.innerHeight;
    return {
      isMobile: width < 640,
      isTablet: width >= 640 && width <= 1024,
      isDesktop: width > 1024,
      isLandscape: width > height,
      width,
      height,
    };
  });

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      setState({
        isMobile: width < 640,
        isTablet: width >= 640 && width <= 1024,
        isDesktop: width > 1024,
        isLandscape: width > height,
        width,
        height,
      });
    };

    // Set initial state
    handleResize();

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return state;
}
