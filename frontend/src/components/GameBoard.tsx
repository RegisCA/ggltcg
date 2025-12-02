/**
 * GameBoard Component
 * 
 * Main game interface that orchestrates all game components.
 * Refactored to use custom hooks for better separation of concerns.
 * 
 * Uses Framer Motion LayoutGroup for smooth card zone transitions.
 */

import { useState, useEffect, useCallback } from 'react';
import { LayoutGroup } from 'framer-motion';
import type { ValidAction, GameState, Card } from '../types/game';
import { useGameState, useValidActions } from '../hooks/useGame';
import { useGameMessages } from '../hooks/useGameMessages';
import { useGameFlow } from '../hooks/useGameFlow';
import { useGameActions } from '../hooks/useGameActions';
import { useResponsive } from '../hooks/useResponsive';
import { PlayerInfoBar } from './PlayerInfoBar';
import { InPlayZone } from './InPlayZone';
import { HandZone } from './HandZone';
import { SleepZoneDisplay } from './SleepZoneDisplay';
import { ActionPanel } from './ActionPanel';
import { TargetSelectionModal } from './TargetSelectionModal';
import { GameMessages } from './GameMessages';

interface GameBoardProps {
  gameId: string;
  humanPlayerId: string;
  aiPlayerId?: string;
  onGameEnd: (winner: string, gameState: GameState) => void;
}

