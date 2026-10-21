import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ReadinessPage } from './ReadinessPage';
import { readinessService } from '@/services/readinessService';
import { makeAxiosError } from '@/test/helpers';
import type { ReadinessResult } from '@/types';

vi.mock('@/services/readinessService', () => ({
  readinessService: { listRoles: vi.fn(), getLatest: vi.fn(), history: vi.fn(), compute: vi.fn() },
}));

function makeResult(overrides: Partial<ReadinessResult> = {}): ReadinessResult {
  return {
    id: 1,
    student_id: 1,
    role_id: null,
    role_name: null,
    rule_id: 3,
    rule_version: 2,
    overall: 72.5,
    level: 'Strong',
    coverage: 60,
    category_scores: [{ category_id: 1, category_name: 'Technical', weight: 50, score: 80, evidence_count: 3 }],
    evidence: [{ skill_id: 1, skill_name: 'Python', category_name: 'Technical', score: 80, evidence_count: 3, last_result_id: 9 }],
    gaps: [],
    computed_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ReadinessPage />
    </MemoryRouter>,
  );
}

describe('ReadinessPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(readinessService.listRoles).mockResolvedValue([
      { id: 5, department_id: null, name: 'Backend Engineer', description: null, is_active: true },
    ]);
    vi.mocked(readinessService.history).mockResolvedValue([]);
  });

  it('shows score, API level text, coverage and rule version', async () => {
    vi.mocked(readinessService.getLatest).mockResolvedValue(makeResult());
    renderPage();
    expect(await screen.findByTestId('overall-score')).toHaveTextContent('72.5');
    expect(screen.getByTestId('level')).toHaveTextContent('Strong');
    expect(screen.getByTestId('coverage-value')).toHaveTextContent('60%');
    expect(screen.getByText(/Rule version 2/)).toBeInTheDocument();
    expect(screen.getByText(/partial evidence/)).toBeInTheDocument();
    expect(screen.getByText('3 result(s)', { selector: 'td' })).toBeInTheDocument();
    expect(screen.queryByText(/probab|chance/i)).not.toBeInTheDocument();
  });

  it('shows Not enough evidence yet with a link to assessments when overall is null', async () => {
    vi.mocked(readinessService.getLatest).mockResolvedValue(makeResult({ overall: null, level: null, coverage: 0 }));
    renderPage();
    expect(await screen.findByText('Not enough evidence yet')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go to assessments' })).toHaveAttribute('href', '/assessments');
    expect(screen.queryByTestId('overall-score')).not.toBeInTheDocument();
    expect(screen.getByTestId('coverage-value')).toHaveTextContent('0%');
  });

  it('prompts to compute when nothing has been computed (404)', async () => {
    vi.mocked(readinessService.getLatest).mockRejectedValue(makeAxiosError(404, 'No readiness result'));
    renderPage();
    expect(await screen.findByTestId('not-computed')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows a clear message when no rule is configured (409)', async () => {
    vi.mocked(readinessService.getLatest).mockRejectedValue(makeAxiosError(404, 'none'));
    vi.mocked(readinessService.compute).mockRejectedValue(makeAxiosError(409, 'No active readiness rule configured'));
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Compute / refresh' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No readiness rule is configured yet');
  });

  it('computes for the selected role and refreshes history', async () => {
    vi.mocked(readinessService.getLatest).mockRejectedValue(makeAxiosError(404, 'none'));
    vi.mocked(readinessService.compute).mockResolvedValue(makeResult({ id: 2, role_id: 5, role_name: 'Backend Engineer' }));
    vi.mocked(readinessService.history).mockResolvedValueOnce([]).mockResolvedValue([makeResult({ id: 2 })]);
    renderPage();
    await screen.findByTestId('not-computed');
    await screen.findByRole('option', { name: 'Backend Engineer' });
    await userEvent.selectOptions(screen.getByLabelText('Career role'), '5');
    await screen.findByTestId('not-computed');
    await userEvent.click(screen.getByRole('button', { name: 'Compute / refresh' }));
    expect(await screen.findByTestId('overall-score')).toBeInTheDocument();
    expect(readinessService.compute).toHaveBeenCalledWith(5);
    const history = await screen.findByRole('list', { name: 'Readiness history' });
    expect(within(history).getByText(/rule v2/)).toBeInTheDocument();
  });

  it('shows an error alert when loading fails', async () => {
    vi.mocked(readinessService.getLatest).mockRejectedValue(new Error('boom'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
  });
});
