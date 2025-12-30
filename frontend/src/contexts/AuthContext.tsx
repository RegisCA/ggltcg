/* eslint-disable react-refresh/only-export-components */
/**
 * Authentication context for managing user authentication state.
 * 
 * Provides authentication state, login/logout functions, and JWT token management.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import type { User } from '../types/auth';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  updateUser: (user: User) => void;
  refreshToken: (newToken: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'ggltcg_auth_token';
const USER_KEY = 'ggltcg_user';

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Check if a JWT token is expired.
 * @param token - JWT token string
 * @returns true if token is expired or invalid
 */
const isTokenExpired = (token: string): boolean => {
  try {
    // Validate JWT format (header.payload.signature)
    const parts = token.split('.');
    if (parts.length !== 3) {
      return true; // Invalid JWT format
    }
    
    const payload = JSON.parse(atob(parts[1]));
    const exp = payload.exp * 1000; // Convert to milliseconds
    // Check if token is expired (add 60s buffer to refresh before actual expiry)
    return Date.now() >= (exp - 60000);
  } catch {
    return true; // Invalid token format
  }
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Define callbacks before useEffect hooks that reference them
  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }, []);

  const updateUser = useCallback((updatedUser: User) => {
    setUser(updatedUser);
    localStorage.setItem(USER_KEY, JSON.stringify(updatedUser));
  }, []);

  const refreshToken = useCallback((newToken: string) => {
    setToken(newToken);
    localStorage.setItem(TOKEN_KEY, newToken);
  }, []);

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem(TOKEN_KEY, newToken);
    localStorage.setItem(USER_KEY, JSON.stringify(newUser));
  };

  // Load auth state from localStorage on mount and validate token
  useEffect(() => {
    const loadAuthState = () => {
      try {
        const storedToken = localStorage.getItem(TOKEN_KEY);
        const storedUser = localStorage.getItem(USER_KEY);

        if (storedToken && storedUser) {
          // Check if token is expired
          if (isTokenExpired(storedToken)) {
            console.log('Token expired on load, clearing auth state');
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);
          } else {
            setToken(storedToken);
            setUser(JSON.parse(storedUser));
          }
        }
      } catch (error) {
        console.error('Failed to load auth state:', error);
        // Clear invalid data
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      } finally {
        setIsLoading(false);
      }
    };

    loadAuthState();
  }, []);

  // Validate token periodically (every 5 minutes)
  useEffect(() => {
    if (!token) return;

    const intervalId = setInterval(() => {
      if (isTokenExpired(token)) {
        console.log('Token expired during session, logging out');
        logout();
      }
    }, 5 * 60 * 1000); // Check every 5 minutes

    return () => clearInterval(intervalId);
  }, [token, logout]);

  // Listen for token refresh events from axios interceptor
  useEffect(() => {
    const handleTokenRefresh = (event: CustomEvent<{ token: string }>) => {
      const newToken = event.detail.token;
      console.log('Token refreshed automatically');
      refreshToken(newToken);
    };

    window.addEventListener('token-refreshed', handleTokenRefresh as EventListener);
    return () => window.removeEventListener('token-refreshed', handleTokenRefresh as EventListener);
  }, [refreshToken]);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    isLoading,
    login,
    logout,
    updateUser,
    refreshToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
