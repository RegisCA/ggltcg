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
}

export function ActionPanel({
  validActions,
  onAction,
  isProcessing,
  currentCC,
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

  const groupedActions = validActions.reduce((acc, action) => {
    if (!acc[action.action_type]) {
      acc[action.action_type] = [];
    }
    acc[action.action_type].push(action);
    return acc;
  }, {} as Record<string, ValidAction[]>);

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
      case 'end_turn':
        return 'bg-green-600 hover:bg-green-700';
      default:
        return 'bg-gray-600 hover:bg-gray-700';
    }
  };

return (
  <div className="p-3 bg-game-card rounded border-2 border-game-accent w-full">
    <div className="mb-3">
      {/* CHANGE: Conditionally build the header text. 
        Only include the current CC if there are actions to display.
      */}
      <h3 className="text-lg font-bold mb-1">
        Available Actions
        {validActions.length > 0 && (
          // If actions are available, add " for {currentCC} CC"
          <span> for {currentCC} CC</span>
        )}
      </h3>
    </div>

    {validActions.length === 0 ? (
      <div className="text-gray-500 italic text-center py-4">
        No actions available
      </div>
    ) : (
      <div className="grid grid-cols-1 gap-3 w-full">
        {Object.entries(groupedActions).map(([actionType, actions]) => (
          <div key={actionType} className="w-full">
            <div className="grid grid-cols-1 gap-3 w-full">
              {actions.map((action, index) => {
                const cleanDescription = action.description.replace(/\s*\(Cost:.*?\)/, '');
                const shortcutKey = getShortcutKey(action);

                return (
                  <button
                    key={`${action.action_type}-${action.card_id || 'action'}-${index}`}
                    onClick={() => onAction(action)}
                    disabled={isProcessing}
                    className={`
                      w-full block px-4 py-3 rounded transition-all text-sm border-2
                      ${getActionColor(action.action_type)}
                      ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:scale-[1.02] active:scale-95'}
                      ${action.action_type === 'end_turn' && shouldBlink ? 'animate-blink ring-4 ring-yellow-400' : 'border-transparent'}
                      disabled:opacity-50 disabled:cursor-not-allowed
                    `}
                  >
                    <div className="flex justify-between items-center w-full gap-2">
                      {/* Keyboard shortcut indicator */}
                      {shortcutKey && (
                        <span className="w-6 h-6 flex items-center justify-center bg-black/30 rounded text-xs font-mono font-bold flex-shrink-0">
                          {shortcutKey}
                        </span>
                      )}
                      <span className="font-bold text-left flex-1">{cleanDescription}</span>
                      
                      {action.cost_cc !== undefined && action.action_type !== 'end_turn' && (
                        <span className={`
                          px-2 py-1 rounded text-xs font-bold whitespace-nowrap
                          ${action.cost_cc > currentCC ? 'bg-red-800 text-white' : 'bg-black/40 text-white'}
                        `}>
                          {action.cost_cc} CC
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
);
}
