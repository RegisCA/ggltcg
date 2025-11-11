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
    <div className="p-4 bg-game-card rounded-lg border-2 border-game-accent">
      <div className="mb-4">
        <h3 className="text-xl font-bold mb-1">Available Actions</h3>
        <div className="text-sm text-gray-400">Current CC: {currentCC}</div>
      </div>

      {validActions.length === 0 ? (
        <div className="text-gray-500 italic text-center py-8">
          No actions available
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(groupedActions).map(([actionType, actions]) => (
            <div key={actionType}>
              <h4 className="text-sm font-bold text-gray-400 mb-2">
                {getActionTypeLabel(actionType)}
              </h4>
              <div className="space-y-2">
                {actions.map((action, index) => (
                  <button
                    key={`${action.action_type}-${action.card_name || 'action'}-${index}`}
                    onClick={() => onAction(action)}
                    disabled={isProcessing}
                    className={`
                      w-full px-4 py-3 rounded-lg text-left transition-all
                      ${getActionColor(action.action_type)}
                      ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:scale-102'}
                      disabled:opacity-50 disabled:cursor-not-allowed
                    `}
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-medium">{action.description}</span>
                      {action.cost_cc !== undefined && (
                        <span className={`
                          px-2 py-1 rounded text-xs font-bold
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
