/**
 * GameCodeDisplay Component
 * 
 * Displays a game code with copy-to-clipboard functionality.
 * Shows visual feedback when code is copied.
 */

import { useCopyToClipboard } from '../../hooks/useCopyToClipboard';

interface GameCodeDisplayProps {
  code: string;
  /** Display size variant */
  size?: 'small' | 'large';
  /** Show label above code */
  showLabel?: boolean;
  /** Custom label text */
  label?: string;
}

export function GameCodeDisplay({
  code,
  size = 'large',
  showLabel = true,
  label = 'Game Code',
}: GameCodeDisplayProps) {
  const { copied, copyToClipboard } = useCopyToClipboard();

  const handleClick = () => {
    copyToClipboard(code);
  };

  const sizeClasses = size === 'large' 
    ? 'text-6xl tracking-widest' 
    : 'text-2xl tracking-widest';

  const feedbackText = size === 'large'
    ? (copied ? '✅ Copied to clipboard!' : '📋 Click to copy')
    : (copied ? '✓' : '📋');

  return (
    <div className="text-center">
      {showLabel && (
        <div className="text-lg text-gray-300 mb-3 font-semibold">
          {label}
        </div>
      )}
      <button
        onClick={handleClick}
        className={`
          font-mono font-bold text-game-highlight 
          hover:text-red-400 transition-colors
          ${sizeClasses}
        `}
        title="Click to copy"
      >
        {code} {size === 'small' && feedbackText}
      </button>
      {size === 'large' && (
        <div className="text-lg text-gray-300 mt-3 font-semibold">
          {feedbackText}
        </div>
      )}
    </div>
  );
}
