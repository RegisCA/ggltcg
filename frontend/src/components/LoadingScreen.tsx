/**
 * LoadingScreen Component
 * Initial loading screen that wakes up backend and preloads card data.
 * Enhanced with better branding and expectation setting for backend wake-up time.
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
    const retryCount = healthCheck.failureCount || 0;
    switch (status) {
      case 'checking':
        return 'Connecting to game server';
      case 'waking':
        return retryCount <= 2 
          ? 'Waking up game server' 
          : 'Server is warming up';
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
      className="min-h-screen bg-game-bg flex flex-col items-center justify-center text-white"
      style={{ padding: 'var(--spacing-component-lg)' }}
    >
      {/* Logo */}
      <h1 
        className="text-6xl sm:text-7xl font-bold text-game-highlight"
        style={{ 
          marginBottom: 'var(--spacing-component-sm)',
          fontWeight: 700,
          textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
        }}
      >
        GGLTCG
      </h1>

      <p 
        className="text-xl text-gray-300"
        style={{ marginBottom: 'var(--spacing-component-xl)' }}
      >
        Googooland Trading Card Game
      </p>

      {/* Status Message */}
      <div 
        className={`text-lg ${status === 'error' ? 'text-red-400' : 'text-gray-200'}`}
        style={{ marginBottom: 'var(--spacing-component-lg)', minHeight: '2rem' }}
      >
        {getStatusMessage()}{status !== 'ready' && status !== 'error' && dots}
      </div>

      {/* Loading Spinner */}
      {status !== 'ready' && status !== 'error' && (
        <div 
          className="border-4 border-game-highlight/20 rounded-full"
          style={{
            width: '48px',
            height: '48px',
            borderTopColor: 'var(--color-game-highlight)',
            animation: 'spin 1s linear infinite',
          }}
        />
      )}

      {/* Error Actions */}
      {status === 'error' && (
        <button
          onClick={() => window.location.reload()}
          className="bg-game-highlight hover:bg-red-600 text-white font-semibold rounded transition-colors"
          style={{ 
            marginTop: 'var(--spacing-component-md)',
            padding: 'var(--spacing-component-sm) var(--spacing-component-lg)',
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
      `}</style>

      {/* Wake-up Info Box */}
      {showWakeupInfo && (
        <div 
          className="bg-game-card border border-gray-600 rounded-lg text-center"
          style={{
            marginTop: 'var(--spacing-component-xl)',
            padding: 'var(--spacing-component-md)',
            maxWidth: '400px',
          }}
        >
          <p className="text-gray-300 text-sm" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
            <span className="text-yellow-400 font-semibold">☕ First visit?</span> The game server 
            runs on a free tier and may be asleep.
          </p>
          <p className="text-gray-400 text-sm">
            This can take up to <span className="text-white font-medium">50 seconds</span> the first time. 
            After that, it's instant!
          </p>
          
          {/* Progress indicator */}
          <div 
            className="bg-gray-700 rounded-full overflow-hidden"
            style={{ marginTop: 'var(--spacing-component-md)', height: '4px' }}
          >
            <div 
              className="bg-game-highlight h-full rounded-full"
              style={{
                width: `${Math.min(retryCount * 15, 90)}%`,
                transition: 'width 1s ease-out',
              }}
            />
          </div>
        </div>
      )}

      {/* Tagline at bottom */}
      <p 
        className="text-gray-500 text-sm absolute bottom-8"
      >
        A tactical card game where strategy meets imagination
      </p>
    </div>
  );
}
