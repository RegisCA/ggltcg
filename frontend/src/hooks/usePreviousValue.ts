/**
 * usePreviousValue Hook
 * 
 * Tracks the previous value of a variable across renders.
 * Useful for detecting changes and triggering animations.
 */

import { useRef, useEffect } from 'react';

export function usePreviousValue<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined);
  
  useEffect(() => {
    ref.current = value;
  }, [value]);
  
  return ref.current;
}
