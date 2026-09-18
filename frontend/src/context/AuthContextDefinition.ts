import { createContext } from 'react';
import type { User, SignupResponse } from '../types/auth';

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (name: string, email: string, username: string, password: string) => Promise<SignupResponse>;
  logout: () => Promise<void>;
  refetchUser: () => Promise<User | null>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);
