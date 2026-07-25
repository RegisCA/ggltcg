/**
 * useChangeFlash Hook
 *
 * Reports a transient 'increase' | 'decrease' signal when a numeric value
 * changes, clearing itself after `durationMs`. Drives the stat-flash and
 * charge-pulse animations.
 *
 * Replaces the older usePreviousValue + useEffect pairing: comparing against
 * the last-seen value during render keeps the signal in state, so the reset no
 * longer depends on an incidental re-render happening to re-run the comparison.
 */

import { useState, useEffect } from 'react';

export type ChangeFlash = 'increase' | 'decrease' | null;

type Numeric = number | null | undefined;

export function useChangeFlash(value: Numeric, durationMs = 500): ChangeFlash {
  const [lastSeen, setLastSeen] = useState<Numeric>(value);
  const [flash, setFlash] = useState<ChangeFlash>(null);

  if (lastSeen !== value) {
    setLastSeen(value);
    if (typeof value === 'number' && typeof lastSeen === 'number') {
      setFlash(value > lastSeen ? 'increase' : 'decrease');
    }
  }

  useEffect(() => {
    if (!flash) return;
    const timer = setTimeout(() => setFlash(null), durationMs);
    return () => clearTimeout(timer);
  }, [flash, durationMs]);

  return flash;
}
