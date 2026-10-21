import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '@/App';
import { AuthStub, makeUser } from '@/test/helpers';
import type { UserRole } from '@/types';

vi.mock('@/services/resumeService', () => ({ resumeService: { list: vi.fn() } }));
vi.mock('@/services/roadmapService', () => ({ roadmapService: { listRoles: vi.fn() } }));
vi.mock('@/services/studentService', () => ({ studentService: { getProfile: vi.fn(), listDepartments: vi.fn() } }));

import { resumeService } from '@/services/resumeService';
import { roadmapService } from '@/services/roadmapService';
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

describe('resume route gating', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(resumeService.list).mockResolvedValue([]);
    vi.mocked(roadmapService.listRoles).mockResolvedValue([]);
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

  it('shows students the Resume link and page', async () => {
    renderAt('STUDENT', '/resume');
    expect(await screen.findByRole('heading', { name: 'Resume' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Resume' })).toBeInTheDocument();
  });

  it.each<UserRole>(['ADMIN', 'FACULTY', 'TPO'])('keeps %s out of the resume page', (role) => {
    renderAt(role, '/resume');
    expect(resumeService.list).not.toHaveBeenCalled();
    expect(screen.queryByRole('link', { name: 'Resume' })).not.toBeInTheDocument();
  });
});
