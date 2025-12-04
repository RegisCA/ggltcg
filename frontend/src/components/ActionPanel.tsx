/**
 * ActionPanel Component
 * Displays available actions and handles player inputs
 * Supports keyboard shortcuts: 1-9 for actions, 0 for end turn
 */

import { useState, useEffect, useCallback } from 'react';
import type { ValidAction } from '../types/game';

interface ActionPanelProps {
  validActions: ValidAction[];
  onAction: (action: ValidAction) => void;
  isProcessing: boolean;
  currentCC: number;
  compact?: boolean;  // Smaller buttons for tablet
}

export function ActionPanel({
  validActions,
  onAction,
  isProcessing,
  currentCC,
  compact = false,
}: ActionPanelProps) {
  const [shouldBlink, setShouldBlink] = useState(false);
  const [lastActionTime, setLastActionTime] = useState(Date.now());

  // Build flat list of actions for keyboard shortcuts
  // End turn is always index 0 (key '0'), other actions are 1-9
  const flatActions = validActions.reduce((acc, action) => {
    if (action.action_type === 'end_turn') {
      // End turn goes to position 0
      acc.unshift(action);
    } else {
      acc.push(action);
    }
    return acc;
  }, [] as ValidAction[]);

  // Keyboard shortcut handler
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    // Ignore if processing, or if user is typing in an input
    if (isProcessing) return;
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
    
    const key = event.key;
    
    // 0 = end turn (first item), 1-9 = actions
    if (key >= '0' && key <= '9') {
      const index = parseInt(key, 10);
      
      if (index === 0) {
        // End turn
        const endTurnAction = flatActions.find(a => a.action_type === 'end_turn');
        if (endTurnAction) {
          event.preventDefault();
          onAction(endTurnAction);
        }
      } else {
        // Other actions (1-indexed, but skip end_turn which is at index 0)
        const nonEndTurnActions = flatActions.filter(a => a.action_type !== 'end_turn');
        const action = nonEndTurnActions[index - 1];
        if (action) {
          event.preventDefault();
          onAction(action);
        }
      }
    }
  }, [flatActions, isProcessing, onAction]);

  // Add keyboard listener
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Reset the inactivity timer whenever validActions changes (indicates an action was taken)
  useEffect(() => {
    setLastActionTime(Date.now());
    setShouldBlink(false);
  }, [validActions]);

  // Set up inactivity reminders for "End Turn" button
  useEffect(() => {
    const intervals = [
      { delay: 10000, duration: 2000 },   // 10s: blink for 2s
      { delay: 20000, duration: 2000 },   // 20s: blink for 2s
      { delay: 60000, duration: 2000 },   // 1min: blink for 2s
      { delay: 300000, duration: 0 },     // 5min: stop
    ];

    const timers: ReturnType<typeof setTimeout>[] = [];

    intervals.forEach(({ delay, duration }) => {
      const timer = setTimeout(() => {
        if (duration > 0) {
          setShouldBlink(true);
          setTimeout(() => setShouldBlink(false), duration);
        } else {
          // Stop all blinking after 5 minutes
          setShouldBlink(false);
        }
      }, delay);
      timers.push(timer);
    });

    return () => {
      timers.forEach(timer => clearTimeout(timer));
    };
  }, [lastActionTime]);

  // Build shortcut map: action ID -> shortcut key
  // End turn = 0, other actions = 1-9
  const getShortcutKey = (action: ValidAction): string | null => {
    if (action.action_type === 'end_turn') return '0';
    const nonEndTurnActions = validActions.filter(a => a.action_type !== 'end_turn');
    const index = nonEndTurnActions.indexOf(action);
    if (index >= 0 && index < 9) return String(index + 1);
    return null;
  };

  const getActionColor = (type: string) => {
    switch (type) {
      case 'play_card':
        return 'bg-blue-600 hover:bg-blue-700';
      case 'tussle':
        return 'bg-red-600 hover:bg-red-700';
      case 'activate_ability':
        return 'bg-purple-600 hover:bg-purple-700';
      case 'end_turn':
        return 'bg-amber-600 hover:bg-amber-700';
      default:
        return 'bg-gray-600 hover:bg-gray-700';
    }
  };

  // Separate card actions from turn control
  const cardActions = validActions.filter(a => a.action_type !== 'end_turn');
  const endTurnAction = validActions.find(a => a.action_type === 'end_turn');

