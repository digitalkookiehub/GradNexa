import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '@/App';
import { AuthStub, makeUser } from '@/test/helpers';
import type { UserRole } from '@/types';

vi.mock('@/services/jobService', () => ({ jobService: { list: vi.fn(), get: vi.fn(), eligibility: vi.fn(), skillFit: vi.fn() } }));
vi.mock('@/services/studentService', () => ({ studentService: { getProfile: vi.fn(), listDepartments: vi.fn() } }));

import { jobService } from '@/services/jobService';
import { studentService } from '@/services/studentService';

function renderAt(role: UserRole, path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthStub user={makeUser(role)}>
        <App />
      </AuthStub>
    </MemoryRouter>,
  );
}

describe('jobs route gating', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(jobService.list).mockResolvedValue([]);
    vi.mocked(studentService.listDepartments).mockResolvedValue([]);
    vi.mocked(studentService.getProfile).mockResolvedValue({
      id: 1,
      user_id: 1,
      college_id: 1,
      department_id: 1,
      department_name: 'CSE',
      roll_number: 'R1',
      graduation_year: 2026,
      phone: '9876543210',
      profile_complete: true,
    });
  });

  it('shows students the Jobs link and page', async () => {
    renderAt('STUDENT', '/jobs');
    expect(await screen.findByRole('heading', { name: 'Jobs' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Jobs' })).toBeInTheDocument();
  });

  it.each<UserRole>(['ADMIN', 'FACULTY', 'TPO'])('keeps %s out of the student jobs page', (role) => {
    renderAt(role, '/jobs');
    expect(jobService.list).not.toHaveBeenCalled();
    expect(screen.queryByRole('heading', { name: 'Jobs' })).not.toBeInTheDocument();
  });

  it('does not render student job detail for a TPO', () => {
    renderAt('TPO', '/jobs/3');
    expect(jobService.get).not.toHaveBeenCalled();
  });
});
