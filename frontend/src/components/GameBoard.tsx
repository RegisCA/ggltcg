/**
 * GameBoard Component
 * 
 * Main game interface that orchestrates all game components.
 * Refactored to use custom hooks for better separation of concerns.
 */

import { useState, useEffect, useCallback } from 'react';
import type { ValidAction, GameState, Card } from '../types/game';
import { useGameState, useValidActions } from '../hooks/useGame';
import { useGameMessages } from '../hooks/useGameMessages';
import { useGameFlow } from '../hooks/useGameFlow';
import { useGameActions } from '../hooks/useGameActions';
import { PlayerInfoBar } from './PlayerInfoBar';
import { InPlayZone } from './InPlayZone';
import { HandZone } from './HandZone';
import { SleepZoneDisplay } from './SleepZoneDisplay';
import { ActionPanel } from './ActionPanel';
import { TargetSelectionModal } from './TargetSelectionModal';

interface GameBoardProps {
  gameId: string;
  humanPlayerId: string;
  aiPlayerId?: string;
  onGameEnd: (winner: string, gameState: GameState) => void;
}

export function GameBoard({ gameId, humanPlayerId, aiPlayerId, onGameEnd }: GameBoardProps) {
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<ValidAction | null>(null);

  // Fetch game state with polling
  const { data: gameState, isLoading, error } = useGameState(gameId, humanPlayerId, {
    refetchInterval: 2000,
  });

  // Game messages management
  const { messages, addMessage } = useGameMessages(gameState, {
    humanPlayerId,
    aiPlayerId,
  });

  // Game actions with message callbacks
  const { executeAction, isProcessing: isActionsProcessing } = useGameActions({
    gameId,
    humanPlayerId,
    onMessage: (msg, response) => addMessage(msg, { skipIfGameOver: true, response }),
    onActionComplete: () => setSelectedCard(null),
  });

  // Game flow (AI turns, winner detection, error handling)
  const { isAIThinking } = useGameFlow(gameState, error, {
    gameId,
    humanPlayerId,
    aiPlayerId,
    onGameEnd,
    onAIMessage: (msg) => addMessage(msg, { skipIfGameOver: true }),
    onAIError: (err) => addMessage(`AI Error: ${err.message}`),
    isProcessing: isActionsProcessing,
  });

  const isProcessing = isActionsProcessing || isAIThinking;

  // Fetch valid actions
  const { data: validActionsData } = useValidActions(gameId, humanPlayerId, {
    enabled: gameState?.active_player_id === humanPlayerId,
  });

  // Compute playable card IDs from valid actions
  const playableCardIds = (validActionsData?.valid_actions || [])
    .filter(a => a.action_type === 'play_card' && a.card_id)
    .map(a => a.card_id!);

  const isHumanTurn = gameState?.active_player_id === humanPlayerId;

  // Clear pendingAction (modal) when turn ends or active player changes
  useEffect(() => {
    if (!gameState) return;
    if (gameState.active_player_id !== humanPlayerId && pendingAction) {
      setPendingAction(null);
    }
  }, [gameState?.active_player_id, gameState?.turn_number, humanPlayerId, pendingAction]);

  // Handle action - check if needs target selection modal
  const handleAction = useCallback((action: ValidAction) => {
    const needsTargetSelection =
      (action.action_type === 'play_card' || action.action_type === 'activate_ability') &&
      action.target_options &&
      action.target_options.length > 0;
    const hasAlternativeCost = action.alternative_cost_available;

    if (needsTargetSelection || hasAlternativeCost) {
      setPendingAction(action);
      return;
    }

    executeAction(action, []);
  }, [executeAction]);

  // Handle target selection from modal
  const handleTargetSelection = useCallback((
    selectedTargets: string[],
    alternativeCostCard?: string
  ) => {
    if (!pendingAction) return;
    executeAction(pendingAction, selectedTargets, alternativeCostCard);
    setPendingAction(null);
  }, [pendingAction, executeAction]);

  const handleCancelTargetSelection = useCallback(() => {
    setPendingAction(null);
  }, []);

  // Loading state
  if (isLoading || !gameState) {
    return (
      <div className="min-h-screen bg-game-bg flex items-center justify-center">
        <div className="text-2xl">Loading game...</div>
      </div>
    );
  }

  const humanPlayer = gameState.players[humanPlayerId];
  const otherPlayerId = aiPlayerId || Object.keys(gameState.players).find(id => id !== humanPlayerId) || '';
  const otherPlayer = gameState.players[otherPlayerId];

  if (!humanPlayer || !otherPlayer) {
    return (
      <div className="min-h-screen bg-game-bg flex items-center justify-center">
        <div className="text-2xl text-red-500">Error: Players not found</div>
      </div>
    );
  }

  // Helper function to get available target cards
  const getAvailableTargets = (action: ValidAction): Card[] => {
    if (!action.target_options || action.target_options.length === 0) {
      return [];
    }

    const allCards: Card[] = [
      ...humanPlayer.in_play,
      ...humanPlayer.sleep_zone,
      ...(humanPlayer.hand || []),
      ...otherPlayer.in_play,
      ...otherPlayer.sleep_zone,
    ];

    return allCards.filter(card => action.target_options?.includes(card.id));
  };

  return (
    <div className="min-h-screen bg-game-bg p-3">
      <div className="max-w-[1400px] mx-auto">
        {/* Game Header - Player Info Bars */}
        <div className="mb-3 p-3 bg-game-card rounded grid grid-cols-3 gap-4 items-center">
          <PlayerInfoBar
            player={humanPlayer}
            isActive={gameState.active_player_id === humanPlayerId}
          />
          <div className="text-center">
            <div className="text-lg font-bold">Turn {gameState.turn_number}</div>
          </div>
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
            <InPlayZone
              cards={otherPlayer.in_play}
              playerName={otherPlayer.name}
              isHuman={false}
            />
            <div className="border-t-2 border-game-highlight"></div>
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
            <SleepZoneDisplay
              cards={otherPlayer.sleep_zone}
              playerName={otherPlayer.name}
            />
            <div className="border-t-2 border-game-highlight"></div>
            <SleepZoneDisplay
              cards={humanPlayer.sleep_zone}
              playerName={humanPlayer.name}
            />
          </div>

          {/* Right Column - Messages + Actions */}
          <div className="space-y-3">
            {/* Messages Area */}
            <div
              className="bg-gray-800 rounded p-3 border border-gray-700"
              style={{ minHeight: '200px', maxHeight: '400px', overflowY: 'auto' }}
            >
              <div className="text-sm text-gray-400 mb-2">Game Messages</div>
              <div className="space-y-2">
                {messages.map((msg, idx) => (
                  <div key={idx} className="p-2 bg-blue-900 rounded text-sm">
                    {msg}
                  </div>
                ))}
                {isAIThinking && (
                  <div className="p-2 bg-purple-900 rounded text-sm inline-flex items-center gap-2">
                    <svg className="animate-spin h-3 w-3 text-purple-300 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Opponent is thinking...</span>
                  </div>
                )}
              </div>
            </div>

            {/* Actions Panel */}
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
            playableCardIds={playableCardIds}
            isPlayerTurn={isHumanTurn}
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
}
