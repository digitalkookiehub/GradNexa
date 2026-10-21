import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StudentGate } from './StudentGate';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { studentService } from '@/services/studentService';
import { AuthStub, makeUser } from '@/test/helpers';
import type { StudentProfile, UserRole } from '@/types';

vi.mock('@/services/studentService', () => ({ studentService: { getProfile: vi.fn() } }));

const profile: StudentProfile = {
  id: 1,
  user_id: 1,
  college_id: 1,
  department_id: 1,
  department_name: 'CSE',
  roll_number: 'R1',
  graduation_year: 2026,
  phone: '9876543210',
  profile_complete: true,
};

function renderApp(role: UserRole, path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthStub user={makeUser(role)}>
        <Routes>
          <Route path="/login" element={<div>login page</div>} />
          <Route element={<ProtectedRoute allowedRoles={['STUDENT']} />}>
            <Route path="/onboarding" element={<div>onboarding page</div>} />
          </Route>
          <Route element={<ProtectedRoute />}>
            <Route element={<StudentGate />}>
              <Route path="/profile" element={<div>profile page</div>} />
            </Route>
          </Route>
        </Routes>
      </AuthStub>
    </MemoryRouter>,
  );
}

describe('StudentGate', () => {
  beforeEach(() => vi.resetAllMocks());

  it('redirects a student with an incomplete profile from /profile to /onboarding', async () => {
    vi.mocked(studentService.getProfile).mockResolvedValue({ ...profile, profile_complete: false });
    renderApp('STUDENT', '/profile');
    expect(await screen.findByText('onboarding page')).toBeInTheDocument();
  });

  it('lets a student with a complete profile through', async () => {
    vi.mocked(studentService.getProfile).mockResolvedValue(profile);
    renderApp('STUDENT', '/profile');
    expect(await screen.findByText('profile page')).toBeInTheDocument();
  });

  it('does not call the student API for non-students', () => {
    renderApp('TPO', '/profile');
    expect(screen.getByText('profile page')).toBeInTheDocument();
    expect(studentService.getProfile).not.toHaveBeenCalled();
  });

  it('keeps non-students out of /onboarding', () => {
    renderApp('FACULTY', '/onboarding');
    expect(screen.getByText('login page')).toBeInTheDocument();
  });

  it('shows an error with retry when the profile cannot be loaded', async () => {
    vi.mocked(studentService.getProfile).mockRejectedValue(new Error('boom'));
    renderApp('STUDENT', '/profile');
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });
});
