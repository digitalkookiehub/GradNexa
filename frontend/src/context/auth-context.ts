import { createContext } from 'react';
import type { LoginPayload, User } from '@/types';

export interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (fullName: string) => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
