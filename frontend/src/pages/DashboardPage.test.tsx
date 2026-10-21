import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DashboardPage } from './DashboardPage';
import { dashboardService } from '@/services/dashboardService';
import { makeAxiosError } from '@/test/helpers';
import type { StudentDashboard } from '@/types';

vi.mock('@/services/dashboardService', () => ({ dashboardService: { getStudent: vi.fn(), getPlacement: vi.fn() } }));

const base: StudentDashboard = {
  profile: { profile_complete: true, department_name: 'CSE', roll_number: 'R1' },
  rule_active: true,
  readiness: {
    general: { overall: 72.5, level: 'Advanced', coverage: 60, rule_version: 2, computed_at: '2026-01-01T00:00:00Z' },
    roles: [{ role_id: 3, role_name: 'Backend Dev', overall: null, level: null, coverage: 20, rule_version: 2, computed_at: '2026-01-01T00:00:00Z' }],
  },
  skills: [{ skill_id: 1, skill_name: 'Python', category_name: 'Tech', score: 80, evidence_count: 3 }],
  top_gaps: [
    { role_id: 3, role_name: 'Backend Dev', skill_id: 2, skill_name: 'SQL', current: 40, required: 70, gap: 30, status: 'GAP', priority: 'HIGH', recommended_action: 'Practise joins' },
  ],
  goals: [{ career_role_id: 3, role_name: 'Backend Dev', priority: 1 }],
  plan: { id: 1, role_id: 3, role_name: 'Backend Dev', status: 'ACTIVE', starts_on: null, progress: { done: 2, total: 4, percent: 50 } },
  recent_assessments: [{ attempt_id: 9, assessment_title: 'Python Basics', percentage: 88, submitted_at: '2026-01-02T00:00:00Z' }],
  not_implemented: ['resume_score', 'interview_progress'],
};

function renderPage() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );
}

