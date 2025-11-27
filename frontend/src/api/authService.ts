/**
 * Authentication API service.
 * 
 * Handles communication with backend authentication endpoints.
 */

import axios from 'axios';
import type { AuthResponse, UserProfile } from '../types/auth';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const authService = {
  /**
   * Authenticate with Google OAuth token.
   * 
   * @param googleToken - Google ID token from OAuth flow
   * @returns JWT token and user information
   */
  async authenticateWithGoogle(googleToken: string): Promise<AuthResponse> {
    const response = await axios.post<AuthResponse>(
      `${API_BASE_URL}/auth/google`,
      { token: googleToken }
    );
    return response.data;
  },

  /**
   * Verify JWT token is still valid.
   * 
   * @param jwtToken - JWT token to verify
   * @returns Whether token is valid
   */
  async verifyToken(jwtToken: string): Promise<{ valid: boolean; google_id: string }> {
    const response = await axios.get(`${API_BASE_URL}/auth/verify`, {
      headers: {
        Authorization: `Bearer ${jwtToken}`,
      },
    });
    return response.data;
  },

  /**
   * Get current user's profile.
   * 
   * @param jwtToken - JWT token for authentication
   * @returns User profile information
   */
  async getUserProfile(jwtToken: string): Promise<UserProfile> {
    const response = await axios.get<UserProfile>(`${API_BASE_URL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${jwtToken}`,
      },
    });
    return response.data;
  },

  /**
   * Update user's custom display name.
   * 
   * @param jwtToken - JWT token for authentication
   * @param displayName - New display name (or null to clear)
   * @returns Updated user information
   */
  async updateDisplayName(
    jwtToken: string,
    displayName: string | null
  ): Promise<{ success: boolean; user: UserProfile }> {
    const response = await axios.put(
      `${API_BASE_URL}/auth/profile`,
      { display_name: displayName },
      {
        headers: {
          Authorization: `Bearer ${jwtToken}`,
        },
      }
    );
    return response.data;
  },
};
