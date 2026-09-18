/**
 * Authentication TypeScript type definitions.
 */

export interface User {
  id: string;
  name: string;
  email: string;
  username: string;
  isEmailVerified: boolean;
}

export interface AuthResponse {
  user: User;
  message: string;
}

export interface SignupResponse {
  user: User;
  message: string;
  devVerificationToken?: string | null;
  devVerificationUrl?: string | null;
}

export interface MessageResponse {
  message: string;
  devVerificationToken?: string | null;
  devVerificationUrl?: string | null;
  devResetToken?: string | null;
  devResetUrl?: string | null;
}
