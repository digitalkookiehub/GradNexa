import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminJobsPage } from './AdminJobsPage';
import { adminJobService } from '@/services/adminJobService';
import { adminReadinessService } from '@/services/adminReadinessService';
import { makeAxiosError } from '@/test/helpers';
import type { AdminJobSummary, JobStatus } from '@/types/jobAdmin';

vi.mock('@/services/adminJobService', () => ({
  adminJobService: { listJobs: vi.fn(), listCompanies: vi.fn(), createJob: vi.fn(), publishJob: vi.fn(), closeJob: vi.fn() },
}));
vi.mock('@/services/adminReadinessService', () => ({ adminReadinessService: { listRoles: vi.fn() } }));

function job(id: number, status: JobStatus): AdminJobSummary {
  return {
    id,
    company_id: 1,
    company_name: 'Acme',
    title: `Job ${status}`,
    role_id: null,
    role_name: null,
    status,
    application_deadline: null,
    has_eligibility_rule: false,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminJobsPage />
    </MemoryRouter>,
  );
}

describe('AdminJobsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminJobService.listJobs).mockResolvedValue([job(1, 'DRAFT'), job(2, 'OPEN'), job(3, 'CLOSED')]);
    vi.mocked(adminJobService.listCompanies).mockResolvedValue([{ id: 1, name: 'Acme', description: null, website: null, is_active: true, job_count: 3 }]);
    vi.mocked(adminReadinessService.listRoles).mockResolvedValue([]);
  });

  it('shows lifecycle buttons per status', async () => {
    renderPage();
    expect(await screen.findByRole('button', { name: 'Publish job Job DRAFT' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Close job Job DRAFT' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Close job Job OPEN' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Publish job Job OPEN' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Publish job Job CLOSED' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Close job Job CLOSED' })).not.toBeInTheDocument();
  });

  it('publishes only after in-page confirmation', async () => {
    vi.mocked(adminJobService.publishJob).mockResolvedValue();
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Publish job Job DRAFT' }));
    expect(adminJobService.publishJob).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Confirm publish' }));
    expect(adminJobService.publishJob).toHaveBeenCalledWith(1);
  });

  it('closes after confirmation and surfaces a server error', async () => {
    vi.mocked(adminJobService.closeJob).mockRejectedValue(makeAxiosError(409, 'Only OPEN jobs can be closed'));
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Close job Job OPEN' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm close' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Only OPEN jobs can be closed');
  });

  it('filters by status through the service', async () => {
    renderPage();
    await screen.findByText('Job DRAFT');
    await userEvent.selectOptions(screen.getByLabelText('Filter by status'), 'OPEN');
    expect(adminJobService.listJobs).toHaveBeenLastCalledWith({ status: 'OPEN' });
  });

  it('shows the empty state', async () => {
    vi.mocked(adminJobService.listJobs).mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText('No jobs found.')).toBeInTheDocument();
  });

  it('creates a draft job and omits an unset deadline', async () => {
    vi.mocked(adminJobService.createJob).mockResolvedValue({ ...job(9, 'DRAFT'), body: 'b', created_by: 1, skills: [], eligibility: null });
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'New job' }));
    await userEvent.selectOptions(await screen.findByLabelText('Company'), '1');
    await userEvent.type(screen.getByLabelText('Job title'), 'SDE');
    await userEvent.type(screen.getByLabelText('Job description'), 'Build things');
    await userEvent.click(screen.getByRole('button', { name: 'Create job' }));
    expect(adminJobService.createJob).toHaveBeenCalledWith({ company_id: 1, title: 'SDE', body: 'Build things', role_id: null });
  });

  it('omits the role picker and role_id when roles cannot be listed (TPO)', async () => {
    vi.mocked(adminReadinessService.listRoles).mockRejectedValue(makeAxiosError(403, 'Forbidden'));
    vi.mocked(adminJobService.createJob).mockResolvedValue({ ...job(9, 'DRAFT'), body: 'b', created_by: 1, skills: [], eligibility: null });
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'New job' }));
    await userEvent.selectOptions(await screen.findByLabelText('Company'), '1');
    expect(await screen.findByTestId('role-unavailable')).toBeInTheDocument();
    expect(screen.queryByLabelText('Career role (optional)')).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Job title'), 'SDE');
    await userEvent.type(screen.getByLabelText('Job description'), 'Build things');
    await userEvent.click(screen.getByRole('button', { name: 'Create job' }));
    expect(adminJobService.createJob).toHaveBeenCalledWith({ company_id: 1, title: 'SDE', body: 'Build things' });
    expect(screen.queryByText('Could not load companies.')).not.toBeInTheDocument();
  });
});
