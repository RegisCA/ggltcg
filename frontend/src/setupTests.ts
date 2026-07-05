// Vitest global setup — adds jest-dom matchers (toBeInTheDocument, etc.) to
// `expect` for all test files. Referenced from vite.config.ts `test.setupFiles`.
import '@testing-library/jest-dom/vitest';

// jsdom doesn't implement matchMedia; useReducedMotion (used by CardDisplay,
// via framer-motion-adjacent code) reads it unconditionally on mount.
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }) as unknown as MediaQueryList;
}
