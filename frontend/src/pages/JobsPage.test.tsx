import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { JobsPage } from './JobsPage';
import { jobService } from '@/services/jobService';
import { makeAxiosError } from '@/test/helpers';
import type { EligibilityStatus, JobListItem } from '@/types/jobs';

vi.mock('@/services/jobService', () => ({ jobService: { list: vi.fn() } }));

function make(id: number, status: EligibilityStatus, overrides: Partial<JobListItem> = {}): JobListItem {
  return {
    id,
    company_id: 1,
    company_name: `Company ${id}`,
    title: `Job ${id}`,
    role_id: null,
    role_name: null,
    status: 'OPEN',
    application_deadline: null,
    deadline_passed: false,
    has_eligibility_rule: status !== 'NO_RULE',
    eligibility_status: status,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <JobsPage />
    </MemoryRouter>,
  );
}

describe('JobsPage', () => {
  beforeEach(() => vi.resetAllMocks());

  it('shows plain-language badge text per status', async () => {
    vi.mocked(jobService.list).mockResolvedValue([make(1, 'ELIGIBLE'), make(2, 'NOT_ELIGIBLE'), make(3, 'INCOMPLETE_DATA'), make(4, 'NO_RULE')]);
    renderPage();
    await screen.findByText('Job 1');
    const badges = screen.getAllByTestId('eligibility-badge').map((b) => b.textContent);
    expect(badges).toEqual(['Meets configured criteria', 'Does not meet configured criteria', 'Some data missing', 'No automatic criteria']);
  });

  it('flags a passed deadline and links to the detail page', async () => {
    vi.mocked(jobService.list).mockResolvedValue([make(1, 'ELIGIBLE', { deadline_passed: true, application_deadline: '2026-01-01T00:00:00Z' })]);
    renderPage();
    expect(await screen.findByText('Deadline passed')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Job 1' })).toHaveAttribute('href', '/jobs/1');
  });

  it('filters by eligibility status and by search text', async () => {
    const user = userEvent.setup();
    vi.mocked(jobService.list).mockResolvedValue([make(1, 'ELIGIBLE', { title: 'Backend' }), make(2, 'NOT_ELIGIBLE', { title: 'Frontend' })]);
    renderPage();
    await screen.findByText('Backend');
    await user.selectOptions(screen.getByLabelText('Eligibility'), 'NOT_ELIGIBLE');
    expect(screen.queryByText('Backend')).not.toBeInTheDocument();
    expect(screen.getByText('Frontend')).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Eligibility'), 'ALL');
    await user.type(screen.getByLabelText('Search'), 'back');
    expect(screen.getByText('Backend')).toBeInTheDocument();
    expect(screen.queryByText('Frontend')).not.toBeInTheDocument();
    await user.clear(screen.getByLabelText('Search'));
    await user.type(screen.getByLabelText('Search'), 'zzz');
    expect(screen.getByText('No postings match your filters.')).toBeInTheDocument();
  });

  it('shows an empty state', async () => {
    vi.mocked(jobService.list).mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText('There are no open job postings right now.')).toBeInTheDocument();
  });

  it('shows an error state as an alert', async () => {
    vi.mocked(jobService.list).mockRejectedValue(makeAxiosError(500, 'Server down'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('Server down');
    expect(screen.queryByText('There are no open job postings right now.')).not.toBeInTheDocument();
  });
});
