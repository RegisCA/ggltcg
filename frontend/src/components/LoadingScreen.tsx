/**
 * LoadingScreen Component
 * Initial loading screen that wakes up backend and preloads card data.
 *
 * Restyled to Paper & Ink (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md) — desk
 * gradient background, Gochi Hand title, gold spinner/progress accents.
 *
 * Decorative emoji removed per §8 (☕); none of these are content-bearing
 * state badges.
 */

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { Card } from '../types/game';

interface LoadingScreenProps {
  onReady: (cards: Card[]) => void;
}

export function LoadingScreen({ onReady }: LoadingScreenProps) {
  const [status, setStatus] = useState<'checking' | 'waking' | 'loading' | 'ready' | 'error'>('checking');
  const [dots, setDots] = useState('');

  // Check backend health
  const healthCheck = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
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

  useEffect(() => {
    if (healthCheck.isError) {
      setStatus('waking');
    } else if (healthCheck.isSuccess && status === 'checking') {
      setStatus('loading');
    }
  }, [healthCheck.isError, healthCheck.isSuccess, status]);

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
        return 'Waking up game server (up to 50 seconds)';
      case 'loading':
        return 'Loading cards';
      case 'ready':
        return 'Ready to play!';
      case 'error':
        return 'Unable to connect';
    }
  };

  const retryCount = healthCheck.failureCount || 0;
  const showWakeupInfo = status === 'waking' && retryCount > 1;

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

      {/* Wake-up Info Box - shows after a few retries */}
      {showWakeupInfo && (
        <div
          className="text-center"
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
            <span style={{ color: 'var(--gold)', fontWeight: 700 }}>First visit of the day?</span> The server
            is waking up. After this, it&apos;ll be instant!
          </p>

          {/* Progress indicator */}
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
                width: `${Math.min(retryCount * 15, 90)}%`,
                height: '100%',
                borderRadius: '999px',
                background: 'var(--gold)',
                transition: 'width 1s ease-out',
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
