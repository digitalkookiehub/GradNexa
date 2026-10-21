import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FacultyDashboardPage } from './FacultyDashboardPage';
import { facultyDashboardService } from '@/services/facultyDashboardService';
import type { FacultyDashboard, FacultyStudentRow } from '@/types';

vi.mock('@/services/facultyDashboardService', () => ({ facultyDashboardService: { get: vi.fn() } }));

function student(over: Partial<FacultyStudentRow>): FacultyStudentRow {
  return {
    student_id: 1,
    name: 'Asha',
    email: 'asha@x.edu',
    department_name: 'CSE',
    roll_number: 'R1',
    overall: 70,
    level: 'Intermediate',
    coverage: 60,
    high_priority_gap_count: 1,
    last_assessment_percentage: 80,
    last_assessment_at: '2026-01-01T00:00:00Z',
    needs_support: false,
    support_reasons: [],
    ...over,
  };
}

const base: FacultyDashboard = {
  generated_at: '2026-01-01T00:00:00Z',
  totals: { assigned_students: 3, with_readiness_score: 2, needing_support: 1 },
  students: [
    student({ student_id: 1, name: 'Chitra', overall: 40, needs_support: true, support_reasons: ['Overall below 50', 'No assessment in 30 days'] }),
    student({ student_id: 2, name: 'Asha', overall: 90 }),
    student({ student_id: 3, name: 'Bala', overall: null, level: null, coverage: null, last_assessment_percentage: null, last_assessment_at: null }),
  ],
  top_gaps: [{ skill_id: 1, skill_name: 'SQL', students_affected: 2, high_priority_students: 1 }],
  assessment_performance: [{ assessment_id: 1, title: 'Aptitude 1', attempts_submitted: 5, average_percentage: null }],
};

function rowNames(): string[] {
  const table = screen.getByRole('table', { name: 'Assigned students' });
  const names = ['Asha', 'Bala', 'Chitra'];
  return within(table)
    .getAllByRole('row')
    .slice(1)
    .map((r) => names.find((n) => (within(r).getAllByRole('rowheader')[0].textContent ?? '').startsWith(n)) ?? '?');
}

describe('FacultyDashboardPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(facultyDashboardService.get).mockResolvedValue(base);
  });

  it('shows reasons, the heuristic note, nulls as dashes and never probabilities', async () => {
    render(<FacultyDashboardPage />);
    expect(await screen.findByRole('heading', { name: 'Faculty dashboard' })).toBeInTheDocument();
    expect(await screen.findByText(/configured rule-based heuristic, not a prediction/)).toBeInTheDocument();
    const reasons = screen.getByRole('list', { name: 'Reasons for Chitra' });
    expect(reasons).toHaveTextContent('Overall below 50');
    expect(reasons).toHaveTextContent('No assessment in 30 days');
    const bala = screen.getByRole('row', { name: /Bala/ });
    expect(bala).toHaveTextContent('Not scored');
    expect(bala).toHaveTextContent('-');
    expect(screen.getByRole('row', { name: /Aptitude 1.*5.*-/ })).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /SQL/ })).toHaveTextContent('2');
    expect(screen.queryByText(/probability|chance/i)).not.toBeInTheDocument();
  });

  it('sorts by name, overall and needs-support', async () => {
    const user = userEvent.setup();
    render(<FacultyDashboardPage />);
    await screen.findByRole('table', { name: 'Assigned students' });
    expect(rowNames()).toEqual(['Asha', 'Bala', 'Chitra']);

    await user.click(screen.getByRole('button', { name: /^Overall/ }));
    expect(rowNames()).toEqual(['Chitra', 'Asha', 'Bala']);
    await user.click(screen.getByRole('button', { name: /^Overall/ }));
    expect(rowNames()).toEqual(['Asha', 'Chitra', 'Bala']);

    await user.click(screen.getByRole('button', { name: /^Needs support/ }));
    expect(rowNames()[0]).toBe('Chitra');
  });

  it('shows an empty state with no assigned students', async () => {
    vi.mocked(facultyDashboardService.get).mockResolvedValue({
      ...base,
      totals: { assigned_students: 0, with_readiness_score: 0, needing_support: 0 },
      students: [],
    });
    render(<FacultyDashboardPage />);
    expect(await screen.findByTestId('no-students')).toBeInTheDocument();
  });

  it('shows an alert on failure', async () => {
    vi.mocked(facultyDashboardService.get).mockRejectedValue(new Error('boom'));
    render(<FacultyDashboardPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
  });
});
