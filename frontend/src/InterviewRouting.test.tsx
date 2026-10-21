import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { AuthStub, makeUser } from '@/test/helpers';
import type { UserRole } from '@/types';

vi.mock('@/services/interviewService', () => ({ interviewService: { list: vi.fn(), start: vi.fn() } }));
vi.mock('@/services/adminInterviewService', () => ({ adminInterviewService: { list: vi.fn() } }));
vi.mock('@/services/roadmapService', () => ({ roadmapService: { listRoles: vi.fn() } }));
vi.mock('@/services/readinessService', () => ({ readinessService: { listRoles: vi.fn() } }));
vi.mock('@/services/assessmentService', () => ({ assessmentService: { listSkills: vi.fn() } }));
vi.mock('@/services/studentService', () => ({ studentService: { getProfile: vi.fn() } }));

import { adminInterviewService } from '@/services/adminInterviewService';
import { interviewService } from '@/services/interviewService';
import { readinessService } from '@/services/readinessService';
import { roadmapService } from '@/services/roadmapService';
import { assessmentService } from '@/services/assessmentService';
import { studentService } from '@/services/studentService';

function renderAt(path: string, role: UserRole) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthStub user={makeUser(role)}>
        <App />
      </AuthStub>
    </MemoryRouter>,
  );
}

describe('interview routes and navigation', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(interviewService.list).mockResolvedValue([]);
    vi.mocked(adminInterviewService.list).mockResolvedValue([]);
    vi.mocked(roadmapService.listRoles).mockResolvedValue([]);
    vi.mocked(readinessService.listRoles).mockResolvedValue([]);
    vi.mocked(assessmentService.listSkills).mockResolvedValue([]);
    vi.mocked(studentService.getProfile).mockResolvedValue({ profile_complete: true } as never);
  });

  it('lets students open /interview and shows the Interview nav link', async () => {
    renderAt('/interview', 'STUDENT');
    expect(await screen.findByRole('heading', { name: 'Mock interview' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Interview' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Interview questions' })).not.toBeInTheDocument();
  });

  it.each<UserRole>(['ADMIN', 'FACULTY'])('lets %s open the admin question bank', async (role) => {
    renderAt('/admin/interview-questions', role);
    expect(await screen.findByRole('heading', { name: 'Interview questions' })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Interview questions' }).length).toBeGreaterThan(0);
  });

  it('keeps students out of the admin page', async () => {
    renderAt('/admin/interview-questions', 'STUDENT');
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Interview questions' })).not.toBeInTheDocument());
    expect(adminInterviewService.list).not.toHaveBeenCalled();
  });

  it('keeps faculty out of the student interview page', async () => {
    renderAt('/interview', 'FACULTY');
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Mock interview' })).not.toBeInTheDocument());
    expect(interviewService.list).not.toHaveBeenCalled();
  });
});
