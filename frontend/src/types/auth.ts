/**
 * Authentication types for Google OAuth integration.
 */

export interface User {
  google_id: string;
  first_name: string;
  display_name: string;
  custom_display_name: string | null;
}

export interface AuthResponse {
  jwt_token: string;
  user: User;
}

export interface UserProfile {
  google_id: string;
  first_name: string;
  display_name: string;
  custom_display_name: string | null;
  created_at: string;
  updated_at: string;
}
