import { act, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { AuthProvider } from './AuthContext';
import { useAuth } from '@/hooks/useAuth';
import { authService } from '@/services/authService';
import { tokenStorage } from '@/lib/tokenStorage';
import type { User } from '@/types';

vi.mock('@/services/authService', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    getMe: vi.fn(),
    updateMe: vi.fn(),
  },
}));

const user: User = { id: 1, email: 'a@b.com', full_name: 'Ada', role: 'STUDENT', college_id: 1, is_active: true, is_verified: false };

function Probe() {
  const { user: u, isLoading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="state">{isLoading ? 'loading' : u ? u.full_name : 'anon'}</span>
      <button onClick={() => void login({ email: 'a@b.com', password: 'pw' })}>login</button>
      <button onClick={() => void logout()}>logout</button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    tokenStorage.clear();
  });

  it('is anonymous without a stored token', () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    expect(screen.getByTestId('state')).toHaveTextContent('anon');
    expect(authService.getMe).not.toHaveBeenCalled();
  });

  it('restores the user from a stored token', async () => {
    tokenStorage.setTokens('a', 'r');
    vi.mocked(authService.getMe).mockResolvedValue(user);
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    expect(screen.getByTestId('state')).toHaveTextContent('loading');
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('Ada'));
  });

  it('logs in and logs out', async () => {
    vi.mocked(authService.login).mockResolvedValue({ access_token: 'a', refresh_token: 'r', token_type: 'bearer' });
    vi.mocked(authService.getMe).mockResolvedValue(user);
    vi.mocked(authService.logout).mockResolvedValue(undefined);
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await act(async () => screen.getByText('login').click());
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('Ada'));
    await act(async () => screen.getByText('logout').click());
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('anon'));
  });

  it('clears an invalid stored session', async () => {
    tokenStorage.setTokens('bad', 'bad');
    vi.mocked(authService.getMe).mockRejectedValue(new Error('401'));
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('anon'));
    expect(tokenStorage.getAccessToken()).toBeNull();
  });
});
