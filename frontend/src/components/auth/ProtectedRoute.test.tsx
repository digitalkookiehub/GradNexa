import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import { ProtectedRoute } from './ProtectedRoute';
import { AuthContext, type AuthContextValue } from '@/context/auth-context';
import type { User, UserRole } from '@/types';

function makeUser(role: UserRole): User {
  return { id: 1, email: 'a@b.com', full_name: 'Ada', role, college_id: 1, is_active: true, is_verified: true };
}

function renderRoute(user: User | null, isLoading: boolean, allowedRoles?: UserRole[]) {
  const value: AuthContextValue = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    login: vi.fn(),
    logout: vi.fn(),
    updateProfile: vi.fn(),
  };
  return render(
    <MemoryRouter initialEntries={['/secret']}>
      <AuthContext.Provider value={value}>
        <Routes>
          <Route path="/login" element={<div>login page</div>} />
          <Route element={<ProtectedRoute allowedRoles={allowedRoles} />}>
            <Route path="/secret" element={<div>secret content</div>} />
          </Route>
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

describe('ProtectedRoute', () => {
  it('redirects unauthenticated users to /login', () => {
    renderRoute(null, false);
    expect(screen.getByText('login page')).toBeInTheDocument();
  });

  it('shows loading state while auth resolves', () => {
    renderRoute(null, true);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders content for an authenticated user', () => {
    renderRoute(makeUser('STUDENT'), false);
    expect(screen.getByText('secret content')).toBeInTheDocument();
  });

  it('allows a user whose role is permitted', () => {
    renderRoute(makeUser('TPO'), false, ['TPO', 'ADMIN']);
    expect(screen.getByText('secret content')).toBeInTheDocument();
  });

  it('redirects a user whose role is not permitted', () => {
    renderRoute(makeUser('STUDENT'), false, ['ADMIN']);
    expect(screen.getByText('login page')).toBeInTheDocument();
  });
});
