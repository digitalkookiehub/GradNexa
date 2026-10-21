import api from './api';
import { tokenStorage } from '@/lib/tokenStorage';
import type { LoginPayload, RegisterPayload, TokenPair, User } from '@/types';

export const authService = {
  async register(payload: RegisterPayload): Promise<User> {
    const { data } = await api.post<User>('/auth/register', payload);
    return data;
  },

  async login(payload: LoginPayload): Promise<TokenPair> {
    const { data } = await api.post<TokenPair>('/auth/login', payload);
    tokenStorage.setTokens(data.access_token, data.refresh_token);
    return data;
  },

  async logout(): Promise<void> {
    const refreshToken = tokenStorage.getRefreshToken();
    try {
      if (refreshToken) await api.post('/auth/logout', { refresh_token: refreshToken });
    } finally {
      tokenStorage.clear();
    }
  },

  async forgotPassword(email: string): Promise<void> {
    await api.post('/auth/forgot-password', { email });
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    await api.post('/auth/reset-password', { token, new_password: newPassword });
  },

  async getMe(): Promise<User> {
    const { data } = await api.get<User>('/auth/me');
    return data;
  },

  async updateMe(fullName: string): Promise<User> {
    const { data } = await api.put<User>('/auth/me', { full_name: fullName });
    return data;
  },
};
