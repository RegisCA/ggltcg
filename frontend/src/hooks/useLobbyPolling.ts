/**
 * useLobbyPolling Hook
 * 
 * Handles all polling logic for lobby status:
 * - Poll for player2 joining
 * - Poll for deck submission status  
 * - Poll for game start
 */

import { useState, useEffect, useCallback } from 'react';
import { getLobbyStatus } from '../api/gameService';

export type LobbyPhase = 
  | 'waiting-for-player' 
  | 'deck-selection' 
  | 'waiting-for-decks' 
  | 'starting';

interface LobbyState {
  phase: LobbyPhase;
  otherPlayerName: string | null;
  otherPlayerReady: boolean;
}

interface UseLobbyPollingOptions {
  gameCode: string;
  initialOtherPlayerName: string | null;
  onGameReady?: () => void;
}

interface UseLobbyPollingReturn {
  phase: LobbyPhase;
  otherPlayerName: string | null;
  otherPlayerReady: boolean;
  setPhase: (phase: LobbyPhase) => void;
  setCurrentPlayerReady: () => void;
}

export function useLobbyPolling(options: UseLobbyPollingOptions): UseLobbyPollingReturn {
  const { gameCode, initialOtherPlayerName, onGameReady } = options;

  const [state, setState] = useState<LobbyState>({
    phase: initialOtherPlayerName ? 'deck-selection' : 'waiting-for-player',
    otherPlayerName: initialOtherPlayerName,
    otherPlayerReady: false,
  });

  // Poll for lobby status when waiting for player 2 or waiting for deck submissions
  useEffect(() => {
    if (state.phase !== 'waiting-for-player' && state.phase !== 'waiting-for-decks') {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const status = await getLobbyStatus(gameCode);

        // Player 2 joined
        if (state.phase === 'waiting-for-player' && status.player2_name) {
          setState(prev => ({
            ...prev,
            otherPlayerName: status.player2_name,
            phase: 'deck-selection',
          }));
        }

        // Check if both players are ready (other player submitted deck)
        if (state.phase === 'waiting-for-decks' && status.ready_to_start) {
          setState(prev => ({
            ...prev,
            otherPlayerReady: true,
            phase: 'starting',
          }));
        }
      } catch (err) {
        console.error('Failed to poll lobby status:', err);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [gameCode, state.phase]);

  // When both players ready and status is 'starting', poll for game state
  useEffect(() => {
    if (state.phase !== 'starting') {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const status = await getLobbyStatus(gameCode);
        
        // Check if game has started
        if (status.ready_to_start) {
          onGameReady?.();
        }
      } catch (err) {
        console.error('Failed to check game start:', err);
      }
    }, 1000); // Poll more frequently when starting

    return () => clearInterval(pollInterval);
  }, [state.phase, gameCode, onGameReady]);

  const setPhase = useCallback((phase: LobbyPhase) => {
    setState(prev => ({ ...prev, phase }));
  }, []);

  const setCurrentPlayerReady = useCallback(() => {
    setState(prev => ({ ...prev, phase: 'waiting-for-decks' }));
  }, []);

  return {
    phase: state.phase,
    otherPlayerName: state.otherPlayerName,
    otherPlayerReady: state.otherPlayerReady,
    setPhase,
    setCurrentPlayerReady,
  };
}
