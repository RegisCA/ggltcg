/**
 * Shared Footer Component
 *
 * Consistent footer with branding, copyright, and legal links.
 * Used across LoginPage, LobbyHome, and LoadingScreen.
 *
 * Restyled to Paper & Ink tokens (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md) —
 * last legacy `ui/` piece these screens pull in. The `variant` prop is now a
 * no-op kept for API compatibility (both consumers render on the dark desk
 * background, so there is no longer a light/dark split); ink text tokens
 * cover both cases.
 */

import React from 'react';

interface FooterProps {
  onShowPrivacyPolicy?: () => void;
  onShowTermsOfService?: () => void;
  /** @deprecated retained for API compatibility; both variants now render with ink tokens. */
  variant?: 'light' | 'dark';
  /** Show the tagline above links */
  showTagline?: boolean;
  /** Additional className for container */
  className?: string;
}

export const Footer: React.FC<FooterProps> = ({
  onShowPrivacyPolicy,
  onShowTermsOfService,
  showTagline = true,
  className = '',
}) => {
  return (
    <footer
      className={`text-center ${className}`}
      style={{ marginTop: 'var(--spacing-component-xl)', fontSize: '13px', color: 'var(--ink-faint)' }}
    >
      {showTagline && (
        <p style={{ marginBottom: 'var(--spacing-component-xs)' }}>
          A tactical card game where strategy meets imagination
        </p>
      )}

      <p style={{ marginBottom: 'var(--spacing-component-xs)' }}>
        © 2025 GGLTCG
        <span style={{ margin: '0 8px' }}>•</span>
        <a
          href="https://github.com/RegisCA/ggltcg"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'var(--you)', textDecoration: 'none' }}
        >
          GitHub
        </a>
      </p>

      {(onShowPrivacyPolicy || onShowTermsOfService) && (
        <p>
          {onShowPrivacyPolicy && (
            <button
              onClick={onShowPrivacyPolicy}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--you)', textDecoration: 'underline' }}
            >
              Privacy Policy
            </button>
          )}
          {onShowPrivacyPolicy && onShowTermsOfService && (
            <span style={{ margin: '0 8px' }}>•</span>
          )}
          {onShowTermsOfService && (
            <button
              onClick={onShowTermsOfService}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--you)', textDecoration: 'underline' }}
            >
              Terms of Service
            </button>
          )}
        </p>
      )}
    </footer>
  );
};
