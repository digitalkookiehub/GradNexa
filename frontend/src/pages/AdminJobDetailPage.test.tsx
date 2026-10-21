import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminJobDetailPage } from './AdminJobDetailPage';
import { adminJobService } from '@/services/adminJobService';
import { adminReadinessService } from '@/services/adminReadinessService';
import { assessmentService } from '@/services/assessmentService';
import { studentService } from '@/services/studentService';
import { makeAxiosError } from '@/test/helpers';
import type { AdminJob, JobStatus } from '@/types/jobAdmin';

vi.mock('@/services/adminJobService', () => ({
  adminJobService: {
    getJob: vi.fn(),
    updateJob: vi.fn(),
    deleteJob: vi.fn(),
    publishJob: vi.fn(),
    closeJob: vi.fn(),
    setJobSkills: vi.fn(),
    setEligibility: vi.fn(),
    deleteEligibility: vi.fn(),
  },
}));
vi.mock('@/services/adminReadinessService', () => ({ adminReadinessService: { listRoles: vi.fn() } }));
vi.mock('@/services/assessmentService', () => ({ assessmentService: { listSkills: vi.fn() } }));
vi.mock('@/services/studentService', () => ({ studentService: { listDepartments: vi.fn() } }));

function makeJob(status: JobStatus, overrides: Partial<AdminJob> = {}): AdminJob {
  return {
    id: 5,
    company_id: 1,
    company_name: 'Acme',
    title: 'SDE',
    role_id: 7,
    role_name: 'Backend Developer',
    status,
    application_deadline: null,
    has_eligibility_rule: false,
    body: 'Build things',
    created_by: 1,
    skills: [{ skill_id: 1, skill_name: 'Python', required_level: 60, weight: 1 }],
    eligibility: null,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/jobs/5']}>
      <Routes>
        <Route path="/admin/jobs/:id" element={<AdminJobDetailPage />} />
        <Route path="/admin/jobs" element={<div>Jobs list</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('AdminJobDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminJobService.getJob).mockResolvedValue(makeJob('DRAFT'));
    vi.mocked(adminReadinessService.listRoles).mockResolvedValue([]);
    vi.mocked(assessmentService.listSkills).mockResolvedValue([{ id: 1, name: 'Python', description: null, category_id: 1, category_name: 'Tech' }]);
    vi.mocked(studentService.listDepartments).mockResolvedValue([{ id: 1, name: 'CSE', code: 'CSE' }]);
  });

  it('shows a load error', async () => {
    vi.mocked(adminJobService.getJob).mockRejectedValue(makeAxiosError(404, 'Job not found'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('Job not found');
  });

  it('disables editing for CLOSED jobs and hides save buttons', async () => {
    vi.mocked(adminJobService.getJob).mockResolvedValue(makeJob('CLOSED'));
    renderPage();
    expect(await screen.findByText(/closed and can no longer be edited/)).toBeInTheDocument();
    expect(screen.getByLabelText('Job title')).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Save details' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Save skills' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Save eligibility rule' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Publish' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Close job' })).not.toBeInTheDocument();
  });

  it('offers publish and delete for DRAFT, close for OPEN', async () => {
    renderPage();
    expect(await screen.findByRole('button', { name: 'Publish' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete draft' })).toBeInTheDocument();
  });

  it('shows Close job for an OPEN job', async () => {
    vi.mocked(adminJobService.getJob).mockResolvedValue(makeJob('OPEN'));
    renderPage();
    expect(await screen.findByRole('button', { name: 'Close job' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete draft' })).not.toBeInTheDocument();
  });

  it('saves details with an explicit null deadline and role', async () => {
    vi.mocked(adminJobService.updateJob).mockResolvedValue(makeJob('DRAFT'));
    vi.mocked(adminReadinessService.listRoles).mockResolvedValue([{ id: 7, name: 'Backend Developer' } as never]);
    renderPage();
    await screen.findByLabelText('Job title');
    await userEvent.selectOptions(await screen.findByLabelText('Career role (optional)'), '');
    await userEvent.click(screen.getByRole('button', { name: 'Save details' }));
    expect(adminJobService.updateJob).toHaveBeenCalledWith(5, { title: 'SDE', body: 'Build things', application_deadline: null, role_id: null });
  });

  it('leaves role_id out of the update when the role list is forbidden (TPO)', async () => {
    vi.mocked(adminReadinessService.listRoles).mockRejectedValue(makeAxiosError(403, 'Forbidden'));
    vi.mocked(adminJobService.updateJob).mockResolvedValue(makeJob('DRAFT'));
    renderPage();
    expect(await screen.findByTestId('role-unavailable')).toHaveTextContent('Backend Developer');
    await userEvent.click(screen.getByRole('button', { name: 'Save details' }));
    expect(adminJobService.updateJob).toHaveBeenCalledWith(5, { title: 'SDE', body: 'Build things', application_deadline: null });
    expect(screen.queryByText(/Could not load/)).not.toBeInTheDocument();
  });

  it('saves skills as a bulk payload', async () => {
    vi.mocked(adminJobService.setJobSkills).mockResolvedValue([{ skill_id: 1, skill_name: 'Python', required_level: 80, weight: 1 }]);
    renderPage();
    const req = await screen.findByLabelText('Required level for Python');
    await userEvent.clear(req);
    await userEvent.type(req, '80');
    await userEvent.click(screen.getByRole('button', { name: 'Save skills' }));
    expect(adminJobService.setJobSkills).toHaveBeenCalledWith(5, [{ skill_id: 1, required_level: 80, weight: 1 }]);
  });

  it('saves the eligibility rule and shows the 422 server message on failure', async () => {
    vi.mocked(adminJobService.setEligibility).mockRejectedValue(makeAxiosError(422, 'cgpa_min requires cgpa_basis'));
    renderPage();
    await userEvent.click(await screen.findByLabelText('Maximum arrears'));
    await userEvent.type(screen.getByLabelText('Maximum arrears allowed'), '0');
    await userEvent.click(screen.getByRole('button', { name: 'Save eligibility rule' }));
    expect(adminJobService.setEligibility).toHaveBeenCalledWith(5, { max_arrears: 0 });
    expect(await screen.findByRole('alert')).toHaveTextContent('cgpa_min requires cgpa_basis');
  });

  it('deletes a draft after confirmation and returns to the list', async () => {
    vi.mocked(adminJobService.deleteJob).mockResolvedValue();
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Delete draft' }));
    expect(adminJobService.deleteJob).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));
    expect(await screen.findByText('Jobs list')).toBeInTheDocument();
  });

  it('summarises the saved rule without any probability wording', async () => {
    vi.mocked(adminJobService.getJob).mockResolvedValue(
      makeJob('DRAFT', {
        has_eligibility_rule: true,
        eligibility: {
          cgpa_min: 7.5,
          cgpa_basis: 'LATEST_SEMESTER',
          max_arrears: null,
          attendance_min: null,
          department_ids: [{ id: 1, name: 'CSE' }],
          graduation_years: [2026],
          custom_notes: ['Carry ID'],
        },
      }),
    );
    renderPage();
    const summary = await screen.findByRole('group', { name: 'Eligibility summary' });
    expect(summary).toHaveTextContent('Minimum CGPA 7.5 (latest semester)');
    expect(summary).toHaveTextContent('Departments: CSE');
    expect(summary).toHaveTextContent('Graduation years: 2026');
    expect(summary).toHaveTextContent('Carry ID');
    expect(summary).not.toHaveTextContent(/chance|probability/i);
  });
});
