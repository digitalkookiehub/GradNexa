import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { AuthContext, type AuthContextValue } from './auth-context';
import { setAuthFailureHandler } from '@/services/api';
import { authService } from '@/services/authService';
import { tokenStorage } from '@/lib/tokenStorage';
import type { LoginPayload, User } from '@/types';

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(() => tokenStorage.getAccessToken() !== null);

  useEffect(() => {
    setAuthFailureHandler(() => setUser(null));
    return () => setAuthFailureHandler(null);
  }, []);

  useEffect(() => {
    if (tokenStorage.getAccessToken() === null) return;
    let cancelled = false;
    authService
      .getMe()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        tokenStorage.clear();
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload): Promise<void> => {
    await authService.login(payload);
    try {
      setUser(await authService.getMe());
    } catch (err) {
      tokenStorage.clear();
      throw err;
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    try {
      await authService.logout();
    } catch {
      // server-side revoke failed; local session is still cleared below
    } finally {
      tokenStorage.clear();
      setUser(null);
    }
  }, []);

  const updateProfile = useCallback(async (fullName: string): Promise<void> => {
    setUser(await authService.updateMe(fullName));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, isAuthenticated: user !== null, login, logout, updateProfile }),
    [user, isLoading, login, logout, updateProfile],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
