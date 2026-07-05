/**
 * LoadingScreen Component
 * Initial loading screen that wakes up backend and preloads card data.
 *
 * Restyled to Paper & Ink (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md) — desk
 * gradient background, Gochi Hand title, gold spinner/progress accents.
 *
 * Cold-start expectation (Régis-approved, Phase 3 PR 5): the production
 * backend is Render free tier — it's either warm (health responds within a
 * few seconds) or cold (takes just under a minute to spin up). Rather than a
 * vague "waking up, could be a while" message, we set that expectation
 * honestly: a short quick-path window, then an explicit "about a minute"
 * message with a time-based progress bar calibrated to ~55s. The bar
 * approaches but never reaches 100% until the health check actually
 * succeeds — it should never look "done" while still polling.
 *
 * Decorative emoji removed per §8 (☕); none of these are content-bearing
 * state badges.
 */

import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { Card } from '../types/game';

interface LoadingScreenProps {
  onReady: (cards: Card[]) => void;
  /** Test/preview seam: when true, skips the quick-path window and forces
   *  the cold-start "waking up" presentation immediately — used by the
   *  /design.html#loading fixture so the interesting state is visible
   *  offline without waiting out the real quick-path timer. */
  coldStartOverride?: boolean;
}

// Quick path: if health responds within this window, proceed as normal —
// this covers the "already warm" case (the common case after the first
// visit of the day).
const QUICK_PATH_MS = 2500;

// Cold-start progress is calibrated to Render free tier's observed wake time
// (consistently just under a minute). The bar approaches, but never reaches,
// 100% on its own — only an actual successful health check completes it.
const COLD_START_ESTIMATE_MS = 55000;
const COLD_START_PROGRESS_TICK_MS = 200;
// Asymptotic cap so the bar visibly slows rather than snapping to a hard
// ceiling — still reads as "almost there" without ever claiming done.
const COLD_START_MAX_PROGRESS = 96;

