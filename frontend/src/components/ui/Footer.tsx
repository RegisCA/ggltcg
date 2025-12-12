/**
 * Shared Footer Component
 * 
 * Consistent footer with branding, copyright, and legal links.
 * Used across LoginPage, LobbyHome, and LoadingScreen.
 */

import React from 'react';

interface FooterProps {
  onShowPrivacyPolicy?: () => void;
  onShowTermsOfService?: () => void;
  /** Variant styling - 'light' for dark backgrounds, 'dark' for light backgrounds */
  variant?: 'light' | 'dark';
  /** Show the tagline above links */
  showTagline?: boolean;
  /** Additional className for container */
  className?: string;
}

export const Footer: React.FC<FooterProps> = ({
  onShowPrivacyPolicy,
  onShowTermsOfService,
  variant = 'light',
  showTagline = true,
  className = '',
}) => {
  const textColor = variant === 'light' ? 'text-gray-400' : 'text-gray-600';
  const linkColor = variant === 'light' ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-500';
  
  return (
    <footer 
      className={`text-center text-sm ${textColor} ${className}`}
      style={{ marginTop: 'var(--spacing-component-xl)' }}
    >
      {showTagline && (
        <p style={{ marginBottom: 'var(--spacing-component-xs)' }}>
          A tactical card game where strategy meets imagination
        </p>
      )}
      
      <p style={{ marginBottom: 'var(--spacing-component-xs)' }}>
        © 2025 GGLTCG
        <span className="mx-2">•</span>
        <a 
          href="https://github.com/RegisCA/ggltcg" 
          target="_blank" 
          rel="noopener noreferrer"
          className={`${linkColor} hover:underline`}
        >
          GitHub
        </a>
      </p>
      
      {(onShowPrivacyPolicy || onShowTermsOfService) && (
        <p>
          {onShowPrivacyPolicy && (
            <button
              onClick={onShowPrivacyPolicy}
              className={`${linkColor} hover:underline`}
            >
              Privacy Policy
            </button>
          )}
          {onShowPrivacyPolicy && onShowTermsOfService && (
            <span className="mx-2">•</span>
          )}
          {onShowTermsOfService && (
            <button
              onClick={onShowTermsOfService}
              className={`${linkColor} hover:underline`}
            >
              Terms of Service
            </button>
          )}
        </p>
      )}
    </footer>
  );
};
