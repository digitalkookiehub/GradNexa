import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ResumePage } from './ResumePage';
import { MAX_RESUME_BYTES } from '@/lib/resume';
import { resumeService } from '@/services/resumeService';
import { roadmapService } from '@/services/roadmapService';
import { makeAxiosError } from '@/test/helpers';
import type { Resume } from '@/types/resume';

vi.mock('@/services/resumeService', () => ({
  resumeService: { list: vi.fn(), upload: vi.fn(), remove: vi.fn(), analyze: vi.fn() },
}));
vi.mock('@/services/roadmapService', () => ({ roadmapService: { listRoles: vi.fn() } }));
vi.mock('@/services/jobService', () => ({ jobService: { list: vi.fn() } }));
import { jobService } from '@/services/jobService';

function makeResume(overrides: Partial<Resume> = {}): Resume {
  return {
    id: 1,
    original_filename: 'cv.pdf',
    content_type: 'application/pdf',
    size_bytes: 2048,
    page_count: 2,
    uploaded_at: '2026-01-01T00:00:00Z',
    has_text: true,
    text_length: 500,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/resume']}>
      <Routes>
        <Route path="/resume" element={<ResumePage />} />
        <Route path="/resume/:id/analysis" element={<p>analysis page</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

function pdf(name = 'new.pdf', size = 100): File {
  const f = new File(['x'], name, { type: 'application/pdf' });
  Object.defineProperty(f, 'size', { value: size });
  return f;
}

describe('ResumePage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(jobService.list).mockResolvedValue([]);
    vi.mocked(resumeService.list).mockResolvedValue([makeResume()]);
    vi.mocked(roadmapService.listRoles).mockResolvedValue([
      { id: 5, name: 'Backend Engineer', description: null, department_id: null, is_active: true, is_goal: false },
      { id: 6, name: 'Data Analyst', description: null, department_id: null, is_active: true, is_goal: true },
    ]);
  });

  it('shows disclaimers and the resume list', async () => {
    renderPage();
    expect(await screen.findByText('cv.pdf')).toBeInTheDocument();
    expect(screen.getByText(/not a readiness score/)).toBeInTheDocument();
    expect(screen.getByText(/keyword-based/)).toBeInTheDocument();
    expect(screen.getAllByText(/no OCR/i).length).toBeGreaterThan(0);
  });

  it('shows an empty state', async () => {
    vi.mocked(resumeService.list).mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText(/not uploaded a resume yet/)).toBeInTheDocument();
  });

  it('shows a load error', async () => {
    vi.mocked(resumeService.list).mockRejectedValue(makeAxiosError(500, 'boom'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
  });

  it('rejects wrong file types and oversize files client-side', async () => {
    const user = userEvent.setup({ applyAccept: false });
    renderPage();
    await screen.findByText('cv.pdf');
    const input = screen.getByLabelText('Resume file');
    await user.upload(input, new File(['x'], 'cv.txt', { type: 'text/plain' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/PDF or DOCX/);
    await user.upload(input, pdf('big.pdf', MAX_RESUME_BYTES + 1));
    expect(await screen.findByRole('alert')).toHaveTextContent(/larger/);
    expect(screen.getByRole('button', { name: 'Upload resume' })).toBeDisabled();
    expect(resumeService.upload).not.toHaveBeenCalled();
  });

  it('uploads a valid file and prepends it to the list', async () => {
    const user = userEvent.setup();
    vi.mocked(resumeService.upload).mockResolvedValue(makeResume({ id: 2, original_filename: 'new.pdf' }));
    renderPage();
    await screen.findByText('cv.pdf');
    await user.upload(screen.getByLabelText('Resume file'), pdf());
    await user.click(screen.getByRole('button', { name: 'Upload resume' }));
    expect(await screen.findByText('new.pdf', { selector: 'p' })).toBeInTheDocument();
    expect(resumeService.upload).toHaveBeenCalledTimes(1);
  });

  it.each([
    [413, /File too large/],
    [415, /Unsupported file type/],
    [422, /corrupt or password-protected/],
  ])('maps a %i upload error', async (status, pattern) => {
    const user = userEvent.setup();
    vi.mocked(resumeService.upload).mockRejectedValue(makeAxiosError(status, 'server says no'));
    renderPage();
    await screen.findByText('cv.pdf');
    await user.upload(screen.getByLabelText('Resume file'), pdf());
    await user.click(screen.getByRole('button', { name: 'Upload resume' }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(pattern);
    expect(alert).toHaveTextContent('server says no');
  });

  it('asks for in-page confirmation before deleting', async () => {
    const user = userEvent.setup();
    vi.mocked(resumeService.remove).mockResolvedValue(undefined);
    renderPage();
    await screen.findByText('cv.pdf');
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    expect(resumeService.remove).not.toHaveBeenCalled();
    const dialog = screen.getByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    await user.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Delete resume' }));
    await waitFor(() => expect(resumeService.remove).toHaveBeenCalledWith(1));
    await waitFor(() => expect(screen.queryByText('cv.pdf')).not.toBeInTheDocument());
  });

  it('sends role and job description in the analyze payload, goals listed first', async () => {
    const user = userEvent.setup();
    vi.mocked(resumeService.analyze).mockResolvedValue({} as never);
    renderPage();
    await screen.findByText('cv.pdf');
    await user.click(screen.getByRole('button', { name: 'Analyze' }));
    const select = screen.getByLabelText(/Target role/);
    expect(within(select).getByRole('group', { name: 'Your goals' })).toHaveTextContent('Data Analyst');
    await user.selectOptions(select, '5');
    await user.type(screen.getByLabelText(/Job description/), 'Need SQL');
    await user.click(screen.getByRole('button', { name: 'Run analysis' }));
    await waitFor(() => expect(resumeService.analyze).toHaveBeenCalledWith(1, { role_id: 5, jd_text: 'Need SQL' }));
    expect(await screen.findByText('analysis page')).toBeInTheDocument();
  });

  it('sends an empty payload when nothing is chosen and surfaces analyze errors', async () => {
    const user = userEvent.setup();
    vi.mocked(resumeService.analyze).mockRejectedValue(makeAxiosError(422, 'No text'));
    renderPage();
    await screen.findByText('cv.pdf');
    await user.click(screen.getByRole('button', { name: 'Analyze' }));
    await user.click(screen.getByRole('button', { name: 'Run analysis' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No text');
    expect(resumeService.analyze).toHaveBeenCalledWith(1, {});
  });

  it('warns and disables analysis when no text was extracted', async () => {
    vi.mocked(resumeService.list).mockResolvedValue([makeResume({ has_text: false, text_length: 0 })]);
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent(/No text could be extracted/);
    expect(screen.getByRole('button', { name: 'Analyze' })).toBeDisabled();
  });

  describe('job comparison', () => {
    const jobItem = {
      id: 7,
      company_id: 1,
      company_name: 'Acme',
      title: 'SDE I',
      role_id: null,
      role_name: null,
      status: 'OPEN',
      application_deadline: null,
      deadline_passed: false,
      has_eligibility_rule: false,
      eligibility_status: 'NO_RULE' as const,
    };

    it('sends job_id only and disables the pasted description when a job is chosen', async () => {
      const user = userEvent.setup();
      vi.mocked(jobService.list).mockResolvedValue([jobItem]);
      vi.mocked(resumeService.analyze).mockResolvedValue({} as never);
      renderPage();
      await screen.findByText('cv.pdf');
      await user.click(screen.getByRole('button', { name: 'Analyze' }));
      await screen.findByRole('option', { name: /SDE I/ });
      await user.selectOptions(screen.getByLabelText(/Compare with a job posting/), '7');
      expect(screen.getByLabelText(/Job description/)).toBeDisabled();
      await user.click(screen.getByRole('button', { name: 'Run analysis' }));
      await waitFor(() => expect(resumeService.analyze).toHaveBeenCalledWith(1, { job_id: 7 }));
    });

    it('disables the job select when a description is pasted and sends jd_text', async () => {
      const user = userEvent.setup();
      vi.mocked(jobService.list).mockResolvedValue([jobItem]);
      vi.mocked(resumeService.analyze).mockResolvedValue({} as never);
      renderPage();
      await screen.findByText('cv.pdf');
      await user.click(screen.getByRole('button', { name: 'Analyze' }));
      await user.type(screen.getByLabelText(/Job description/), 'Need SQL');
      expect(screen.getByLabelText(/Compare with a job posting/)).toBeDisabled();
      await user.click(screen.getByRole('button', { name: 'Run analysis' }));
      await waitFor(() => expect(resumeService.analyze).toHaveBeenCalledWith(1, { jd_text: 'Need SQL' }));
    });

    it('still lets the student analyze when the job list fails to load', async () => {
      const user = userEvent.setup();
      vi.mocked(jobService.list).mockRejectedValue(makeAxiosError(500, 'boom'));
      renderPage();
      await screen.findByText('cv.pdf');
      await user.click(screen.getByRole('button', { name: 'Analyze' }));
      expect(await screen.findByRole('alert')).toHaveTextContent('boom');
      expect(screen.getByLabelText(/Job description/)).toBeEnabled();
    });
  });
});
