import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { JobDetailPage } from './JobDetailPage';
import { jobService } from '@/services/jobService';
import { makeAxiosError } from '@/test/helpers';
import type { Gap } from '@/types';
import type { EligibilityCheck, JobDetail, JobSkillFit } from '@/types/jobs';

vi.mock('@/services/jobService', () => ({ jobService: { get: vi.fn(), eligibility: vi.fn(), skillFit: vi.fn() } }));

const BODY = 'Line one\n<script>alert(1)</script>\n<b>bold</b>';

const job: JobDetail = {
  id: 3,
  company: { id: 1, name: 'Acme', description: null, website: null },
  title: 'SDE I',
  body: BODY,
  role_id: null,
  role_name: null,
  status: 'OPEN',
  application_deadline: null,
  deadline_passed: false,
  skills: [{ skill_id: 1, skill_name: 'Python', required_level: 60, weight: 1 }],
  eligibility_criteria: null,
};

const check: EligibilityCheck = {
  job_id: 3,
  status: 'INCOMPLETE_DATA',
  criteria: [
    { key: 'cgpa', label: 'CGPA', required: '>= 7.5', actual: '8.1', result: 'MET' },
    { key: 'arrears', label: 'Arrears', required: '<= 0', actual: '2', result: 'NOT_MET' },
    { key: 'attendance', label: 'Attendance', required: '>= 75%', actual: null, result: 'UNKNOWN' },
    { key: 'graduation_year', label: 'Graduation year', required: '2026', actual: null, result: 'UNKNOWN' },
  ],
  custom_notes: ['Bring two ID proofs'],
  note: 'This is a check against configured criteria only.',
  evaluated_at: '2026-01-01T00:00:00Z',
};

