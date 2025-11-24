/**
 * ActionPanel Component
 * Displays available actions and handles player inputs
 */

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
  const groupedActions = validActions.reduce((acc, action) => {
    if (!acc[action.action_type]) {
      acc[action.action_type] = [];
    }
    acc[action.action_type].push(action);
    return acc;
  }, {} as Record<string, ValidAction[]>);

  const getActionTypeLabel = (type: string) => {
    switch (type) {
      case 'play_card':
        return 'Play Cards';
      case 'tussle':
        return 'Tussle';
      case 'end_turn':
        return 'End Turn';
      default:
        return type;
    }
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
    <div className="p-3 bg-game-card rounded border-2 border-game-accent">
      <div className="mb-3">
        <h3 className="text-lg font-bold mb-1">Available Actions for {currentCC} CC</h3>
      </div>

      {validActions.length === 0 ? (
        <div className="text-gray-500 italic text-center py-4">
          No actions available
        </div>
      ) : (
        <div className="space-y-3">
          {Object.entries(groupedActions).map(([actionType, actions]) => (
            <div key={actionType}>
              <div className="space-y-1.5">
                {actions.map((action, index) => (
                  <button
                    key={`${action.action_type}-${action.card_name || 'action'}-${index}`}
                    onClick={() => onAction(action)}
                    disabled={isProcessing}
                    className={`
                      w-full px-3 py-2 rounded text-left transition-all text-sm
                      ${getActionColor(action.action_type)}
                      ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:scale-102'}
                      disabled:opacity-50 disabled:cursor-not-allowed
                    `}
                  >
                    <div className="flex justify-between items-center gap-2">
                      <span className="font-medium leading-tight">{action.description}</span>
                      {action.cost_cc !== undefined && action.action_type !== 'end_turn' && (
                        <span className={`
                          px-2 py-0.5 rounded text-xs font-bold whitespace-nowrap
                          ${action.cost_cc > currentCC ? 'bg-red-800' : 'bg-black bg-opacity-30'}
                        `}>
                          {action.cost_cc} CC
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
