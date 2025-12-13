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
  const { isDesktop, isMobile, isLandscape, isTablet, width, height } = useResponsive();
  // Use small cards only for true mobile (<360px)
  // Use medium cards (with effect text) for tablet and desktop - readability is key
  const cardSize = isMobile ? 'small' : 'medium';
  
  // Debug flag - set to true to show viewport debug info
  const DEBUG_VIEWPORT = false;

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
  }, [gameState, humanPlayerId, pendingAction]);

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
    <div className="min-h-screen bg-game-bg" style={{ padding: 'var(--spacing-component-sm)' }}>
      {/* Debug viewport indicator - toggle DEBUG_VIEWPORT to show */}
      {DEBUG_VIEWPORT && (
        <div className="fixed top-0 left-0 bg-black/80 text-white text-xs px-2 py-1 z-50 font-mono">
          {width}×{height} | {isMobile ? 'MOBILE' : isTablet ? 'TABLET' : 'DESKTOP'} | {isLandscape ? 'LAND' : 'PORT'}
        </div>
      )}
      <div className="max-w-[1400px] mx-auto">
        {/* Game Header - Player Info Bars */}
        <div 
          className={`bg-game-card rounded ${isMobile ? 'flex flex-col' : 'grid grid-cols-3'} items-center`}
          style={{ 
            marginBottom: 'var(--spacing-component-sm)', 
            padding: 'var(--spacing-component-sm)', 
            gap: isMobile ? 'var(--spacing-component-xs)' : 'var(--spacing-component-md)' 
          }}
        >
          {isMobile ? (
            <>
              {/* Mobile: Turn indicator first */}
              <div className="text-center">
                <div 
                  className={`
                    text-base font-bold rounded-lg transition-all duration-300
                    ${isHumanTurn 
                      ? 'bg-green-600 text-white shadow-lg shadow-green-600/50' 
                      : 'bg-gray-700 text-gray-300'
                    }
                  `}
                  style={{ padding: '4px var(--spacing-component-sm)' }}
                >
                  {isHumanTurn ? 'Your Turn' : "Opponent's Turn"} • Turn {gameState.turn_number}
                </div>
              </div>
              {/* Mobile: Players side by side */}
              <div className="flex justify-between w-full" style={{ gap: 'var(--spacing-component-xs)' }}>
                <PlayerInfoBar
                  player={humanPlayer}
                  isActive={gameState.active_player_id === humanPlayerId}
                />
                <PlayerInfoBar
                  player={otherPlayer}
                  isActive={gameState.active_player_id === otherPlayerId}
                />
              </div>
            </>
          ) : (
            <>
              {/* Desktop/Tablet: 3 columns */}
              <PlayerInfoBar
                player={humanPlayer}
                isActive={gameState.active_player_id === humanPlayerId}
              />
              <div className="text-center">
                <div 
                  className={`
                    text-lg font-bold rounded-lg transition-all duration-300
                    ${isHumanTurn 
                      ? 'bg-green-600 text-white shadow-lg shadow-green-600/50' 
                      : 'bg-gray-700 text-gray-300'
                    }
                  `}
                  style={{ padding: '4px var(--spacing-component-md)' }}
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
            </>
          )}
        </div>

        {/* Main Game Area - Responsive Layout */}
        <LayoutGroup>
        {isDesktop ? (
          /* Desktop: Left side = game zones stacked, Right side = messages + actions */
          <div className="grid" style={{ gap: 'var(--spacing-component-sm)', gridTemplateColumns: '1fr 350px' }}>
            {/* Left Side - All Game Zones */}
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-sm)' }}>
              {/* Opponent's Zones - Side by Side */}
              <div className="grid grid-cols-2" style={{ gap: 'var(--spacing-component-sm)' }}>
                <InPlayZone
                  cards={otherPlayer.in_play}
                  playerName={otherPlayer.name}
                  isHuman={false}
                  size={cardSize}
                  enableLayoutAnimation={true}
                />
                <SleepZoneDisplay
                  cards={otherPlayer.sleep_zone}
                  playerName={otherPlayer.name}
                  enableLayoutAnimation={true}
                />
              </div>

              {/* Divider */}
              <div className="border-t-2 border-game-highlight"></div>

              {/* My Zones - Side by Side */}
              <div className="grid grid-cols-2" style={{ gap: 'var(--spacing-component-sm)' }}>
                <InPlayZone
                  cards={humanPlayer.in_play}
                  playerName={humanPlayer.name}
                  isHuman={true}
                  selectedCard={selectedCard || undefined}
                  onCardClick={handleInPlayCardClick}
                  actionableCardIds={actionableInPlayCardIds}
                  isPlayerTurn={isHumanTurn}
                  size={cardSize}
                  enableLayoutAnimation={true}
                />
                <SleepZoneDisplay
                  cards={humanPlayer.sleep_zone}
                  playerName={humanPlayer.name}
                  enableLayoutAnimation={true}
                />
              </div>

              {/* My Hand - Full Width Below My Zones */}
              <HandZone
                cards={humanPlayer.hand || []}
                selectedCard={selectedCard || undefined}
                onCardClick={handleHandCardClick}
                playableCardIds={playableCardIds}
                isPlayerTurn={isHumanTurn}
                size={cardSize}
                isCompact={false}
                enableLayoutAnimation={true}
              />
            </div>

            {/* Right Side - Messages + Actions (Full Height) */}
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-sm)' }}>
              {/* Messages Area */}
              <GameMessages
                messages={messages}
                isAIThinking={isAIThinking}
                playByPlay={gameState?.play_by_play}
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
        ) : isMobile ? (
          /* Mobile: Single-column stack for small screens */
          <div className="flex flex-col" style={{ gap: 'var(--spacing-component-xs)' }}>
            {/* Opponent's zones */}
            <div className="flex" style={{ gap: 'var(--spacing-component-xs)' }}>
              <div className="flex-1" style={{ minWidth: 0 }}>
                <InPlayZone
                  cards={otherPlayer.in_play}
                  playerName={otherPlayer.name}
                  isHuman={false}
                  size={cardSize}
                  enableLayoutAnimation={true}
                />
              </div>
              <div style={{ width: 'var(--width-sleep-zone-mobile)', flexShrink: 0 }}>
                <SleepZoneDisplay
                  cards={otherPlayer.sleep_zone}
                  playerName={otherPlayer.name}
                  isCompact={true}
                  enableLayoutAnimation={true}
                />
              </div>
            </div>
            
            <div className="border-t-2 border-game-highlight"></div>
            
            {/* Human's zones */}
            <div className="flex" style={{ gap: 'var(--spacing-component-xs)' }}>
              <div className="flex-1" style={{ minWidth: 0 }}>
                <InPlayZone
                  cards={humanPlayer.in_play}
                  playerName={humanPlayer.name}
                  isHuman={true}
                  selectedCard={selectedCard || undefined}
                  onCardClick={handleInPlayCardClick}
                  actionableCardIds={actionableInPlayCardIds}
                  isPlayerTurn={isHumanTurn}
                  size={cardSize}
                  enableLayoutAnimation={true}
                />
              </div>
              <div style={{ width: 'var(--width-sleep-zone-mobile)', flexShrink: 0 }}>
                <SleepZoneDisplay
                  cards={humanPlayer.sleep_zone}
                  playerName={humanPlayer.name}
                  isCompact={true}
                  enableLayoutAnimation={true}
                />
              </div>
            </div>
            
            {/* Human Hand */}
            <HandZone
              cards={humanPlayer.hand || []}
              selectedCard={selectedCard || undefined}
              onCardClick={handleHandCardClick}
              playableCardIds={playableCardIds}
              isPlayerTurn={isHumanTurn}
              size={cardSize}
              isCompact={true}
              enableLayoutAnimation={true}
            />
            
            {/* Messages */}
            <GameMessages
              messages={messages}
              isAIThinking={isAIThinking}
              isCompact={true}
              playByPlay={gameState?.play_by_play}
            />
            
            {/* Actions Panel */}
            <ActionPanel
              validActions={validActionsData?.valid_actions || []}
              onAction={handleAction}
              isProcessing={isProcessing}
              currentCC={humanPlayer.cc}
              isCompact={true}
            />
          </div>
        ) : (
          /* Tablet: 2-column layout */
          <>
          <div className="grid" style={{ gap: 'var(--spacing-component-xs)', gridTemplateColumns: '1fr var(--width-sidebar-tablet)' }}>
            {/* Left Column - Game Zones (In Play + Sleep stacked) */}
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-xs)' }}>
              {/* Opponent's zones */}
              <div className="flex" style={{ gap: 'var(--spacing-component-xs)' }}>
                <div className="flex-1">
                  <InPlayZone
                    cards={otherPlayer.in_play}
                    playerName={otherPlayer.name}
                    isHuman={false}
                    size={cardSize}
                    enableLayoutAnimation={true}
                  />
                </div>
                <div style={{ width: '200px' }}>
                  <SleepZoneDisplay
                    cards={otherPlayer.sleep_zone}
                    playerName={otherPlayer.name}
                    isCompact={true}
                    enableLayoutAnimation={true}
                  />
                </div>
              </div>
              
              <div className="border-t-2 border-game-highlight"></div>
              
              {/* Human's zones */}
              <div className="flex" style={{ gap: 'var(--spacing-component-xs)' }}>
                <div className="flex-1">
                  <InPlayZone
                    cards={humanPlayer.in_play}
                    playerName={humanPlayer.name}
                    isHuman={true}
                    selectedCard={selectedCard || undefined}
                    onCardClick={handleInPlayCardClick}
                    actionableCardIds={actionableInPlayCardIds}
                    isPlayerTurn={isHumanTurn}
                    size={cardSize}
                    enableLayoutAnimation={true}
                  />
                </div>
                <div style={{ width: '200px' }}>
                  <SleepZoneDisplay
                    cards={humanPlayer.sleep_zone}
                    playerName={humanPlayer.name}
                    isCompact={true}
                    enableLayoutAnimation={true}
                  />
                </div>
              </div>
            </div>

            {/* Right Column - Messages + Actions */}
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-xs)' }}>
              {/* Messages Area - Compact & Collapsible */}
              <GameMessages
                messages={messages}
                isAIThinking={isAIThinking}
                isCompact={true}
                playByPlay={gameState?.play_by_play}
              />

              {/* Actions Panel */}
              <ActionPanel
                validActions={validActionsData?.valid_actions || []}
                onAction={handleAction}
                isProcessing={isProcessing}
                currentCC={humanPlayer.cc}
                isCompact={true}
              />
            </div>
          </div>

          {/* Human Hand - Full Width at Bottom (Tablet/Mobile only) */}
          <div style={{ marginTop: 'var(--spacing-component-xs)' }}>
            <HandZone
              cards={humanPlayer.hand || []}
              selectedCard={selectedCard || undefined}
              onCardClick={handleHandCardClick}
              playableCardIds={playableCardIds}
              isPlayerTurn={isHumanTurn}
              size={cardSize}
              isCompact={isTablet && isLandscape}
              enableLayoutAnimation={true}
            />
          </div>
          </>
        )}
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
