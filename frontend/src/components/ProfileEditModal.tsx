/**
 * Profile edit modal for updating display name.
 * 
 * Allows users to set or change their custom display name with validation.
 */

import React, { useState } from 'react';
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

  const handleCancel = () => {
    setDisplayName(user.custom_display_name || '');
    setError(null);
    onClose();
  };

  return (
    <>
      {/* Backdrop */}
      <div
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
          padding: '2rem'
        }}
        onClick={handleCancel}
      >
        {/* Modal */}
        <div
          className="bg-gray-900 rounded-xl border-4 border-game-highlight shadow-2xl flex flex-col"
          style={{
            width: '600px',
            maxHeight: '80vh',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-6 border-b-4 border-game-accent bg-gray-800 flex-shrink-0">
            <h2 className="text-3xl font-bold mb-2 text-game-highlight">Edit Profile</h2>
            <p className="text-lg text-gray-300 mb-6">Customize how others see you</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 overflow-y-auto flex-1">
            <div className="mb-6">
              <label htmlFor="displayName" className="block text-gray-200 font-bold mb-3 text-lg">
                Display Name
              </label>
              <input
                type="text"
                id="displayName"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                maxLength={50}
                placeholder={user.first_name}
                className="w-full px-4 py-3 bg-gray-700 border-2 border-gray-600 rounded-lg text-white placeholder-gray-400 text-lg focus:ring-2 focus:ring-game-highlight focus:border-game-highlight outline-none transition-all"
                disabled={isLoading}
              />
              <p className="text-sm text-gray-400 mt-2">
                Leave empty to use your first name: <span className="font-semibold text-gray-300">{user.first_name}</span>
              </p>
              <p className="text-sm text-gray-400 mt-1">
                {displayName.length}/50 characters
              </p>
            </div>

            {error && (
              <div className="mb-4 p-4 bg-red-900/50 border-2 border-red-500 text-red-200 rounded-lg">
                {error}
              </div>
            )}

            <div className="mb-6 p-4 bg-blue-900/30 border-2 border-blue-500/50 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="w-6 h-6 text-blue-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="text-gray-300">
                  <p className="font-bold mb-2 text-lg">Display name rules:</p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>1-50 characters</li>
                    <li>No inappropriate language</li>
                    <li>Be respectful to other players</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Buttons */}
            <div className="flex gap-4 pt-4">
              <button
                type="button"
                onClick={handleCancel}
                disabled={isLoading}
                className="flex-1 px-6 py-3 rounded-lg bg-gray-600 hover:bg-gray-700 font-bold transition-all text-white text-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 px-6 py-3 rounded-lg bg-game-highlight hover:bg-red-600 font-bold transition-all text-white text-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
};
