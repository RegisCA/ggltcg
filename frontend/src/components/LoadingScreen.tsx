/**
 * LoadingScreen Component
 * Initial loading screen that wakes up backend and preloads card data
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
        return 'Connecting to game server...';
      case 'waking':
        return retryCount <= 2 
          ? 'Waking up game server...' 
          : 'Game server is warming up (this can take up to 50 seconds)...';
      case 'loading':
        return 'Loading card database...';
      case 'ready':
        return 'Ready to play!';
      case 'error':
        return 'Unable to connect to game server. Please refresh the page.';
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#1a1a2e',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'white',
      padding: '2rem',
    }}>
      {/* Logo */}
      <div style={{
        fontSize: '4rem',
        fontWeight: 'bold',
        marginBottom: '2rem',
        textAlign: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
      }}>
        GGLTCG
      </div>

      <div style={{
        fontSize: '1.5rem',
        color: '#a0a0c0',
        marginBottom: '3rem',
        textAlign: 'center',
      }}>
        Googooland Trading Card Game
      </div>

      {/* Status Message */}
      <div style={{
        fontSize: '1.125rem',
        color: status === 'error' ? '#ff6b6b' : '#e0e0ff',
        marginBottom: '2rem',
        textAlign: 'center',
        minHeight: '2rem',
      }}>
        {getStatusMessage()}{status !== 'ready' && status !== 'error' && dots}
      </div>

      {/* Loading Spinner */}
      {status !== 'ready' && status !== 'error' && (
        <div style={{
          width: '48px',
          height: '48px',
          border: '4px solid rgba(102, 126, 234, 0.2)',
          borderTopColor: '#667eea',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }} />
      )}

      {/* Error Actions */}
      {status === 'error' && (
        <button
          onClick={() => window.location.reload()}
          style={{
            marginTop: '1rem',
            padding: '0.75rem 1.5rem',
            backgroundColor: '#667eea',
            color: 'white',
            border: 'none',
            borderRadius: '0.5rem',
            fontSize: '1rem',
            cursor: 'pointer',
            fontWeight: '600',
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

      {/* Note about free tier */}
      {status === 'waking' && (healthCheck.failureCount || 0) > 1 && (
        <div style={{
          marginTop: '3rem',
          padding: '1rem',
          backgroundColor: 'rgba(102, 126, 234, 0.1)',
          borderRadius: '0.5rem',
          maxWidth: '500px',
          fontSize: '0.875rem',
          color: '#a0a0c0',
          textAlign: 'center',
          lineHeight: '1.5',
        }}>
          <strong>Note:</strong> The game server runs on a free tier and may be asleep. 
          First load can take up to 50 seconds while the server wakes up. 
          Subsequent plays will be much faster!
        </div>
      )}
    </div>
  );
}
