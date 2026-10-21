import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '@/App';
import { AuthStub, makeUser } from '@/test/helpers';
import type { UserRole } from '@/types';

vi.mock('@/services/adminJobService', () => ({
  adminJobService: { listJobs: vi.fn(), listCompanies: vi.fn() },
}));
vi.mock('@/services/adminReadinessService', () => ({ adminReadinessService: { listRoles: vi.fn() } }));
vi.mock('@/services/dashboardService', () => ({ dashboardService: { getPlacement: vi.fn() } }));
vi.mock('@/services/studentService', () => ({ studentService: { getProfile: vi.fn(), listDepartments: vi.fn() } }));

import { adminJobService } from '@/services/adminJobService';
import { adminReadinessService } from '@/services/adminReadinessService';
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

describe('admin jobs route gating and navigation', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminJobService.listJobs).mockResolvedValue([]);
    vi.mocked(adminJobService.listCompanies).mockResolvedValue([]);
    vi.mocked(adminReadinessService.listRoles).mockResolvedValue([]);
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

  it.each<UserRole>(['TPO', 'ADMIN'])('lets %s open the jobs admin page and see nav links', async (role) => {
    renderAt(role, '/admin/jobs');
    expect(await screen.findByRole('heading', { name: 'Jobs' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Companies' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Jobs' })).toBeInTheDocument();
  });

  it('lets TPO open the companies page', async () => {
    renderAt('TPO', '/admin/companies');
    expect(await screen.findByRole('heading', { name: 'Companies' })).toBeInTheDocument();
  });

  it.each<UserRole>(['STUDENT', 'FACULTY'])('blocks %s from the admin jobs and companies pages', (role) => {
    renderAt(role, '/admin/jobs');
    expect(screen.queryByRole('heading', { name: 'Jobs' })).not.toBeInTheDocument();
    expect(adminJobService.listJobs).not.toHaveBeenCalled();
  });

  it.each<UserRole>(['STUDENT', 'FACULTY'])('blocks %s from /admin/companies', (role) => {
    renderAt(role, '/admin/companies');
    expect(screen.queryByRole('heading', { name: 'Companies' })).not.toBeInTheDocument();
    expect(adminJobService.listCompanies).not.toHaveBeenCalled();
  });
});
