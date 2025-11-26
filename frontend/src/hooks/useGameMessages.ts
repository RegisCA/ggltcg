/**
 * useGameMessages Hook
 * 
 * Manages game message state and clearing logic.
 * Handles:
 * - Message display
 * - Starting player announcement
 * - Auto-clearing on turn transitions
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { GameState } from '../types/game';

interface UseGameMessagesOptions {
  humanPlayerId: string;
  aiPlayerId?: string;
}

interface UseGameMessagesReturn {
  messages: string[];
  addMessage: (msg: string, options?: { skipIfGameOver?: boolean; response?: any }) => void;
  clearMessages: () => void;
  isProcessingMessage: boolean;
}

export function useGameMessages(
  gameState: GameState | undefined,
  options: UseGameMessagesOptions
): UseGameMessagesReturn {
  const { humanPlayerId, aiPlayerId } = options;
  
  const [messages, setMessages] = useState<string[]>([]);
  const [shouldClearOnNextAction, setShouldClearOnNextAction] = useState(false);
  
  // Track previous state for detecting transitions
  const lastTurnNumber = useRef<number>(0);
  const lastActivePlayerId = useRef<string>('');
  const isProcessingMessage = useRef(false);

  // Show starting player announcement and manage message clearing
  useEffect(() => {
    if (!gameState) return;

    const currentTurn = gameState.turn_number;
    const currentActivePlayer = gameState.active_player_id;

    // Show starting player announcement on turn 1, first load
    if (currentTurn === 1 && lastTurnNumber.current === 0 && !lastActivePlayerId.current) {
      const firstPlayerName = gameState.players[gameState.first_player_id]?.name || 'Unknown';
      setMessages([`${firstPlayerName} goes first!`]);
      lastTurnNumber.current = 1;
      lastActivePlayerId.current = currentActivePlayer;
      
      // If human goes first, set flag to clear on their first action
      if (currentActivePlayer === humanPlayerId) {
        setShouldClearOnNextAction(true);
      }
      return;
    }

    // When active player changes, handle message clearing
    if (currentActivePlayer !== lastActivePlayerId.current && lastActivePlayerId.current !== '') {
      if (currentActivePlayer === humanPlayerId) {
        // Transitioning to human: set flag to clear on their first action
        setShouldClearOnNextAction(true);
        lastActivePlayerId.current = currentActivePlayer;
      } else if (aiPlayerId && currentActivePlayer === aiPlayerId) {
        // Transitioning to AI: clear messages immediately
        setMessages([]);
        lastActivePlayerId.current = currentActivePlayer;
      } else {
        // Transitioning to other human player in multiplayer
        lastActivePlayerId.current = currentActivePlayer;
      }
    }

    // Track turn number changes
    if (currentTurn !== lastTurnNumber.current) {
      lastTurnNumber.current = currentTurn;
    }
  }, [gameState, humanPlayerId, aiPlayerId]);

  // Add a message with optional clearing behavior
  const addMessage = useCallback((
    msg: string, 
    options?: { skipIfGameOver?: boolean; response?: any }
  ) => {
    // Don't add action messages if the response indicates game is over
    if (options?.skipIfGameOver && options?.response?.game_state?.is_game_over) {
      return;
    }

    setMessages(prev => {
      if (shouldClearOnNextAction) {
        setShouldClearOnNextAction(false);
        return [msg];
      }
      return [...prev, msg];
    });
  }, [shouldClearOnNextAction]);

  // Clear all messages
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    addMessage,
    clearMessages,
    isProcessingMessage: isProcessingMessage.current,
  };
}
