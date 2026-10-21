/* eslint-disable react-refresh/only-export-components -- test-only helpers */
import type { ReactNode } from 'react';
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { vi } from 'vitest';
import { AuthContext, type AuthContextValue } from '@/context/auth-context';
import type { User, UserRole } from '@/types';

export function makeUser(role: UserRole): User {
  return { id: 1, email: 'a@b.com', full_name: 'Ada', role, college_id: 1, is_active: true, is_verified: true };
}

export function AuthStub({ user, children }: { user: User | null; children: ReactNode }) {
  const value: AuthContextValue = {
    user,
    isLoading: false,
    isAuthenticated: user !== null,
    login: vi.fn(),
    logout: vi.fn(),
    updateProfile: vi.fn(),
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function makeAxiosError(status: number, detail: string): AxiosError {
  const response = { status, data: { detail }, statusText: '', headers: {}, config: {} as InternalAxiosRequestConfig } as AxiosResponse;
  return new AxiosError(detail, 'ERR_BAD_REQUEST', undefined, undefined, response);
}
