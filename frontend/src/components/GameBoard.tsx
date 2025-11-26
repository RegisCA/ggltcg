/**
 * GameBoard Component
 * Main game interface that orchestrates all game components
 */

import { useState, useEffect } from 'react';
import type { ValidAction, GameState, Card } from '../types/game';
import { useGameState, useValidActions, usePlayCard, useTussle, useEndTurn, useActivateAbility, useAITurn } from '../hooks/useGame';
import { PlayerInfoBar } from './PlayerInfoBar';
import { InPlayZone } from './InPlayZone';
import { HandZone } from './HandZone';
import { SleepZoneDisplay } from './SleepZoneDisplay';
import { ActionPanel } from './ActionPanel';
import { TargetSelectionModal } from './TargetSelectionModal';

interface GameBoardProps {
  gameId: string;
  humanPlayerId: string;
  aiPlayerId?: string; // Optional for multiplayer (human vs human)
  onGameEnd: (winner: string, gameState: GameState) => void;
}

export function GameBoard({ gameId, humanPlayerId, aiPlayerId, onGameEnd }: GameBoardProps) {
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [messages, setMessages] = useState<string[]>([]);
  const [lastTurnNumber, setLastTurnNumber] = useState<number>(0);
  const [lastActivePlayerId, setLastActivePlayerId] = useState<string>('');
  const [shouldClearOnNextAction, setShouldClearOnNextAction] = useState(false);
  const [pendingAction, setPendingAction] = useState<ValidAction | null>(null);

  // Fetch game state with polling
  const { data: gameState, isLoading, error } = useGameState(gameId, humanPlayerId, {
    refetchInterval: 2000, // Poll every 2 seconds
  });

  // Clear pendingAction (modal) when turn ends or active player changes
  useEffect(() => {
    if (!gameState) return;
    // If human is not active player, clear modal
    if (gameState.active_player_id !== humanPlayerId && pendingAction) {
      setPendingAction(null);
    }
  }, [gameState?.active_player_id, gameState?.turn_number]);

  // Handle game not found (404 error)
  useEffect(() => {
    if (error) {
      const apiError = error as any;
      if (apiError?.response?.status === 404) {
        alert('Game not found. The server may have restarted. Please create a new game.');
        window.location.reload(); // Reload to go back to deck selection
      }
    }
  }, [error]);

  // Fetch valid actions
  const { data: validActionsData } = useValidActions(gameId, humanPlayerId, {
    enabled: gameState?.active_player_id === humanPlayerId,
  });

  // Mutations
  const playCardMutation = usePlayCard(gameId);
  const tussleMutation = useTussle(gameId);
  const endTurnMutation = useEndTurn(gameId);
  const activateAbilityMutation = useActivateAbility(gameId);
  const aiTurnMutation = useAITurn(gameId);

  const isProcessing =
    playCardMutation.isPending ||
    tussleMutation.isPending ||
    endTurnMutation.isPending ||
    activateAbilityMutation.isPending ||
    aiTurnMutation.isPending;

  // Check for game over
  useEffect(() => {
    if (gameState?.winner) {
      onGameEnd(gameState.winner, gameState);
    }
  }, [gameState?.winner, onGameEnd, gameState]);

  // Show starting player announcement and manage message clearing
  useEffect(() => {
    if (!gameState) return;

    // Show starting player announcement on turn 1, active player change
    if (gameState.turn_number === 1 && lastTurnNumber === 0 && !lastActivePlayerId) {
      const firstPlayerName = gameState.players[gameState.first_player_id]?.name || 'Unknown';
      setMessages([`${firstPlayerName} goes first!`]);
      setLastTurnNumber(1);
      setLastActivePlayerId(gameState.active_player_id);
      // If human goes first, set flag to clear on their first action
      if (gameState.active_player_id === humanPlayerId) {
        setShouldClearOnNextAction(true);
      }
      return;
    }

    // When active player changes, handle message clearing
    if (gameState.active_player_id !== lastActivePlayerId && lastActivePlayerId !== '') {
      if (gameState.active_player_id === humanPlayerId) {
        // Transitioning to human: set flag to clear on their first action
        setShouldClearOnNextAction(true);
        setLastActivePlayerId(gameState.active_player_id);
      } else if (aiPlayerId && gameState.active_player_id === aiPlayerId) {
        // Transitioning to AI: clear messages immediately
        setMessages([]);
        setLastActivePlayerId(gameState.active_player_id);
      } else {
        // Transitioning to other human player in multiplayer
        setLastActivePlayerId(gameState.active_player_id);
      }
    }

    // Track turn number changes
    if (gameState.turn_number !== lastTurnNumber) {
      setLastTurnNumber(gameState.turn_number);
    }
  }, [gameState, lastTurnNumber, lastActivePlayerId, humanPlayerId, aiPlayerId]);

  // Auto-trigger AI turn (only for single-player mode)
  useEffect(() => {
    if (
      aiPlayerId &&
      gameState &&
      gameState.active_player_id === aiPlayerId &&
      !gameState.is_game_over &&
      !isProcessing &&
      !aiTurnMutation.isPending
    ) {
      // Delay AI turn slightly for better UX
      const timer = setTimeout(() => {
        aiTurnMutation.mutate(aiPlayerId, {
          onSuccess: (response) => {
            // Don't add message if game just ended
            if (!response.game_state?.is_game_over) {
              setMessages(prev => [...prev, response.message]);
            }
          },
          onError: (error) => {
            console.error('AI turn error:', error);
            setMessages(prev => [...prev, `AI Error: ${error.message}`]);
          },
        });
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [gameState?.active_player_id, gameState?.turn_number, aiPlayerId, isProcessing, aiTurnMutation.isPending]);

  const handleAction = (action: ValidAction) => {
    // Check if action requires target selection or has alternative cost
    // NOTE: Tussles already have their target specified in target_options, so don't show modal
    const needsTargetSelection = 
      (action.action_type === 'play_card' || action.action_type === 'activate_ability') && 
      action.target_options && 
      action.target_options.length > 0;
    const hasAlternativeCost = action.alternative_cost_available;
    
    if (needsTargetSelection || hasAlternativeCost) {
      // Show target selection modal
      setPendingAction(action);
      return;
    }
    
    // Otherwise, execute action immediately
    executeAction(action, []);
  };

  const executeAction = (action: ValidAction, selectedTargets: string[], alternativeCostCard?: string) => {
    // Helper to add message with optional clearing
    const addMessage = (msg: string, response?: any) => {
      // Don't add action messages if the response indicates game is over
      if (response?.game_state?.is_game_over) return;
      
      if (shouldClearOnNextAction) {
        setMessages([msg]);
        setShouldClearOnNextAction(false);
      } else {
        setMessages(prev => [...prev, msg]);
      }
    };
    
    if (action.action_type === 'end_turn') {
      endTurnMutation.mutate(
        { player_id: humanPlayerId },
        {
          onSuccess: (response) => addMessage(response.message, response),
          onError: (error) => addMessage(`Error: ${error.message}`),
        }
      );
    } else if (action.action_type === 'play_card' && action.card_id) {
      playCardMutation.mutate(
        { 
          player_id: humanPlayerId, 
          card_id: action.card_id,
          target_card_id: selectedTargets.length === 1 ? selectedTargets[0] : undefined,
          target_card_ids: selectedTargets.length > 1 ? selectedTargets : undefined,
          alternative_cost_card_id: alternativeCostCard,
        },
        {
          onSuccess: (response) => {
            addMessage(response.message, response);
            setSelectedCard(null);
          },
          onError: (error) => {
            addMessage(`Error: ${error.message}`);
            setSelectedCard(null);
          },
        }
      );
    } else if (action.action_type === 'tussle' && action.card_id) {
      const defenderId = action.target_options?.[0] === 'direct_attack' 
        ? undefined 
        : action.target_options?.[0];
      
      tussleMutation.mutate(
        {
          player_id: humanPlayerId,
          attacker_id: action.card_id,
          defender_id: defenderId,
        },
        {
          onSuccess: (response) => {
            addMessage(response.message, response);
            setSelectedCard(null);
          },
          onError: (error) => {
            addMessage(`Error: ${error.message}`);
            setSelectedCard(null);
          },
        }
      );
    } else if (action.action_type === 'activate_ability' && action.card_id) {
      activateAbilityMutation.mutate(
        {
          player_id: humanPlayerId,
          card_id: action.card_id,
          target_id: selectedTargets.length === 1 ? selectedTargets[0] : undefined,
          amount: 1,
        },
        {
          onSuccess: (response) => {
            addMessage(response.message, response);
            setSelectedCard(null);
          },
          onError: (error) => {
            addMessage(`Error: ${error.message}`);
            setSelectedCard(null);
          },
        }
      );
    }
  };

  const handleTargetSelection = (selectedTargets: string[], alternativeCostCard?: string) => {
    if (!pendingAction) return;
    
    executeAction(pendingAction, selectedTargets, alternativeCostCard);
    setPendingAction(null);
  };

  const handleCancelTargetSelection = () => {
    setPendingAction(null);
  };

  if (isLoading || !gameState) {
    return (
      <div className="min-h-screen bg-game-bg flex items-center justify-center">
        <div className="text-2xl">Loading game...</div>
      </div>
    );
  }

  const humanPlayer = gameState.players[humanPlayerId];
  // In multiplayer, the "other" player is not AI, just the other player
  const otherPlayerId = aiPlayerId || Object.keys(gameState.players).find(id => id !== humanPlayerId) || '';
  const otherPlayer = gameState.players[otherPlayerId];

  if (!humanPlayer || !otherPlayer) {
    return (
      <div className="min-h-screen bg-game-bg flex items-center justify-center">
        <div className="text-2xl text-red-500">Error: Players not found</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-game-bg p-3">
      <div className="max-w-[1400px] mx-auto">
        {/* Game Header - Player Info Bars */}
        <div className="mb-3 p-3 bg-game-card rounded grid grid-cols-3 gap-4 items-center">
          {/* Human Player Info - Left */}
          <PlayerInfoBar 
            player={humanPlayer} 
            isActive={gameState.active_player_id === humanPlayerId} 
          />
          
          {/* Turn Info - Center */}
          <div className="text-center">
            <div className="text-lg font-bold">Turn {gameState.turn_number}</div>
          </div>
          
          {/* Other Player Info - Right */}
          <div className="flex justify-end">
            <PlayerInfoBar 
              player={otherPlayer} 
              isActive={gameState.active_player_id === otherPlayerId} 
            />
          </div>
        </div>

        {/* Main Game Area - 3 Columns */}
        <div className="grid gap-3" style={{ gridTemplateColumns: '1fr 280px 350px' }}>
          {/* Left Column - In Play Zones */}
          <div className="space-y-3">
            {/* Other Player In Play - Top */}
            <InPlayZone
              cards={otherPlayer.in_play}
              playerName={otherPlayer.name}
              isHuman={false}
            />
            
            {/* Divider */}
            <div className="border-t-2 border-game-highlight"></div>
            
            {/* Human In Play - Bottom */}
            <InPlayZone
              cards={humanPlayer.in_play}
              playerName={humanPlayer.name}
              isHuman={true}
              selectedCard={selectedCard || undefined}
              onCardClick={(cardId) => setSelectedCard(cardId)}
            />
          </div>

          {/* Center Column - Sleep Zones */}
          <div className="space-y-3">
            {/* Other Player Sleep Zone - Top */}
            <SleepZoneDisplay
              cards={otherPlayer.sleep_zone}
              playerName={otherPlayer.name}
            />
            
            {/* Divider */}
            <div className="border-t-2 border-game-highlight"></div>
            
            {/* Human Sleep Zone - Bottom */}
            <SleepZoneDisplay
              cards={humanPlayer.sleep_zone}
              playerName={humanPlayer.name}
            />
          </div>

          {/* Right Column - Messages + Actions */}
          <div className="space-y-3">
            {/* Messages Area - Top */}
            <div className="bg-gray-800 rounded p-3 border border-gray-700" style={{ minHeight: '200px', maxHeight: '400px', overflowY: 'auto' }}>
              <div className="text-sm text-gray-400 mb-2">Game Messages</div>
              <div className="space-y-2">
                {messages.map((msg, idx) => (
                  <div key={idx} className="p-2 bg-blue-900 rounded text-sm">
                    {msg}
                  </div>
                ))}
                {isProcessing && aiPlayerId && gameState.active_player_id === aiPlayerId && (
                  <div className="p-2 bg-purple-900 rounded text-sm animate-pulse">
                    AI is thinking...
                  </div>
                )}
              </div>
            </div>
            
            {/* Actions Panel - Bottom */}
            <ActionPanel
              validActions={validActionsData?.valid_actions || []}
              onAction={handleAction}
              isProcessing={isProcessing}
              currentCC={humanPlayer.cc}
            />
          </div>
        </div>

        {/* Human Hand - Full Width at Bottom */}
        <div className="mt-3">
          <HandZone
            cards={humanPlayer.hand || []}
            selectedCard={selectedCard || undefined}
            onCardClick={(cardId) => setSelectedCard(cardId)}
          />
        </div>
      </div>

      {/* Target Selection Modal */}
      {pendingAction && (
        <TargetSelectionModal
          action={pendingAction}
          availableTargets={getAvailableTargets(pendingAction)}
          onConfirm={handleTargetSelection}
          onCancel={handleCancelTargetSelection}
          alternativeCostOptions={
            pendingAction.alternative_cost_available
              ? [...humanPlayer.in_play, ...(humanPlayer.hand || [])]
              : undefined
          }
        />
      )}
    </div>
  );

  // Helper function to get available target cards based on target options
  function getAvailableTargets(action: ValidAction): Card[] {
    if (!action.target_options || action.target_options.length === 0) {
      return [];
    }

    // Search all zones for both players - the backend already provides
    // the valid target IDs in action.target_options, so we just need to
    // find the card objects matching those IDs.
    const allCards: Card[] = [
      ...humanPlayer.in_play,
      ...humanPlayer.sleep_zone,
      ...(humanPlayer.hand || []),
      ...otherPlayer.in_play,
      ...otherPlayer.sleep_zone,
    ];

    // Filter using card IDs (target_options contains valid target card IDs)
    return allCards.filter(card => action.target_options?.includes(card.id));
  }
}