export function LoadingScreen({ onReady, coldStartOverride }: LoadingScreenProps) {
  const [status, setStatus] = useState<'checking' | 'waking' | 'loading' | 'ready' | 'error'>(
    coldStartOverride ? 'waking' : 'checking'
  );
  const [dots, setDots] = useState('');
  const [coldStartProgress, setColdStartProgress] = useState(0);
  const wakingStartRef = useRef<number | null>(coldStartOverride ? Date.now() : null);

  // Check backend health
  const healthCheck = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      if (coldStartOverride) {
        // Preview harness: never actually resolves, so the waking state
        // stays visible indefinitely instead of flashing to "ready".
        return new Promise<never>(() => {});
      }
      const response = await apiClient.get('/health');
      return response.data;
    },
    retry: Infinity, // Retry indefinitely
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000), // Max 10s between retries
    enabled: status === 'checking' || status === 'waking',
  });

  // Load cards once backend is healthy
  const cardsQuery = useQuery({
    queryKey: ['cards'],
    queryFn: async () => {
      const response = await apiClient.get<Card[]>('/games/cards');
      return response.data;
    },
    enabled: healthCheck.isSuccess && status === 'loading',
    retry: 3,
  });

  // Animated dots for loading messages
  useEffect(() => {
    if (status === 'ready' || status === 'error') return;
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);
    return () => clearInterval(interval);
  }, [status]);

  // Quick-path timer: if we're still "checking" after QUICK_PATH_MS, the
  // backend is cold — switch to the honest waking message. Skipped when
  // coldStartOverride forces the waking state from the start.
  useEffect(() => {
    if (coldStartOverride) return;
    if (status !== 'checking') return;
    const timer = setTimeout(() => {
      setStatus((current) => (current === 'checking' ? 'waking' : current));
    }, QUICK_PATH_MS);
    return () => clearTimeout(timer);
  }, [status, coldStartOverride]);

  // Track when we entered "waking" so progress is time-based, not
  // retry-count-based (a real quick retry backoff doesn't line up with the
  // ~55s wake estimate).
  useEffect(() => {
    if (status === 'waking' && wakingStartRef.current === null) {
      wakingStartRef.current = Date.now();
    }
    if (status !== 'waking') {
      wakingStartRef.current = null;
      setColdStartProgress(0);
    }
  }, [status]);

  useEffect(() => {
    if (status !== 'waking') return;
    const interval = setInterval(() => {
      const start = wakingStartRef.current;
      if (start === null) return;
      const elapsed = Date.now() - start;
      // Asymptotic approach to COLD_START_MAX_PROGRESS so it never reads as
      // finished before the health check actually succeeds.
      const linear = Math.min(100, (elapsed / COLD_START_ESTIMATE_MS) * 100);
      setColdStartProgress(Math.min(COLD_START_MAX_PROGRESS, linear));
    }, COLD_START_PROGRESS_TICK_MS);
    return () => clearInterval(interval);
  }, [status]);

  useEffect(() => {
    if (coldStartOverride) return; // stay in the forced waking state
    if (healthCheck.isError) {
      setStatus((current) => (current === 'checking' ? 'waking' : current));
    } else if (healthCheck.isSuccess && (status === 'checking' || status === 'waking')) {
      setColdStartProgress(100);
      setStatus('loading');
    }
  }, [healthCheck.isError, healthCheck.isSuccess, status, coldStartOverride]);

  useEffect(() => {
    if (cardsQuery.isSuccess && cardsQuery.data) {
      setStatus('ready');
      setTimeout(() => onReady(cardsQuery.data), 500);
    } else if (cardsQuery.isError) {
      setStatus('error');
    }
  }, [cardsQuery.isSuccess, cardsQuery.isError, cardsQuery.data, onReady]);

  const getStatusMessage = () => {
    switch (status) {
      case 'checking':
        return 'Connecting to game server';
      case 'waking':
        return 'Waking up the game server';
      case 'loading':
        return 'Loading cards';
      case 'ready':
        return 'Ready to play!';
      case 'error':
        return 'Unable to connect';
    }
  };

  const showWakeupInfo = status === 'waking';

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center"
      style={{
        padding: 'var(--spacing-component-lg)',
        background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))',
        color: 'var(--ink-text)',
      }}
    >
      {/* Logo */}
      <h1
        style={{
          fontFamily: 'var(--font-card-name)',
          fontSize: 'clamp(48px, 10vw, 72px)',
          lineHeight: 1,
          color: 'var(--ink-text)',
          marginBottom: 'var(--spacing-component-sm)',
        }}
      >
        GGLTCG
      </h1>

      <p style={{ fontSize: 'clamp(16px, 3vw, 20px)', fontWeight: 700, color: 'var(--ink-muted)', marginBottom: 'var(--spacing-component-xl)' }}>
        Googooland Trading Card Game
      </p>

      {/* Status Message */}
      <div
        style={{
          fontSize: '17px',
          fontWeight: 700,
          color: status === 'error' ? 'var(--danger)' : 'var(--ink-muted)',
          marginBottom: 'var(--spacing-component-lg)',
          minHeight: '2rem',
        }}
      >
        {getStatusMessage()}{status !== 'ready' && status !== 'error' && dots}
      </div>

      {/* Loading Spinner */}
      {status !== 'ready' && status !== 'error' && (
        <div
          className="loading-screen-spinner"
          style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            border: '4px solid rgba(242,193,78,.2)',
            borderTopColor: 'var(--gold)',
            animation: 'spin 1s linear infinite',
          }}
        />
      )}

      {/* Error Actions */}
      {status === 'error' && (
        <button
          onClick={() => window.location.reload()}
          style={{
            marginTop: 'var(--spacing-component-md)',
            padding: 'var(--spacing-component-sm) var(--spacing-component-lg)',
            borderRadius: '6px',
            border: 'none',
            fontWeight: 900,
            background: 'var(--gold)',
            color: 'var(--desk-bottom)',
            boxShadow: '0 3px 0 rgba(0,0,0,.5)',
            cursor: 'pointer',
          }}
        >
          Refresh Page
        </button>
      )}

      {/* CSS for spinner animation */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @media (prefers-reduced-motion: reduce) {
          .loading-screen-spinner {
            animation: none !important;
          }
        }
      `}</style>

      {/* Cold-start info box — shown once the quick-path window has elapsed
          with no response, i.e. the backend is actually cold. */}
      {showWakeupInfo && (
        <div
          className="text-center"
          data-testid="cold-start-info"
          style={{
            marginTop: 'var(--spacing-component-xl)',
            padding: 'var(--spacing-component-md)',
            maxWidth: '400px',
            background: '#241E17',
            border: '1px solid rgba(242,193,78,.25)',
            borderRadius: '8px',
          }}
        >
          <p style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>
            <span style={{ color: 'var(--gold)', fontWeight: 700 }}>First visit of the day?</span> The
            server is waking up — it takes about a minute. After this, it&apos;ll be instant.
          </p>

          {/* Progress indicator — time-based, calibrated to ~55s; approaches
              but never hits 100% until the health check actually succeeds. */}
          <div
            style={{
              marginTop: 'var(--spacing-component-md)',
              height: '4px',
              borderRadius: '999px',
              overflow: 'hidden',
              background: 'rgba(237,232,222,.1)',
            }}
          >
            <div
              style={{
                width: `${coldStartProgress}%`,
                height: '100%',
                borderRadius: '999px',
                background: 'var(--gold)',
                transition: 'width 200ms linear',
              }}
            />
          </div>
        </div>
      )}

      {/* Tagline at bottom */}
      <p
        className="absolute bottom-8"
        style={{ fontSize: '12px', color: 'var(--ink-faint)' }}
      >
        A tactical card game where strategy meets imagination
      </p>
    </div>
  );
}
