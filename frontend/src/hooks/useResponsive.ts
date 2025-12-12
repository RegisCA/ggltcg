/**
 * useResponsive Hook
 * 
 * Provides responsive breakpoint detection for adaptive layouts.
 * Based on common breakpoints: mobile (<640), tablet (640-1024), desktop (>1024)
 * Also detects landscape orientation for tablets.
 * 
 * Uses visualViewport API when available for more accurate measurements
 * across different mobile browsers (especially iOS Chrome vs Safari).
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

/**
 * Get viewport dimensions using the most reliable method available.
 * visualViewport API provides the actual visible viewport size,
 * accounting for browser chrome, pinch-zoom, and on-screen keyboards.
 */
function getViewportDimensions(): { width: number; height: number } {
  if (typeof window === 'undefined') {
    return { width: 1200, height: 800 };
  }

  // Try visualViewport first (more accurate on mobile)
  if (window.visualViewport) {
    return {
      width: window.visualViewport.width,
      height: window.visualViewport.height,
    };
  }

  // Fallback to document.documentElement (more reliable than window.innerWidth on some browsers)
  const docEl = document.documentElement;
  return {
    width: docEl.clientWidth || window.innerWidth,
    height: docEl.clientHeight || window.innerHeight,
  };
}

export function useResponsive(): ResponsiveState {
  const [state, setState] = useState<ResponsiveState>(() => {
    const { width, height } = getViewportDimensions();
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
    const updateState = () => {
      const { width, height } = getViewportDimensions();
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
    updateState();

    // Listen to resize events
    window.addEventListener('resize', updateState);
    
    // Also listen to visualViewport changes if available
    // This catches pinch-zoom and on-screen keyboard events
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', updateState);
    }

    // Listen to orientation changes (more reliable on mobile)
    window.addEventListener('orientationchange', () => {
      // Delay slightly to let the browser settle after orientation change
      setTimeout(updateState, 100);
    });

    return () => {
      window.removeEventListener('resize', updateState);
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('resize', updateState);
      }
      window.removeEventListener('orientationchange', updateState);
    };
  }, []);

  return state;
}
