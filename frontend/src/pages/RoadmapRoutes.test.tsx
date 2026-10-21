import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '@/App';
import { AuthStub, makeUser } from '@/test/helpers';
import type { UserRole } from '@/types';

vi.mock('@/services/roadmapService', () => ({
  roadmapService: { listRoles: vi.fn(), getGoals: vi.fn(), getActivePlan: vi.fn(), history: vi.fn() },
}));
vi.mock('@/services/adminResourceService', () => ({ adminResourceService: { list: vi.fn() } }));
vi.mock('@/services/assessmentService', () => ({ assessmentService: { listSkills: vi.fn() } }));
vi.mock('@/services/studentService', () => ({ studentService: { getProfile: vi.fn(), listDepartments: vi.fn() } }));

import { adminResourceService } from '@/services/adminResourceService';
import { assessmentService } from '@/services/assessmentService';
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

describe('roadmap route gating and navigation', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(roadmapService.listRoles).mockResolvedValue([]);
    vi.mocked(roadmapService.getGoals).mockResolvedValue([]);
    vi.mocked(roadmapService.getActivePlan).mockResolvedValue(null);
    vi.mocked(roadmapService.history).mockResolvedValue([]);
    vi.mocked(adminResourceService.list).mockResolvedValue([]);
    vi.mocked(assessmentService.listSkills).mockResolvedValue([]);
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

  it('shows students Careers and Plan links and the explorer page', async () => {
    renderAt('STUDENT', '/careers');
    expect(await screen.findByRole('heading', { name: 'Career explorer' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Careers' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Plan' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Learning resources' })).not.toBeInTheDocument();
  });

  it('renders the plan page for students', async () => {
    renderAt('STUDENT', '/plan');
    expect(await screen.findByRole('heading', { name: '30-day plan' })).toBeInTheDocument();
  });

  it('renders plan history for students', async () => {
    renderAt('STUDENT', '/plan/progress');
    expect(await screen.findByRole('heading', { name: 'Plan history' })).toBeInTheDocument();
  });

  it('keeps admins and faculty out of student roadmap pages', () => {
    renderAt('ADMIN', '/careers');
    renderAt('FACULTY', '/plan');
    expect(roadmapService.listRoles).not.toHaveBeenCalled();
    expect(roadmapService.getActivePlan).not.toHaveBeenCalled();
  });

  it.each<UserRole>(['ADMIN', 'FACULTY'])('lets %s open learning resources and see the nav link', async (role) => {
    renderAt(role, '/admin/learning-resources');
    expect(await screen.findByRole('heading', { name: 'Learning resources', level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Learning resources' })).toBeInTheDocument();
  });

  it('keeps students out of learning resources admin', () => {
    renderAt('STUDENT', '/admin/learning-resources');
    expect(adminResourceService.list).not.toHaveBeenCalled();
  });
});
