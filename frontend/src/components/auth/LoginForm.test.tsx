import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { LoginForm } from './LoginForm';
import { AuthContext, type AuthContextValue } from '@/context/auth-context';

function renderForm(login: AuthContextValue['login'], onSuccess?: () => void) {
  const value: AuthContextValue = {
    user: null,
    isLoading: false,
    isAuthenticated: false,
    login,
    logout: vi.fn(),
    updateProfile: vi.fn(),
  };
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={value}>
        <LoginForm onSuccess={onSuccess} />
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

describe('LoginForm', () => {
  it('disables submit until fields are filled', () => {
    renderForm(vi.fn());
    expect(screen.getByRole('button', { name: /sign in/i })).toBeDisabled();
  });

  it('submits credentials and calls onSuccess', async () => {
    const login = vi.fn().mockResolvedValue(undefined);
    const onSuccess = vi.fn();
    renderForm(login, onSuccess);
    await userEvent.type(screen.getByLabelText('Email'), 'a@b.com');
    await userEvent.type(screen.getByLabelText('Password'), 'secret123');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(login).toHaveBeenCalledWith({ email: 'a@b.com', password: 'secret123' });
  });

  it('shows the server error on failure', async () => {
    const login = vi.fn().mockRejectedValue(new Error('Invalid credentials'));
    renderForm(login);
    await userEvent.type(screen.getByLabelText('Email'), 'a@b.com');
    await userEvent.type(screen.getByLabelText('Password'), 'bad');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid credentials');
  });
});