export function GameBoard({ gameId, humanPlayerId, aiPlayerId, onGameEnd }: GameBoardProps) {
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<ValidAction | null>(null);
  
  // Responsive layout detection
  const { isDesktop, isMobile, isLandscape, isTablet } = useResponsive();
  // Use small cards for mobile OR tablet in landscape (limited vertical space)
  // Use medium cards for desktop and tablet in portrait
  const isLandscapeTablet = isTablet && isLandscape;
  const cardSize = (isMobile || isLandscapeTablet) ? 'small' : 'medium';

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

  // Compute cards that can initiate tussle (attacker cards)
  const tussleableCardIds = (validActionsData?.valid_actions || [])
    .filter(a => a.action_type === 'tussle' && a.card_id)
    .map(a => a.card_id!)
    .filter((id, index, arr) => arr.indexOf(id) === index); // unique

  // Compute cards with activated abilities
  const activatableCardIds = (validActionsData?.valid_actions || [])
    .filter(a => a.action_type === 'activate_ability' && a.card_id)
    .map(a => a.card_id!);

  // Cards in play that have any action available (tussle OR activate)
  const actionableInPlayCardIds = [...new Set([...tussleableCardIds, ...activatableCardIds])];

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

  // Handle direct card click from Hand zone - find and execute play_card action
  const handleHandCardClick = useCallback((cardId: string) => {
    setSelectedCard(cardId);
    
    // Find the play_card action for this card
    const playAction = (validActionsData?.valid_actions || []).find(
      a => a.action_type === 'play_card' && a.card_id === cardId
    );
    
    if (playAction) {
      // Trigger the action (will open modal if targets needed, otherwise execute)
      handleAction(playAction);
    }
  }, [validActionsData?.valid_actions, handleAction]);

  // Handle direct card click from InPlay zone - find tussle or activated ability action
  const handleInPlayCardClick = useCallback((cardId: string) => {
    setSelectedCard(cardId);
    
    const validActions = validActionsData?.valid_actions || [];
    
    // Check for activated ability first (like Archer)
    const abilityAction = validActions.find(
      a => a.action_type === 'activate_ability' && a.card_id === cardId
    );
    
    if (abilityAction) {
      handleAction(abilityAction);
      return;
    }
    
    // Check for tussle actions from this card
    const tussleActions = validActions.filter(
      a => a.action_type === 'tussle' && a.card_id === cardId
    );
    
    if (tussleActions.length === 1 && tussleActions[0].target_options?.length === 1) {
      // Single target - execute directly (like direct attack or only one defender)
      executeAction(tussleActions[0], tussleActions[0].target_options);
    } else if (tussleActions.length > 0) {
      // Multiple tussle targets - create a synthetic action for target selection modal
      // Collect all unique target options from all tussle actions for this card
      const allTargetIds = [...new Set(
        tussleActions.flatMap(a => a.target_options || [])
      )];
      
      const syntheticTussleAction: ValidAction = {
        action_type: 'tussle',
        card_id: cardId,
        card_name: tussleActions[0].card_name,
        target_options: allTargetIds,
        min_targets: 1,
        max_targets: 1,
        description: `Select target for ${tussleActions[0].card_name} to tussle`,
      };
      
      setPendingAction(syntheticTussleAction);
    }
  }, [validActionsData?.valid_actions, handleAction, executeAction]);

  // Handle target selection from modal
  const handleTargetSelection = useCallback((
    selectedTargets: string[],
    alternativeCostCard?: string
  ) => {
    if (!pendingAction) return;
    
    // For tussle actions, we need to find the actual action with this target
    // because the backend expects the specific tussle action, not a synthetic one
    if (pendingAction.action_type === 'tussle' && selectedTargets.length === 1) {
      const targetId = selectedTargets[0];
      const actualTussleAction = (validActionsData?.valid_actions || []).find(
        a => a.action_type === 'tussle' && 
             a.card_id === pendingAction.card_id && 
             a.target_options?.includes(targetId)
      );
      
      if (actualTussleAction) {
        executeAction(actualTussleAction, selectedTargets, alternativeCostCard);
        setPendingAction(null);
        return;
      }
    }
    
    executeAction(pendingAction, selectedTargets, alternativeCostCard);
    setPendingAction(null);
  }, [pendingAction, executeAction, validActionsData?.valid_actions]);

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
            <div 
              className={`
                text-lg font-bold px-4 py-1 rounded-lg transition-all duration-300
                ${isHumanTurn 
                  ? 'bg-green-600 text-white shadow-lg shadow-green-600/50' 
                  : 'bg-gray-700 text-gray-300'
                }
              `}
            >
              {isHumanTurn ? 'Your Turn' : "Opponent's Turn"} • Turn {gameState.turn_number}
            </div>
          </div>
          <div className="flex justify-end">
            <PlayerInfoBar
              player={otherPlayer}
              isActive={gameState.active_player_id === otherPlayerId}
            />
          </div>
        </div>

        {/* Main Game Area - Responsive Layout */}
        <LayoutGroup>
        {isDesktop ? (
          /* Desktop: 3-column layout */
          <div className="grid gap-3" style={{ gridTemplateColumns: '1fr 280px 350px' }}>
            {/* Left Column - In Play Zones */}
            <div className="space-y-3">
              <InPlayZone
                cards={otherPlayer.in_play}
                playerName={otherPlayer.name}
                isHuman={false}
                cardSize={cardSize}
                enableLayoutAnimation={true}
              />
              <div className="border-t-2 border-game-highlight"></div>
              <InPlayZone
                cards={humanPlayer.in_play}
                playerName={humanPlayer.name}
                isHuman={true}
                selectedCard={selectedCard || undefined}
                onCardClick={handleInPlayCardClick}
                actionableCardIds={actionableInPlayCardIds}
                isPlayerTurn={isHumanTurn}
                cardSize={cardSize}
                enableLayoutAnimation={true}
              />
            </div>

            {/* Center Column - Sleep Zones */}
            <div className="space-y-3">
              <SleepZoneDisplay
                cards={otherPlayer.sleep_zone}
                playerName={otherPlayer.name}
                enableLayoutAnimation={true}
              />
              <div className="border-t-2 border-game-highlight"></div>
              <SleepZoneDisplay
                cards={humanPlayer.sleep_zone}
                playerName={humanPlayer.name}
                enableLayoutAnimation={true}
              />
            </div>

            {/* Right Column - Messages + Actions */}
            <div className="space-y-3">
              {/* Messages Area - Collapsible */}
              <GameMessages
                messages={messages}
                isAIThinking={isAIThinking}
              />

              {/* Actions Panel */}
              <ActionPanel
                validActions={validActionsData?.valid_actions || []}
                onAction={handleAction}
                isProcessing={isProcessing}
                currentCC={humanPlayer.cc}
              />
            </div>
          </div>
        ) : (
          /* Tablet/Mobile: 2-column layout */
          <div className="grid gap-2" style={{ gridTemplateColumns: '1fr 280px' }}>
            {/* Left Column - Game Zones (In Play + Sleep stacked) */}
            <div className="space-y-2">
              {/* Opponent's zones */}
              <div className="flex gap-2">
                <div className="flex-1">
                  <InPlayZone
                    cards={otherPlayer.in_play}
                    playerName={otherPlayer.name}
                    isHuman={false}
                    cardSize={cardSize}
                    enableLayoutAnimation={true}
                  />
                </div>
                <div style={{ width: '200px' }}>
                  <SleepZoneDisplay
                    cards={otherPlayer.sleep_zone}
                    playerName={otherPlayer.name}
                    compact={true}
                    enableLayoutAnimation={true}
                  />
                </div>
              </div>
              
              <div className="border-t-2 border-game-highlight"></div>
              
              {/* Human's zones */}
              <div className="flex gap-2">
                <div className="flex-1">
                  <InPlayZone
                    cards={humanPlayer.in_play}
                    playerName={humanPlayer.name}
                    isHuman={true}
                    selectedCard={selectedCard || undefined}
                    onCardClick={handleInPlayCardClick}
                    actionableCardIds={actionableInPlayCardIds}
                    isPlayerTurn={isHumanTurn}
                    cardSize={cardSize}
                    enableLayoutAnimation={true}
                  />
                </div>
                <div style={{ width: '200px' }}>
                  <SleepZoneDisplay
                    cards={humanPlayer.sleep_zone}
                    playerName={humanPlayer.name}
                    compact={true}
                    enableLayoutAnimation={true}
                  />
                </div>
              </div>
            </div>

            {/* Right Column - Messages + Actions */}
            <div className="space-y-2">
              {/* Messages Area - Compact & Collapsible */}
              <GameMessages
                messages={messages}
                isAIThinking={isAIThinking}
                compact={true}
              />

              {/* Actions Panel */}
              <ActionPanel
                validActions={validActionsData?.valid_actions || []}
                onAction={handleAction}
                isProcessing={isProcessing}
                currentCC={humanPlayer.cc}
                compact={true}
              />
            </div>
          </div>
        )}

        {/* Human Hand - Full Width at Bottom */}
        <div className={isDesktop ? "mt-3" : "mt-2"}>
          <HandZone
            cards={humanPlayer.hand || []}
            selectedCard={selectedCard || undefined}
            onCardClick={handleHandCardClick}
            playableCardIds={playableCardIds}
            isPlayerTurn={isHumanTurn}
            cardSize={cardSize}
            compact={isLandscapeTablet}
            enableLayoutAnimation={true}
          />
        </div>
        </LayoutGroup>
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
