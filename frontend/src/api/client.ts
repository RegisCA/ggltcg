/**
 * Axios client configuration for GGLTCG API
 */

import axios from 'axios';
import type { AxiosError, InternalAxiosRequestConfig } from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 90000, // 90 seconds (health checks during cold start + AI turns with Gemini retries)
});

// Track if we're currently refreshing the token to avoid multiple simultaneous refresh attempts
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

// Notify all subscribers when token refresh completes
const onTokenRefreshed = (token: string) => {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
};

// Add a request to the queue to be retried after token refresh
const addRefreshSubscriber = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback);
};

// Add request interceptor to include auth token
apiClient.interceptors.request.use(
  (config) => {
    // Get token from localStorage
    const token = localStorage.getItem('ggltcg_auth_token');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling with token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    
    if (error.response) {
      // Server responded with error
      console.error('API Error:', error.response.data);
      
      // Handle 401 Unauthorized - attempt token refresh
      if (error.response.status === 401 && originalRequest && !originalRequest._retry) {
        // Skip refresh for auth endpoints to avoid infinite loops
        if (originalRequest.url?.includes('/auth/google') || 
            originalRequest.url?.includes('/auth/refresh')) {
          // Clear auth state and reload
          localStorage.removeItem('ggltcg_auth_token');
          localStorage.removeItem('ggltcg_user');
          window.location.href = '/';
          return Promise.reject(error);
        }

        // If already refreshing, queue this request
        if (isRefreshing) {
          return new Promise((resolve) => {
            addRefreshSubscriber((token: string) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              resolve(apiClient(originalRequest));
            });
          });
        }

        // Mark that we're refreshing
        originalRequest._retry = true;
        isRefreshing = true;

        try {
          // Attempt to refresh the token
          const token = localStorage.getItem('ggltcg_auth_token');
          
          if (!token) {
            throw new Error('No token to refresh');
          }

          // Use raw axios instead of apiClient to avoid triggering this interceptor recursively
          const response = await axios.post(
            `${apiClient.defaults.baseURL}/auth/refresh`,
            {},
            {
              headers: {
                Authorization: `Bearer ${token}`,
              },
            }
          );

          const newToken = response.data.jwt_token;
          
          try {
            // Update token in localStorage
            localStorage.setItem('ggltcg_auth_token', newToken);
            
            // Update the auth context via custom event
            window.dispatchEvent(new CustomEvent('token-refreshed', { detail: { token: newToken } }));
            
            // Notify all queued requests
            onTokenRefreshed(newToken);
          } catch (notifyError) {
            console.error('Failed to update token after refresh:', notifyError);
            // Continue anyway - the new token is valid even if notification failed
          }
          
          // Retry the original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
          }
          
          isRefreshing = false;
          return apiClient(originalRequest);
          
        } catch (refreshError) {
          // Refresh failed - clear auth and reload
          isRefreshing = false;
          refreshSubscribers = [];
          localStorage.removeItem('ggltcg_auth_token');
          localStorage.removeItem('ggltcg_user');
          window.location.href = '/';
          return Promise.reject(refreshError);
        }
      }
    } else if (error.request) {
      // No response received
      console.error('Network Error:', error.message);
    } else {
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);
