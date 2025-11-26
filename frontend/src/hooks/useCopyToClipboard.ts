/**
 * useCopyToClipboard Hook
 * 
 * Reusable hook for clipboard functionality with visual feedback.
 * Automatically resets the "copied" state after a delay.
 */

import { useState, useCallback } from 'react';

interface UseCopyToClipboardOptions {
  /** Duration in ms to show "copied" feedback (default: 2000) */
  resetDelay?: number;
}

interface UseCopyToClipboardReturn {
  /** Whether text was recently copied */
  copied: boolean;
  /** Copy text to clipboard */
  copyToClipboard: (text: string) => Promise<boolean>;
  /** Manually reset the copied state */
  reset: () => void;
}

export function useCopyToClipboard(
  options: UseCopyToClipboardOptions = {}
): UseCopyToClipboardReturn {
  const { resetDelay = 2000 } = options;
  const [copied, setCopied] = useState(false);

  const copyToClipboard = useCallback(async (text: string): Promise<boolean> => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      
      // Auto-reset after delay
      setTimeout(() => {
        setCopied(false);
      }, resetDelay);
      
      return true;
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      return false;
    }
  }, [resetDelay]);

  const reset = useCallback(() => {
    setCopied(false);
  }, []);

  return {
    copied,
    copyToClipboard,
    reset,
  };
}
