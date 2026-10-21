const ACCESS_KEY = 'gradnexa_access_token';
const REFRESH_KEY = 'gradnexa_refresh_token';

// In-memory copy is the source of truth during a session; localStorage is a
// best-effort persistence layer so a page reload keeps the user signed in.
let accessToken: string | null = null;
let refreshToken: string | null = null;
let hydrated = false;

function safeGet(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // storage unavailable (private mode / quota): keep in-memory only
  }
}

function safeRemove(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // ignore
  }
}

function hydrate(): void {
  if (hydrated) return;
  hydrated = true;
  accessToken = safeGet(ACCESS_KEY);
  refreshToken = safeGet(REFRESH_KEY);
}

export const tokenStorage = {
  getAccessToken(): string | null {
    hydrate();
    return accessToken;
  },
  getRefreshToken(): string | null {
    hydrate();
    return refreshToken;
  },
  setTokens(access: string, refresh: string): void {
    hydrated = true;
    accessToken = access;
    refreshToken = refresh;
    safeSet(ACCESS_KEY, access);
    safeSet(REFRESH_KEY, refresh);
  },
  clear(): void {
    hydrated = true;
    accessToken = null;
    refreshToken = null;
    safeRemove(ACCESS_KEY);
    safeRemove(REFRESH_KEY);
  },
};