return (
  <div className={`bg-game-card rounded border-2 border-game-accent w-full ${compact ? 'p-2' : 'p-3'}`}>
    <div className={compact ? 'mb-2' : 'mb-3'}>
      <h3 className={`font-bold ${compact ? 'text-sm mb-0.5' : 'text-lg mb-1'}`}>
        Available Actions
        {validActions.length > 0 && (
          <span> for {currentCC} CC</span>
        )}
      </h3>
    </div>

    {validActions.length === 0 ? (
      <div className={`text-gray-500 italic text-center ${compact ? 'py-2 text-xs' : 'py-4'}`}>
        No actions available
      </div>
    ) : (
      <div className="space-y-3">
        {/* Card Actions Group */}
        {cardActions.length > 0 && (
          <div className={`grid grid-cols-1 w-full ${compact ? 'gap-1.5' : 'gap-2'}`}>
            {cardActions.map((action, index) => {
              const cleanDescription = action.description.replace(/\s*\(Cost:.*?\)/, '');
              const shortcutKey = getShortcutKey(action);
              const isUnaffordable = action.cost_cc !== undefined && action.cost_cc > currentCC;

              return (
                <button
                  key={`${action.action_type}-${action.card_id || 'action'}-${index}`}
                  onClick={() => onAction(action)}
                  disabled={isProcessing || isUnaffordable}
                  className={`
                    w-full block rounded transition-all border-2 text-white
                    ${compact ? 'px-2 py-1.5 text-xs' : 'px-4 py-3 text-sm'}
                    ${getActionColor(action.action_type)}
                    ${isProcessing || isUnaffordable ? 'opacity-40 cursor-not-allowed' : 'hover:scale-[1.02] active:scale-95'}
                    border-transparent
                    focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:ring-offset-2 focus:ring-offset-game-card
                  `}
                >
                  <div className={`flex justify-between items-center w-full ${compact ? 'gap-2' : 'gap-2'}`}>
                    {/* Keyboard shortcut indicator */}
                    {shortcutKey && (
                      <span className={`flex items-center justify-center bg-black/30 rounded font-mono font-bold flex-shrink-0 text-white ${compact ? 'w-5 h-5 text-[10px] mr-1' : 'w-6 h-6 text-xs'}`}>
                        {shortcutKey}
                      </span>
                    )}
                    <span className="font-bold text-left flex-1 text-white">
                      {cleanDescription}
                    </span>
                    
                    {action.cost_cc !== undefined && (
                      <span className={`
                        rounded font-bold whitespace-nowrap
                        ${compact ? 'px-2 py-1 text-[10px]' : 'px-3 py-1.5 text-xs'}
                        ${isUnaffordable ? 'bg-red-800 text-white' : 'bg-black/40 text-white'}
                      `}>
                        {isUnaffordable && '🔒 '}
                        {action.cost_cc} CC
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* Separator between card actions and turn control */}
        {cardActions.length > 0 && endTurnAction && (
          <div className="border-t border-game-accent my-4" />
        )}

        {/* Turn Control */}
        {endTurnAction && (
          <button
            onClick={() => onAction(endTurnAction)}
            disabled={isProcessing}
            className={`
              w-full block rounded transition-all border-2 text-white
              ${compact ? 'px-2 py-1.5 text-xs' : 'px-4 py-3 text-sm'}
              ${getActionColor('end_turn')}
              ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:scale-[1.02] active:scale-95'}
              ${shouldBlink ? 'animate-blink ring-4 ring-yellow-400' : 'border-transparent'}
              focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:ring-offset-2 focus:ring-offset-game-card
            `}
          >
            <div className={`flex justify-between items-center w-full ${compact ? 'gap-2' : 'gap-2'}`}>
              <span className={`flex items-center justify-center bg-black/30 rounded font-mono font-bold flex-shrink-0 text-white ${compact ? 'w-5 h-5 text-[10px] mr-1' : 'w-6 h-6 text-xs'}`}>
                0
              </span>
              <span className="font-bold text-left flex-1 text-white">
                {endTurnAction.description.replace(/\s*\(Cost:.*?\)/, '')}
              </span>
            </div>
          </button>
        )}
      </div>
    )}
  </div>
);
}
