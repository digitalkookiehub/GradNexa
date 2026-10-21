import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { tokenStorage } from '@/lib/tokenStorage';
import type { TokenPair } from '@/types';

export const API_BASE_URL = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

type AuthFailureHandler = () => void;
let authFailureHandler: AuthFailureHandler | null = null;

export function setAuthFailureHandler(handler: AuthFailureHandler | null): void {
  authFailureHandler = handler;
}

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

const AUTH_PATHS_WITHOUT_REFRESH = [
  '/auth/login',
  '/auth/register',
  '/auth/refresh',
  '/auth/forgot-password',
  '/auth/reset-password',
];

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) throw new Error('No refresh token');
  // Use a bare axios call so this request does not re-enter our interceptors.
  const { data } = await axios.post<TokenPair>(`${API_BASE_URL}/auth/refresh`, {
    refresh_token: refreshToken,
  });
  tokenStorage.setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    const isAuthEndpoint = AUTH_PATHS_WITHOUT_REFRESH.some((p) => original?.url?.startsWith(p));

    if (error.response?.status === 401 && original && !original._retry && !isAuthEndpoint) {
      original._retry = true;
      try {
        refreshPromise = refreshPromise ?? refreshAccessToken();
        const newToken = await refreshPromise;
        original.headers.Authorization = `Bearer ${newToken}`;
        return await api(original);
      } catch {
        tokenStorage.clear();
        authFailureHandler?.();
        return Promise.reject(error);
      } finally {
        refreshPromise = null;
      }
    }
    return Promise.reject(error);
  },
);

export default api;
