import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PlacementDashboardPage } from './PlacementDashboardPage';
import { dashboardService } from '@/services/dashboardService';
import { placementAnalyticsService } from '@/services/placementAnalyticsService';
import { studentService } from '@/services/studentService';
import type { PlacementAnalytics, PlacementDashboard } from '@/types';

vi.mock('@/services/dashboardService', () => ({ dashboardService: { getStudent: vi.fn(), getPlacement: vi.fn() } }));
vi.mock('@/services/placementAnalyticsService', () => ({ placementAnalyticsService: { get: vi.fn() } }));
vi.mock('@/services/studentService', () => ({ studentService: { listDepartments: vi.fn() } }));

const base: PlacementDashboard = {
  generated_at: '2026-01-01T00:00:00Z',
  scope: { department_id: null, department_name: null },
  rule: { id: 1, version: 2 },
  rule_versions_in_use: [2],
  totals: { students: 10, profile_complete: 8, with_readiness_score: 5, with_assessment_submitted: 6 },
  level_distribution: [
    { level: 'Advanced', count: 2 },
    { level: null, count: 5 },
  ],
  departments: [
    { department_id: 1, department_name: 'CSE', students: 6, scored: 3, avg_overall: 61.2, avg_coverage: 50 },
    { department_id: 2, department_name: 'ECE', students: 4, scored: 0, avg_overall: null, avg_coverage: null },
  ],
  top_gaps: [{ skill_id: 1, skill_name: 'SQL', students_affected: 4, high_priority_students: 2 }],
  assessment_participation: { published_assessments: 3, students_with_attempts: 6, submitted_attempts: 9 },
};

const analytics: PlacementAnalytics = {
  generated_at: '2026-01-01T00:00:00Z',
  scope: { department_id: null, department_name: null },
  role_readiness: [{ role_id: 1, role_name: 'Data Analyst', students_with_goal: 7, students_scored: 4, average_overall: 55.5, average_coverage: null }],
  company_eligibility: [{ job_id: 1, job_title: 'SDE Intern', company_name: 'Acme', eligible: 3, not_eligible: 2, incomplete_data: 4, no_rule_students: 1 }],
  progress_trends: [{ month: '2026-01', students_scored: 4, average_overall: 48 }],
};

describe('PlacementDashboardPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(studentService.listDepartments).mockResolvedValue([
      { id: 1, name: 'CSE', code: 'CSE' },
      { id: 2, name: 'ECE', code: 'ECE' },
    ]);
    vi.mocked(dashboardService.getPlacement).mockResolvedValue(base);
    vi.mocked(placementAnalyticsService.get).mockResolvedValue(analytics);
  });

  it('renders tiles, Not scored label, tables with dashes for null', async () => {
    render(<PlacementDashboardPage />);
    expect(await screen.findByRole('heading', { name: 'Placement dashboard' })).toBeInTheDocument();
    const dist = await screen.findByRole('list', { name: 'Level distribution' });
    expect(dist).toHaveTextContent('Not scored');
    expect(dist).toHaveTextContent('5 student(s)');
    expect(dist).toHaveTextContent('Advanced');
    expect(screen.getByRole('row', { name: /ECE.*-/ })).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /CSE.*61\.2/ })).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /SQL/ })).toHaveTextContent('4');
    expect(screen.getByText('Published assessments')).toBeInTheDocument();
    expect(screen.queryByTestId('mixed-versions')).not.toBeInTheDocument();
    expect(screen.queryByText(/probability|chance/i)).not.toBeInTheDocument();
  });

  it('changing the department filter changes the request', async () => {
    const user = userEvent.setup();
    render(<PlacementDashboardPage />);
    await screen.findByRole('list', { name: 'Level distribution' });
    expect(dashboardService.getPlacement).toHaveBeenLastCalledWith(null);
    await screen.findByRole('option', { name: 'ECE' });
    await user.selectOptions(screen.getByLabelText('Department'), 'ECE');
    await waitFor(() => expect(dashboardService.getPlacement).toHaveBeenLastCalledWith(2));
  });

  it('refresh refetches', async () => {
    const user = userEvent.setup();
    render(<PlacementDashboardPage />);
    await screen.findByRole('list', { name: 'Level distribution' });
    await user.click(screen.getByRole('button', { name: 'Refresh' }));
    await waitFor(() => expect(dashboardService.getPlacement).toHaveBeenCalledTimes(2));
  });

  it('notes mixed rule versions', async () => {
    vi.mocked(dashboardService.getPlacement).mockResolvedValue({ ...base, rule_versions_in_use: [1, 2] });
    render(<PlacementDashboardPage />);
    expect(await screen.findByTestId('mixed-versions')).toHaveTextContent(/different rule versions \(v1, v2\)/);
  });

  it('shows an empty state for zero students', async () => {
    vi.mocked(dashboardService.getPlacement).mockResolvedValue({
      ...base,
      totals: { students: 0, profile_complete: 0, with_readiness_score: 0, with_assessment_submitted: 0 },
      level_distribution: [],
      departments: [],
      top_gaps: [],
    });
    render(<PlacementDashboardPage />);
    expect(await screen.findByTestId('no-students')).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Level distribution' })).not.toBeInTheDocument();
  });

  it('shows an alert on failure', async () => {
    vi.mocked(dashboardService.getPlacement).mockRejectedValue(new Error('x'));
    render(<PlacementDashboardPage />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('renders the analytics section with separate eligibility columns and dashes', async () => {
    render(<PlacementDashboardPage />);
    expect(await screen.findByRole('heading', { name: 'Analytics' })).toBeInTheDocument();
    expect(await screen.findByText('Eligibility (separate from readiness)')).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /Data Analyst.*7.*4.*55\.5.*-/ })).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /SDE Intern.*Acme.*3.*2.*4.*1/ })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'No criteria' })).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /2026-01.*4.*48/ })).toBeInTheDocument();
  });

  it('passes the department filter to analytics', async () => {
    const user = userEvent.setup();
    render(<PlacementDashboardPage />);
    await screen.findByRole('option', { name: 'ECE' });
    await user.selectOptions(screen.getByLabelText('Department'), 'ECE');
    await waitFor(() => expect(placementAnalyticsService.get).toHaveBeenLastCalledWith(2));
  });

  it('isolates an analytics failure from the rest of the page', async () => {
    vi.mocked(placementAnalyticsService.get).mockRejectedValue(new Error('analytics down'));
    render(<PlacementDashboardPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('analytics down');
    expect(screen.getByRole('list', { name: 'Level distribution' })).toBeInTheDocument();
    expect(screen.getAllByRole('alert')).toHaveLength(1);
  });
});
