import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HodDashboardPage } from './HodDashboardPage';
import { hodDashboardService } from '@/services/hodDashboardService';
import { makeAxiosError } from '@/test/helpers';
import type { HodDashboard } from '@/types';

vi.mock('@/services/hodDashboardService', () => ({ hodDashboardService: { get: vi.fn() } }));

const base: HodDashboard = {
  generated_at: '2026-01-01T00:00:00Z',
  scope: { department_ids: [1, 2], department_names: ['CSE', 'ECE'] },
  rule: { id: 1, version: 2 },
  rule_versions_in_use: [2],
  totals: { students: 10, profile_complete: 8, with_readiness_score: 5, with_assessment_submitted: 6 },
  level_distribution: [
    { level: 'Advanced', count: 2 },
    { level: null, count: 5 },
  ],
  skill_heatmap: [
    { skill_id: 1, skill_name: 'SQL', category_name: 'Technical', students_assessed: 4, average_score: 72.5 },
    { skill_id: 2, skill_name: 'Excel', category_name: 'Technical', students_assessed: 0, average_score: null },
  ],
  career_role_distribution: [{ role_id: 1, role_name: 'Data Analyst', students: 3 }],
  assessment_trends: [{ month: '2026-01', submitted_attempts: 9, average_percentage: null }],
  training_priorities: [{ skill_id: 1, skill_name: 'SQL', students_affected: 4, high_priority_students: 2 }],
};

describe('HodDashboardPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(hodDashboardService.get).mockResolvedValue(base);
  });

  it('renders aggregates with heatmap numbers, Not scored and dashes', async () => {
    render(<HodDashboardPage />);
    const dist = await screen.findByRole('list', { name: 'Level distribution' });
    expect(dist).toHaveTextContent('Not scored');
    expect(dist).toHaveTextContent('5 student(s)');
    expect(screen.getByTestId('heat-1')).toHaveTextContent('72.5');
    expect(screen.getByTestId('heat-2')).toHaveTextContent('-');
    expect(screen.getByRole('list', { name: 'Career role distribution' })).toHaveTextContent('Data Analyst');
    expect(screen.getByRole('row', { name: /2026-01.*9.*-/ })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Training priorities' })).toBeInTheDocument();
    expect(screen.queryByTestId('mixed-versions')).not.toBeInTheDocument();
    expect(screen.queryByText(/@|probability|chance/i)).not.toBeInTheDocument();
  });

  it('uses the scope departments for the select and requests the filter', async () => {
    const user = userEvent.setup();
    render(<HodDashboardPage />);
    await screen.findByRole('list', { name: 'Level distribution' });
    expect(hodDashboardService.get).toHaveBeenLastCalledWith(null);
    await user.selectOptions(screen.getByLabelText('Department'), 'ECE');
    await waitFor(() => expect(hodDashboardService.get).toHaveBeenLastCalledWith(2));
    // The options remain those of the unfiltered scope.
    expect(screen.getByRole('option', { name: 'CSE' })).toBeInTheDocument();
  });

  it('hides the select with a single department', async () => {
    vi.mocked(hodDashboardService.get).mockResolvedValue({ ...base, scope: { department_ids: [1], department_names: ['CSE'] } });
    render(<HodDashboardPage />);
    await screen.findByRole('list', { name: 'Level distribution' });
    expect(screen.queryByLabelText('Department')).not.toBeInTheDocument();
  });

  it('notes mixed rule versions', async () => {
    vi.mocked(hodDashboardService.get).mockResolvedValue({ ...base, rule_versions_in_use: [1, 2] });
    render(<HodDashboardPage />);
    expect(await screen.findByTestId('mixed-versions')).toHaveTextContent(/v1, v2/);
  });

  it('shows a clear message when no department is assigned', async () => {
    vi.mocked(hodDashboardService.get).mockRejectedValue(makeAxiosError(403, 'No department assigned'));
    render(<HodDashboardPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/No department is assigned to your account/);
  });

  it('shows an access message for a department that is not assigned', async () => {
    vi.mocked(hodDashboardService.get).mockRejectedValue(makeAxiosError(403, 'Department not assigned to you'));
    render(<HodDashboardPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/do not have access to this department/);
  });
});
