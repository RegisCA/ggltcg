/**
 * GameCodeDisplay Component
 *
 * Displays a game code with copy-to-clipboard functionality.
 * Shows visual feedback when code is copied. Paper & Ink: mono/gold code,
 * text-only copy feedback (no clipboard emoji).
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

  const codeFontSize = size === 'large' ? 'clamp(32px, 8vw, 48px)' : '20px';
  const feedbackText = copied ? 'Copied to clipboard!' : 'Click to copy';

  return (
    <div className="text-center">
      {showLabel && (
        <div
          style={{
            fontSize: '13px',
            fontWeight: 700,
            color: 'var(--ink-muted)',
            marginBottom: 'var(--spacing-component-sm)',
          }}
        >
          {label}
        </div>
      )}
      <button
        onClick={handleClick}
        title="Click to copy"
        style={{
          fontFamily: 'monospace',
          fontWeight: 900,
          letterSpacing: '.15em',
          fontSize: codeFontSize,
          color: 'var(--gold)',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
        }}
      >
        {code}
      </button>
      {size === 'large' && (
        <div
          style={{
            fontSize: '13px',
            fontWeight: 700,
            color: copied ? 'var(--you)' : 'var(--ink-muted)',
            marginTop: 'var(--spacing-component-sm)',
          }}
        >
          {feedbackText}
        </div>
      )}
      {size === 'small' && (
        <div
          style={{
            fontSize: '11px',
            fontWeight: 700,
            color: copied ? 'var(--you)' : 'var(--ink-faint)',
          }}
        >
          {feedbackText}
        </div>
      )}
    </div>
  );
}