function gap(id: number, name: string, priority: Gap['priority']): Gap {
  return { skill_id: id, skill_name: name, current: 40, required: 60, gap: 20, status: 'GAP', priority, recommended_action: `Practise ${name}` };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/jobs/3']}>
      <Routes>
        <Route path="/jobs/:id" element={<JobDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('JobDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(jobService.get).mockResolvedValue(job);
    vi.mocked(jobService.eligibility).mockResolvedValue(check);
  });

  it('renders the body as plain text without injecting markup', async () => {
    const { container } = renderPage();
    const body = await screen.findByTestId('job-body');
    expect(body.textContent).toBe(BODY);
    expect(body.children).toHaveLength(0);
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('b')).toBeNull();
  });

  it('shows the eligibility table with MET, NOT_MET and UNKNOWN as text, notes and missing-data links', async () => {
    renderPage();
    const section = (await screen.findByRole('heading', { name: 'Eligibility' })).closest('section') as HTMLElement;
    expect(await within(section).findByText('Met')).toBeInTheDocument();
    expect(within(section).getByText('Not met')).toBeInTheDocument();
    expect(within(section).getAllByText('Unknown')).toHaveLength(2);
    expect(within(section).getByTestId('eligibility-summary')).toHaveTextContent('You do not meet: Arrears');
    expect(within(section).getByRole('heading', { name: 'Not checked automatically' })).toBeInTheDocument();
    expect(within(section).getByText('Bring two ID proofs')).toBeInTheDocument();
    expect(within(section).getByText('This is a check against configured criteria only.')).toBeInTheDocument();
    const links = within(section).getAllByRole('link');
    expect(links.map((l) => l.getAttribute('href'))).toEqual(['/profile/academics', '/onboarding']);
    expect(within(section).getByText(/Missing data: your attendance is not recorded/)).toBeInTheDocument();
  });

  it('does not mention selection chances', async () => {
    renderPage();
    await screen.findByTestId('eligibility-summary');
    expect(document.body.textContent).not.toMatch(/will be selected|chance|probability/i);
  });

  it('keeps eligibility and skill fit in separate sections with separate headings', async () => {
    const user = userEvent.setup();
    const fit: JobSkillFit = { job_id: 3, rule_id: 1, rule_version: 1, overall: 55, coverage: 50, gaps: [gap(1, 'Python', 'HIGH')] };
    vi.mocked(jobService.skillFit).mockResolvedValue(fit);
    renderPage();
    const eligHeading = await screen.findByRole('heading', { name: 'Eligibility' });
    const fitHeading = screen.getByRole('heading', { name: 'Skill fit' });
    const eligSection = eligHeading.closest('section') as HTMLElement;
    const fitSection = fitHeading.closest('section') as HTMLElement;
    expect(eligSection).not.toBe(fitSection);
    expect(eligSection.contains(fitSection)).toBe(false);
    await user.click(screen.getByRole('button', { name: 'Check my skill fit' }));
    await screen.findByTestId('skill-fit-overall');
    expect(within(eligSection).queryByTestId('skill-fit-overall')).not.toBeInTheDocument();
    expect(within(fitSection).queryByTestId('eligibility-summary')).not.toBeInTheDocument();
    expect(within(fitSection).queryByText(/eligib/i)).not.toBeInTheDocument();
  });

  it('loads skill fit on demand and sorts HIGH priority gaps first', async () => {
    const user = userEvent.setup();
    vi.mocked(jobService.skillFit).mockResolvedValue({
      job_id: 3,
      rule_id: 1,
      rule_version: 1,
      overall: 55,
      coverage: 50,
      gaps: [gap(1, 'Low skill', 'LOW'), gap(2, 'High skill', 'HIGH')],
    });
    renderPage();
    await screen.findByTestId('eligibility-summary');
    expect(jobService.skillFit).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Check my skill fit' }));
    expect(await screen.findByTestId('skill-fit-overall')).toHaveTextContent('55');
    expect(screen.getByTestId('skill-fit-coverage')).toHaveTextContent('50%');
    const rows = screen.getAllByRole('row').map((r) => r.textContent ?? '');
    expect(rows.findIndex((t) => t.includes('High skill'))).toBeLessThan(rows.findIndex((t) => t.includes('Low skill')));
  });

  it('shows "Not enough evidence yet" when overall is null', async () => {
    const user = userEvent.setup();
    vi.mocked(jobService.skillFit).mockResolvedValue({ job_id: 3, rule_id: 1, rule_version: 1, overall: null, coverage: 0, gaps: [] });
    renderPage();
    await screen.findByTestId('eligibility-summary');
    await user.click(screen.getByRole('button', { name: 'Check my skill fit' }));
    expect(await screen.findByTestId('no-overall')).toHaveTextContent('Not enough evidence yet');
  });

  it('shows the 409 no-rule message', async () => {
    const user = userEvent.setup();
    vi.mocked(jobService.skillFit).mockRejectedValue(makeAxiosError(409, 'No active readiness rule configured'));
    renderPage();
    await screen.findByTestId('eligibility-summary');
    await user.click(screen.getByRole('button', { name: 'Check my skill fit' }));
    expect(await screen.findByTestId('no-rule')).toHaveTextContent('No active readiness rule configured');
  });

  it('shows a generic skill-fit error as an alert', async () => {
    const user = userEvent.setup();
    vi.mocked(jobService.skillFit).mockRejectedValue(makeAxiosError(500, 'Boom'));
    renderPage();
    await screen.findByTestId('eligibility-summary');
    await user.click(screen.getByRole('button', { name: 'Check my skill fit' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Boom');
  });

  it('links to the resume comparison', async () => {
    renderPage();
    expect(await screen.findByRole('link', { name: 'Compare my resume' })).toHaveAttribute('href', '/resume?job=3');
  });

  it('handles a missing job', async () => {
    vi.mocked(jobService.get).mockRejectedValue(makeAxiosError(404, 'Job not found'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('not found or is no longer open');
  });

  it('shows an eligibility error with retry', async () => {
    vi.mocked(jobService.eligibility).mockRejectedValue(makeAxiosError(500, 'Eligibility down'));
    renderPage();
    expect(await screen.findByText('Eligibility down')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });
});
