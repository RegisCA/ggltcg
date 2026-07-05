/**
 * User menu component for authenticated users.
 *
 * Shows user's display name and provides access to logout and profile settings.
 * Overlays game screens — restyled to Paper & Ink (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md):
 * dark panel + gold hairline border, ink text tokens, kept compact since it
 * floats over the board/lobby/victory screens.
 */

import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { ProfileEditModal } from './ProfileEditModal';

export const UserMenu: React.FC = () => {
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  if (!user) return null;

  const handleLogout = () => {
    if (confirm('Are you sure you want to logout?')) {
      logout();
    }
  };

  const handleEditProfile = () => {
    setIsOpen(false);
    setIsProfileModalOpen(true);
  };

  return (
    <div className="fixed top-4 right-4 z-50">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center transition-colors"
        style={{
          gap: 'var(--spacing-component-xs)',
          padding: 'var(--spacing-component-xs) var(--spacing-component-md)',
          borderRadius: '8px',
          background: '#241E17',
          border: '1px solid rgba(242,193,78,.35)',
          color: 'var(--ink-text)',
        }}
      >
        <div
          className="flex items-center justify-center"
          style={{
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            fontWeight: 900,
            background: 'var(--gold)',
            color: 'var(--desk-bottom)',
          }}
        >
          {user.first_name.charAt(0).toUpperCase()}
        </div>
        <span style={{ fontWeight: 700, fontSize: '14px' }}>{user.display_name}</span>
        <svg
          className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}
          style={{ width: '14px', height: '14px' }}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          {/* Backdrop to close menu */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown menu - positioned to the right */}
          <div
            className="absolute left-0 overflow-hidden z-50"
            style={{
              marginTop: 'var(--spacing-component-xs)',
              width: '240px',
              background: '#241E17',
              border: '1px solid rgba(242,193,78,.35)',
              borderRadius: '8px',
              boxShadow: '0 8px 24px rgba(0,0,0,.4)',
            }}
          >
            <div
              style={{
                padding: 'var(--spacing-component-md)',
                borderBottom: '1px solid rgba(237,232,222,.12)',
              }}
            >
              <div className="flex items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
                <div
                  className="flex items-center justify-center"
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    fontWeight: 900,
                    fontSize: '18px',
                    background: 'var(--gold)',
                    color: 'var(--desk-bottom)',
                  }}
                >
                  {user.first_name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div style={{ fontWeight: 900, color: 'var(--ink-text)' }}>{user.display_name}</div>
                  <div style={{ fontSize: '12px', color: 'var(--ink-faint)' }}>
                    {user.custom_display_name ? 'Custom name' : 'Using first name'}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ padding: 'var(--spacing-component-xs)' }}>
              <button
                onClick={handleEditProfile}
                className="w-full text-left transition-colors"
                style={{
                  padding: 'var(--spacing-component-xs) var(--spacing-component-md)',
                  borderRadius: '6px',
                  background: 'none',
                  border: 'none',
                  color: 'var(--ink-text)',
                  cursor: 'pointer',
                }}
              >
                <div className="flex items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
                  <svg style={{ width: '18px', height: '18px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span>Edit Profile</span>
                </div>
              </button>

              <button
                onClick={handleLogout}
                className="w-full text-left transition-colors"
                style={{
                  padding: 'var(--spacing-component-xs) var(--spacing-component-md)',
                  borderRadius: '6px',
                  background: 'none',
                  border: 'none',
                  color: 'var(--danger)',
                  cursor: 'pointer',
                }}
              >
                <div className="flex items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
                  <svg style={{ width: '18px', height: '18px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  <span>Logout</span>
                </div>
              </button>
            </div>
          </div>
        </>
      )}

      {/* Profile Edit Modal */}
      <ProfileEditModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
      />
    </div>
  );
};