describe('DashboardPage', () => {
  beforeEach(() => vi.resetAllMocks());

  it('renders the full state with coverage next to the partial score', async () => {
    vi.mocked(dashboardService.getStudent).mockResolvedValue(base);
    renderPage();
    expect(await screen.findByRole('heading', { name: 'Your dashboard' })).toBeInTheDocument();
    expect(screen.getByText(/CSE · Roll no\. R1/)).toBeInTheDocument();
    expect(screen.getByTestId('overall-score')).toHaveTextContent('72.5');
    expect(screen.getByText('Advanced')).toBeInTheDocument();
    expect(screen.getByTestId('coverage-line')).toHaveTextContent('Coverage 60%');
    expect(screen.getByTestId('coverage-line')).toHaveTextContent('rule v2');
    expect(screen.getByRole('list', { name: 'Role readiness' })).toHaveTextContent('Not enough evidence');
    expect(screen.getByRole('list', { name: 'Skill scores' })).toHaveTextContent('80 / 100 · 3 result(s)');
    expect(screen.getByText('High priority')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'See gaps for Backend Dev' })).toHaveAttribute('href', '/readiness/gaps?role=3');
    expect(screen.getByRole('list', { name: 'Plan progress' })).toHaveTextContent('50% (2 of 4 done)');
    expect(screen.getByRole('link', { name: 'View full history' })).toHaveAttribute('href', '/assessments/history');
    expect(screen.getByRole('link', { name: 'Python Basics' })).toBeInTheDocument();
    expect(screen.queryByText(/probability|chance/i)).not.toBeInTheDocument();
  });

  it('shows empty states with calls to action', async () => {
    vi.mocked(dashboardService.getStudent).mockResolvedValue({
      ...base,
      readiness: { general: null, roles: [] },
      skills: [],
      top_gaps: [],
      goals: [],
      plan: null,
      recent_assessments: [],
      not_implemented: [],
    });
    renderPage();
    expect(await screen.findByTestId('no-general')).toBeInTheDocument();
    expect(screen.getByTestId('no-skills')).toBeInTheDocument();
    expect(screen.getByTestId('no-gaps')).toBeInTheDocument();
    expect(screen.getByTestId('no-goals')).toBeInTheDocument();
    expect(screen.getByTestId('no-assessments')).toBeInTheDocument();
    expect(within(screen.getByTestId('no-plan')).getByRole('link', { name: /Choose a career/ })).toHaveAttribute('href', '/careers');
    expect(screen.queryByTestId('coming-later')).not.toBeInTheDocument();
  });

  it('renders resume and interview cards with data', async () => {
    vi.mocked(dashboardService.getStudent).mockResolvedValue({
      ...base,
      not_implemented: [],
      resume: { resume_id: 4, filename: 'cv.pdf', analyzed_at: '2026-01-03T00:00:00Z', role_name: 'Backend Dev', role_match_percent: 64 },
      interview: { completed_count: 2, latest: { role_name: 'Backend Dev', overall: 55, computed_at: '2026-01-04T00:00:00Z' } },
    });
    renderPage();
    const resume = await screen.findByTestId('resume-card');
    expect(resume).toHaveTextContent('cv.pdf');
    expect(resume).toHaveTextContent('64% keyword match for Backend Dev');
    expect(within(resume).getByRole('link', { name: 'Open my resume' })).toHaveAttribute('href', '/resume');
    const interview = screen.getByTestId('interview-card');
    expect(interview).toHaveTextContent('2 completed interviews');
    expect(interview).toHaveTextContent('55 / 100 coverage');
    expect(interview).toHaveTextContent(/not a prediction of hiring outcomes/);
    expect(within(interview).getByRole('link', { name: 'Open mock interviews' })).toHaveAttribute('href', '/interview');
    expect(screen.queryByTestId('coming-later')).not.toBeInTheDocument();
  });

  it('shows calls to action when resume and interview are null', async () => {
    vi.mocked(dashboardService.getStudent).mockResolvedValue({ ...base, not_implemented: [], resume: null, interview: { completed_count: 0, latest: null } });
    renderPage();
    expect(await screen.findByTestId('no-resume')).toBeInTheDocument();
    expect(within(screen.getByTestId('no-resume')).getByRole('link', { name: 'Upload your resume' })).toHaveAttribute('href', '/resume');
    expect(within(screen.getByTestId('no-interview')).getByRole('link', { name: 'Start a mock interview' })).toHaveAttribute('href', '/interview');
  });

  it('does not crash when an older backend omits the new fields', async () => {
    vi.mocked(dashboardService.getStudent).mockResolvedValue(base);
    renderPage();
    expect(await screen.findByTestId('no-resume')).toBeInTheDocument();
    expect(screen.getByTestId('no-interview')).toBeInTheDocument();
  });

  it('shows a notice when no readiness rule is active', async () => {
    vi.mocked(dashboardService.getStudent).mockResolvedValue({ ...base, rule_active: false, readiness: { general: null, roles: [] } });
    renderPage();
    expect(await screen.findByTestId('no-rule')).toHaveTextContent(/not been configured/);
  });

  it('shows not_implemented items as a labelled card with no values', async () => {
    vi.mocked(dashboardService.getStudent).mockResolvedValue(base);
    renderPage();
    const card = await screen.findByTestId('coming-later');
    expect(card).toHaveTextContent('Coming in a later phase');
    expect(card).toHaveTextContent('Resume score');
    expect(card).toHaveTextContent('Interview progress');
    expect(card).not.toHaveTextContent(/\d/);
  });

  it('shows the not-enough-evidence message when overall is null', async () => {
    vi.mocked(dashboardService.getStudent).mockResolvedValue({
      ...base,
      readiness: { general: { overall: null, level: null, coverage: 0, rule_version: 1, computed_at: '2026-01-01T00:00:00Z' }, roles: [] },
    });
    renderPage();
    expect(await screen.findByTestId('no-overall')).toHaveTextContent('Not enough evidence yet');
    expect(screen.queryByTestId('overall-score')).not.toBeInTheDocument();
  });

  it('shows an alert with retry on error', async () => {
    const user = userEvent.setup();
    vi.mocked(dashboardService.getStudent).mockRejectedValueOnce(makeAxiosError(500, 'boom')).mockResolvedValueOnce(base);
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByRole('heading', { name: 'Your dashboard' })).toBeInTheDocument();
  });
});
