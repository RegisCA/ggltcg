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
import { BreakZoneDisplay } from './BreakZoneDisplay';
import { ActionBar } from './ActionBar';
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
  const { isDesktop, isMobile, isPhone, isLandscape, isTablet, width, height } = useResponsive();
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

  // Which side each playable hand card can currently target, derived from
  // the backend's target_options (no card knowledge lives in the frontend).
  // Surfaces self-targetable effects before the target modal opens —
  // observed play: Régis forgot Stomp could hit his own board (WP-2 #5).
  const handTargetHints: Record<string, 'yours' | 'theirs' | 'either'> = {};
  {
    const ownIds = new Set(
      [...humanPlayer.in_play, ...humanPlayer.break_zone, ...(humanPlayer.hand || [])].map((c) => c.id)
    );
    for (const action of validActionsData?.valid_actions || []) {
      if (action.action_type !== 'play_card' || !action.card_id) continue;
      const targets = (action.target_options || []).filter((id) => id !== 'direct_attack');
      if (targets.length === 0) continue;
      const hitsYours = targets.some((id) => ownIds.has(id));
      const hitsTheirs = targets.some((id) => !ownIds.has(id));
      handTargetHints[action.card_id] = hitsYours && hitsTheirs ? 'either' : hitsYours ? 'yours' : 'theirs';
    }
  }

  // Helper function to get available target cards
  const getAvailableTargets = (action: ValidAction): Card[] => {
    if (!action.target_options || action.target_options.length === 0) {
      return [];
    }

    const allCards: Card[] = [
      ...humanPlayer.in_play,
      ...humanPlayer.break_zone,
      ...(humanPlayer.hand || []),
      ...otherPlayer.in_play,
      ...otherPlayer.break_zone,
    ];

    return allCards.filter(card => action.target_options?.includes(card.id));
  };

  return (
    <div className="min-h-screen bg-game-bg">
      {/* Debug viewport indicator - toggle DEBUG_VIEWPORT to show */}
      {DEBUG_VIEWPORT && (
        <div className="fixed top-0 left-0 bg-black/80 text-white text-xs px-2 py-1 z-50 font-mono">
          {width}×{height} | {isMobile ? 'MOBILE' : isTablet ? 'TABLET' : 'DESKTOP'} | {isLandscape ? 'LAND' : 'PORT'}
        </div>
      )}
        {/* Game Header - Player Info Bars */}
        <div
          className={`sticky top-0 z-10 bg-game-bg border-b border-gray-700 ${isPhone ? 'flex flex-col' : 'grid grid-cols-3'} items-center`}
          style={{
            padding: 'var(--spacing-component-sm)',
            gap: isPhone ? 'var(--spacing-component-xs)' : 'var(--spacing-component-md)'
          }}
        >
          {isPhone ? (
            <>
              {/* Phone: Turn indicator first, players stacked below —
                  the 3-column header overlaps into unreadable text under 768px */}
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
              {/* Phone: Players side by side, compact so both fit.
                  Own charge lives in the ActionBar at the hand (WP-2 #2). */}
              <div className="flex justify-between w-full" style={{ gap: 'var(--spacing-component-xs)' }}>
                <PlayerInfoBar
                  player={humanPlayer}
                  isActive={gameState.active_player_id === humanPlayerId}
                  isCompact={true}
                  showCharge={false}
                />
                <PlayerInfoBar
                  player={otherPlayer}
                  isActive={gameState.active_player_id === otherPlayerId}
                  isCompact={true}
                />
              </div>
            </>
          ) : (
            <>
              {/* Desktop/Tablet: 3 columns (compact info bars on tablet).
                  Own charge lives in the ActionBar at the hand (WP-2 #2). */}
              <PlayerInfoBar
                player={humanPlayer}
                isActive={gameState.active_player_id === humanPlayerId}
                isCompact={!isDesktop}
                showCharge={false}
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
                  isCompact={!isDesktop}
                />
              </div>
            </>
          )}
        </div>

        {/* Main Game Area — one JSX tree; arrangement lives in the
            .game-board-grid template areas (index.css). The log ticker sits
            above the zones: it's the first checkpoint of the observed
            post-opponent-turn reading path (WP-2 #4), then the paired boards
            (opponent | you), hand, and action bar follow it in order. */}
        <div className="max-w-[1400px] mx-auto" style={{ marginTop: 'var(--spacing-component-sm)', padding: 'var(--spacing-component-sm)' }}>
        <div style={{ marginBottom: isDesktop ? 'var(--spacing-component-sm)' : 'var(--spacing-component-xs)' }}>
          <GameMessages
            messages={messages}
            isAIThinking={isAIThinking}
            isOpponentTurn={!isHumanTurn && !gameState.is_game_over}
            isCompact={isPhone}
            playByPlay={gameState?.play_by_play}
            humanPlayerName={humanPlayer.name}
          />
        </div>
        <LayoutGroup>
        <div className="game-board-grid">
          <div style={{ gridArea: 'opp-inplay' }}>
            <InPlayZone
              cards={otherPlayer.in_play}
              playerName={otherPlayer.name}
              isHuman={false}
              size={cardSize}
              enableLayoutAnimation={true}
            />
          </div>

          <div style={{ gridArea: 'opp-break' }}>
            <BreakZoneDisplay
              cards={otherPlayer.break_zone}
              playerName={otherPlayer.name}
              isCompact={isPhone}
              enableLayoutAnimation={true}
            />
          </div>

          <div style={{ gridArea: 'my-inplay' }}>
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

          <div style={{ gridArea: 'my-break' }}>
            <BreakZoneDisplay
              cards={humanPlayer.break_zone}
              playerName={humanPlayer.name}
              isCompact={isPhone}
              enableLayoutAnimation={true}
            />
          </div>

          <div style={{ gridArea: 'hand' }}>
            <HandZone
              cards={humanPlayer.hand || []}
              selectedCard={selectedCard || undefined}
              onCardClick={handleHandCardClick}
              playableCardIds={playableCardIds}
              targetHints={handTargetHints}
              isPlayerTurn={isHumanTurn}
              size={cardSize}
              isCompact={!isDesktop && isLandscape}
              enableLayoutAnimation={true}
            />
          </div>

          {/* Charge + End Turn, docked at the hand where play decisions
              happen. Replaces the ActionPanel sidebar list (WP-1 #1,
              WP-2 #1-2): cards themselves are the play surface.
              Sticky: this is the only place the player's own Charge is
              shown, so it must never scroll out of view — in a real game
              the board grows taller than the viewport. */}
          <div
            style={{
              gridArea: 'actionbar',
              position: 'sticky',
              bottom: 0,
              zIndex: 20,
              boxShadow: '0 -8px 16px -4px rgba(26, 26, 46, 0.9)',
            }}
          >
            <ActionBar
              charge={humanPlayer.charge}
              validActions={validActionsData?.valid_actions || []}
              onAction={handleAction}
              isProcessing={isProcessing}
              isCompact={!isDesktop}
            />
          </div>

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
          currentCharge={humanPlayer.charge}
          humanPlayerId={humanPlayerId}
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
