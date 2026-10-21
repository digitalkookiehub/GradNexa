import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AppLayout } from './AppLayout';
import { AuthContext, type AuthContextValue } from '@/context/auth-context';
import { makeUser } from '@/test/helpers';
import type { UserRole } from '@/types';

function renderAs(role: UserRole, logout = vi.fn().mockResolvedValue(undefined)) {
  const value: AuthContextValue = {
    user: makeUser(role),
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout,
    updateProfile: vi.fn(),
  };
  render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={['/jobs']}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/jobs" element={<p>jobs page</p>} />
            <Route path="/assessments" element={<p>assessments page</p>} />
          </Route>
          <Route path="/login" element={<p>login page</p>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
  return { logout };
}

const labels = (nav: HTMLElement): string[] => within(nav).getAllByRole('link').map((a) => a.textContent ?? '');

describe('AppLayout (left sidebar)', () => {
  it('puts every admin link in a grouped left sidebar', () => {
    renderAs('ADMIN');
    const nav = screen.getByRole('navigation', { name: 'Main' });
    expect(nav.closest('aside')).not.toBeNull();
    for (const heading of ['Placement', 'Assessment content', 'College setup', 'Knowledge', 'Help']) {
      expect(within(nav).getByRole('heading', { name: heading })).toBeInTheDocument();
    }
    expect(labels(nav)).toEqual([
      'Placement dashboard',
      'Companies',
      'Jobs',
      'Assessments',
      'Question bank',
      'Learning resources',
      'Interview questions',
      'Users and students',
      'Skills',
      'Readiness rules',
      'Career roles',
      'HOD assignments',
      'Knowledge base',
      'MCP tools',
      'Knowledge search',
      'User guide',
    ]);
  });

  it('shows the student links and none of the staff ones', () => {
    renderAs('STUDENT');
    const nav = screen.getByRole('navigation', { name: 'Main' });
    expect(labels(nav)).toEqual([
      'Dashboard',
      'Assistant',
      'Profile',
      'Academics',
      'Projects & Certifications',
      'Assessments',
      'History',
      'Readiness',
      'Skill gaps',
      'Careers',
      'Plan',
      'Interview',
      'Resume',
      'Jobs',
      'Knowledge',
    ]);
    expect(within(nav).queryByRole('link', { name: 'User guide' })).toBeNull();
  });

  it.each<[UserRole, string[]]>([
    ['TPO', ['Placement dashboard', 'Companies', 'Jobs', 'Profile', 'Knowledge search']],
    ['HOD', ['HOD dashboard', 'Profile', 'Knowledge search']],
    ['FACULTY', ['Faculty dashboard', 'Assessments', 'Question bank', 'Learning resources', 'Interview questions', 'Knowledge base', 'Knowledge search']],
  ])('shows the right links for %s', (role, expected) => {
    renderAs(role);
    expect(labels(screen.getByRole('navigation', { name: 'Main' }))).toEqual(expected);
  });

  it('highlights the current page', () => {
    renderAs('STUDENT');
    expect(screen.getByRole('link', { name: 'Jobs' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Assessments' })).not.toHaveAttribute('aria-current');
  });

  it('shows the signed-in user and logs out to the login page', async () => {
    const { logout } = renderAs('ADMIN');
    expect(screen.getByText('Ada')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Log out' }));
    expect(logout).toHaveBeenCalledTimes(1);
    expect(await screen.findByText('login page')).toBeInTheDocument();
  });

  it('has a menu button for small screens that toggles the sidebar and closes after choosing a page', async () => {
    renderAs('STUDENT');
    const toggle = screen.getByRole('button', { name: /Menu/ });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(toggle);
    expect(screen.getByRole('button', { name: /Close menu/ })).toHaveAttribute('aria-expanded', 'true');
    await userEvent.click(screen.getByRole('link', { name: 'Assessments' }));
    expect(await screen.findByText('assessments page')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Menu/ })).toHaveAttribute('aria-expanded', 'false');
  });
});
