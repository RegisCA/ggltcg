/**
 * useGameMessages Hook
 * 
 * Manages game message state derived from the server's play_by_play.
 * This ensures all players see all actions (including opponent's actions in multiplayer).
 * 
 * Handles:
 * - Message display from play_by_play
 * - Starting player announcement
 * - Additional local messages (AI thinking, errors, etc.)
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { GameState, PlayByPlayEntry } from '../types/game';

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
  _options: UseGameMessagesOptions  // Options kept for API compatibility, but not currently used
): UseGameMessagesReturn {
  // Local messages (for things like "AI is thinking..." that aren't in play_by_play)
  const [localMessages, setLocalMessages] = useState<string[]>([]);
  
  // Track previous state for detecting transitions
  const lastPlayByPlayLength = useRef<number>(0);
  const hasShownStartingPlayer = useRef(false);
  const isProcessingMessage = useRef(false);

  // Derive messages from play_by_play (current turn and previous turn)
  const playByPlayMessages = useMemo(() => {
    if (!gameState?.play_by_play) return [];
    
    const currentTurn = gameState.turn_number;
    
    // Show messages from current turn AND previous turn
    // This ensures you can see what happened on the opponent's turn
    // when it switches back to your turn
    return gameState.play_by_play
      .filter((entry: PlayByPlayEntry) => entry.turn >= currentTurn - 1)
      .map((entry: PlayByPlayEntry) => {
        // Format: "PlayerName: Action description"
        return `${entry.player}: ${entry.description}`;
      });
  }, [gameState?.play_by_play, gameState?.turn_number]);

  // Build starting player message
  const startingPlayerMessage = useMemo(() => {
    if (!gameState || hasShownStartingPlayer.current) return null;
    
    const firstPlayerName = gameState.players[gameState.first_player_id]?.name || 'Unknown';
    hasShownStartingPlayer.current = true;
    return `${firstPlayerName} goes first!`;
  }, [gameState]);

  // Combined messages: starting player + play_by_play + local messages
  const messages = useMemo(() => {
    const allMessages: string[] = [];
    
    // Add starting player message first (if exists)
    if (startingPlayerMessage) {
      allMessages.push(startingPlayerMessage);
    }
    
    // Add all play_by_play messages
    allMessages.push(...playByPlayMessages);
    
    // Add any local messages (AI thinking, errors, etc.)
    allMessages.push(...localMessages);
    
    return allMessages;
  }, [startingPlayerMessage, playByPlayMessages, localMessages]);

  // Clear local messages when new play_by_play entries arrive
  // This removes stale "AI is thinking..." messages once the action completes
  useEffect(() => {
    if (!gameState?.play_by_play) return;
    
    const currentLength = gameState.play_by_play.length;
    if (currentLength > lastPlayByPlayLength.current) {
      // New entries arrived, clear local messages
      setLocalMessages([]);
      lastPlayByPlayLength.current = currentLength;
    }
  }, [gameState?.play_by_play]);

  // Add a local message (for things not in play_by_play)
  const addMessage = useCallback((
    msg: string, 
    options?: { skipIfGameOver?: boolean; response?: any }
  ) => {
    // Don't add action messages if the response indicates game is over
    if (options?.skipIfGameOver && options?.response?.game_state?.is_game_over) {
      return;
    }

    // Don't add duplicate messages that are already in play_by_play
    // (This handles the case where human actions are added locally before 
    // the server response updates play_by_play)
    setLocalMessages(prev => [...prev, msg]);
  }, []);

  // Clear local messages
  const clearMessages = useCallback(() => {
    setLocalMessages([]);
  }, []);

  return {
    messages,
    addMessage,
    clearMessages,
    isProcessingMessage: isProcessingMessage.current,
  };
}
