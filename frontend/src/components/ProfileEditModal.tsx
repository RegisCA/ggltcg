/**
 * Profile edit modal for updating display name.
 *
 * Allows users to set or change their custom display name with validation.
 * Restyled to Paper & Ink (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md) — the
 * settled dark-panel + gold-hairline modal idiom from Leaderboard.tsx /
 * PlayerStats.tsx: dark `#241E17` panel, gold hairline border, Gochi Hand
 * header, gold primary button with the `0 3px 0` shadow, backdrop-click +
 * Esc close. All behavior (validation, save/cancel, error states) unchanged.
 */

import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { authService } from '../api/authService';

interface ProfileEditModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ProfileEditModal: React.FC<ProfileEditModalProps> = ({ isOpen, onClose }) => {
  const { user, token, updateUser, logout } = useAuth();
  const [displayName, setDisplayName] = useState(user?.custom_display_name || '');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleCancel = React.useCallback(() => {
    setDisplayName(user?.custom_display_name || '');
    setError(null);
    onClose();
  }, [user, onClose]);

  // Re-sync the field when the modal opens (or the loaded user changes) —
  // AuthContext hydrates user/token from localStorage asynchronously, so the
  // initial useState value can be stale on first mount.
  useEffect(() => {
    if (isOpen) setDisplayName(user?.custom_display_name || '');
  }, [isOpen, user]);

  // Esc closes, matching the settled modal idiom (Leaderboard/PlayerStats).
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleCancel();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleCancel]);

  if (!isOpen || !user || !token) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const trimmedName = displayName.trim();

      // If empty, clear custom name (will use first name)
      const nameToSend = trimmedName === '' ? null : trimmedName;

      const result = await authService.updateDisplayName(token, nameToSend);

      if (result.success) {
        // Update user in context
        updateUser({
          ...user,
          custom_display_name: result.user.custom_display_name,
          display_name: result.user.display_name,
        });
        onClose();
      }
    } catch (err: unknown) {
      console.error('Failed to update display name:', err);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const errorResponse = (err as any).response;

      // Handle expired token (401 Unauthorized)
      if (errorResponse?.status === 401) {
        // Token has expired - log user out and show friendly message
        logout();
        setError('Your session has expired. Please log in again to edit your profile.');
        setIsLoading(false);
        return;
      }

      // Handle other errors
      setError(errorResponse?.data?.detail || 'Failed to update display name. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const trimmedLength = displayName.trim().length;
  const isNameTooLong = displayName.length > 50;
  const canSave = !isLoading && !isNameTooLong;

  return (
    <div
      onClick={(e) => {
        if (e.target === e.currentTarget) handleCancel();
      }}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 9999,
        backgroundColor: 'rgba(0, 0, 0, 0.80)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--spacing-component-md)',
      }}
    >
      <div
        className="flex flex-col"
        style={{
          width: '480px',
          maxWidth: '100%',
          maxHeight: '85vh',
          background: 'var(--color-panel)',
          borderRadius: '8px',
          border: '1px solid var(--gold)',
          boxShadow: '0 8px 24px rgba(0,0,0,.4)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex-shrink-0 flex justify-between items-start"
          style={{
            padding: 'var(--spacing-component-md)',
            borderBottom: '1px solid rgba(242,193,78,.25)',
          }}
        >
          <div>
            <h2 style={{ fontFamily: 'var(--font-card-name)', fontSize: '28px', color: 'var(--ink-text)' }}>
              Edit Profile
            </h2>
            <p style={{ marginTop: '4px', fontSize: '14px', color: 'var(--ink-muted)' }}>
              Customize how others see you
            </p>
          </div>
          <button
            onClick={handleCancel}
            aria-label="Close edit profile"
            style={{
              fontSize: '22px',
              fontWeight: 900,
              color: 'var(--ink-faint)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            &times;
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="overflow-y-auto flex-1" style={{ padding: 'var(--spacing-component-lg)' }}>
          <div style={{ marginBottom: 'var(--spacing-component-lg)' }}>
            <label
              htmlFor="displayName"
              style={{
                display: 'block',
                fontWeight: 700,
                fontSize: '15px',
                color: 'var(--ink-text)',
                marginBottom: 'var(--spacing-component-sm)',
              }}
            >
              Display Name
            </label>
            <input
              type="text"
              id="displayName"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              maxLength={50}
              placeholder={user.first_name}
              disabled={isLoading}
              style={{
                width: '100%',
                background: 'rgba(0,0,0,.25)',
                border: '1px solid rgba(242,193,78,.35)',
                borderRadius: '6px',
                color: 'var(--ink-text)',
                fontSize: '16px',
                padding: 'var(--spacing-component-sm) var(--spacing-component-md)',
                outline: 'none',
              }}
            />
            <p style={{ marginTop: 'var(--spacing-component-xs)', fontSize: '13px', color: 'var(--ink-faint)' }}>
              Leave empty to use your first name: <span style={{ fontWeight: 700, color: 'var(--ink-muted)' }}>{user.first_name}</span>
            </p>
            <p style={{ marginTop: 'var(--spacing-component-xs)', fontSize: '13px', color: isNameTooLong ? 'var(--danger)' : 'var(--ink-faint)' }}>
              {trimmedLength}/50 characters
            </p>
          </div>

          {error && (
            <div
              style={{
                marginBottom: 'var(--spacing-component-md)',
                padding: 'var(--spacing-component-md)',
                borderRadius: '6px',
                border: '1px solid var(--danger)',
                background: 'rgba(224,113,107,.12)',
                color: 'var(--danger)',
              }}
            >
              {error}
            </div>
          )}

          <div
            style={{
              marginBottom: 'var(--spacing-component-lg)',
              padding: 'var(--spacing-component-md)',
              borderRadius: '6px',
              background: 'rgba(0,0,0,.25)',
            }}
          >
            <p style={{ fontWeight: 700, fontSize: '14px', color: 'var(--ink-text)', marginBottom: 'var(--spacing-component-xs)' }}>
              Display name rules:
            </p>
            <ul style={{ listStyle: 'disc', paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <li style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>1-50 characters</li>
              <li style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>No inappropriate language</li>
              <li style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>Be respectful to other players</li>
            </ul>
          </div>

          {/* Buttons */}
          <div className="flex" style={{ gap: 'var(--spacing-component-md)' }}>
            <button
              type="button"
              onClick={handleCancel}
              disabled={isLoading}
              style={{
                flex: 1,
                padding: 'var(--spacing-component-sm) var(--spacing-component-lg)',
                borderRadius: '6px',
                border: 'none',
                fontWeight: 900,
                background: 'rgba(237,232,222,.1)',
                color: 'var(--ink-text)',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                opacity: isLoading ? 0.5 : 1,
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSave}
              style={{
                flex: 1,
                padding: 'var(--spacing-component-sm) var(--spacing-component-lg)',
                borderRadius: '6px',
                border: 'none',
                fontWeight: 900,
                background: 'var(--gold)',
                color: 'var(--desk-bottom)',
                boxShadow: '0 3px 0 rgba(0,0,0,.5)',
                cursor: canSave ? 'pointer' : 'not-allowed',
                opacity: canSave ? 1 : 0.5,
              }}
            >
              {isLoading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
