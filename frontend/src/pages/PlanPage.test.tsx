import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PlanPage } from './PlanPage';
import { roadmapService } from '@/services/roadmapService';
import { makeAxiosError } from '@/test/helpers';
import type { ExplorerRole, Plan, ReassessResult } from '@/types';

vi.mock('@/services/roadmapService', () => ({
  roadmapService: {
    getActivePlan: vi.fn(),
    listRoles: vi.fn(),
    getGoals: vi.fn(),
    generatePlan: vi.fn(),
    updateItem: vi.fn(),
    reassess: vi.fn(),
  },
}));

function makePlan(): Plan {
  return {
    id: 1,
    role_id: 4,
    role_name: 'Backend Engineer',
    status: 'ACTIVE',
    starts_on: '2026-02-01',
    duration_days: 30,
    skills_per_week: 2,
    baseline: { readiness_score_id: 7, overall: 55, level: 'Developing', rule_version: 1, computed_at: '2026-02-01T00:00:00Z' },
    weeks: [
      {
        week: 1,
        items: [
          {
            id: 11,
            week: 1,
            position: 1,
            kind: 'LEARN',
            skill_id: 1,
            skill_name: 'Python',
            resource: { id: 3, title: 'Python Tutorial', url: 'https://example.com/py' },
            task: 'Learn Python basics',
            status: 'TODO',
            completed_at: null,
          },
          {
            id: 12,
            week: 1,
            position: 2,
            kind: 'LEARN',
            skill_id: 2,
            skill_name: 'SQL',
            resource: null,
            task: 'Learn SQL joins',
            status: 'DONE',
            completed_at: '2026-02-02T00:00:00Z',
          },
        ],
      },
      { week: 2, items: [] },
      { week: 3, items: [] },
      { week: 4, items: [] },
    ],
    unscheduled_skills: [{ skill_id: 9, skill_name: 'Docker', gap: 30 }],
    progress: { done: 1, total: 2, percent: 50 },
  };
}

const roles: ExplorerRole[] = [
  { id: 4, department_id: null, name: 'Backend Engineer', description: null, is_active: true, is_goal: true },
  { id: 5, department_id: null, name: 'Data Analyst', description: null, is_active: true, is_goal: false },
];

function renderPage(path = '/plan') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <PlanPage />
    </MemoryRouter>,
  );
}

describe('PlanPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(roadmapService.listRoles).mockResolvedValue(roles);
    vi.mocked(roadmapService.getGoals).mockResolvedValue([{ career_role_id: 4, role_name: 'Backend Engineer', priority: 1 }]);
    vi.mocked(roadmapService.getActivePlan).mockResolvedValue(makePlan());
  });

  it('renders four weeks, baseline, progress, resource link, no-resource task and unscheduled notice', async () => {
    renderPage();
    expect(await screen.findByRole('heading', { name: 'Week 1' })).toBeInTheDocument();
    for (const w of [2, 3, 4]) expect(screen.getByRole('heading', { name: `Week ${w}` })).toBeInTheDocument();
    expect(screen.getByTestId('baseline')).toHaveTextContent('55 (Developing)');
    expect(screen.getByTestId('progress-text')).toHaveTextContent('1 of 2 done (50%)');
    const link = screen.getByRole('link', { name: 'Python Tutorial' });
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    const noResource = screen.getByTestId('plan-item-12');
    expect(within(noResource).getByText(/No approved learning resource is configured/)).toBeInTheDocument();
    expect(screen.getByTestId('unscheduled')).toHaveTextContent('Docker');
    expect(screen.queryByText(/probab|chance/i)).not.toBeInTheDocument();
  });

  it('updates status optimistically and keeps the server result', async () => {
    vi.mocked(roadmapService.updateItem).mockResolvedValue({ ...makePlan().weeks[0].items[0], status: 'DONE', completed_at: '2026-02-03T00:00:00Z' });
    renderPage();
    await userEvent.selectOptions(await screen.findByLabelText('Status for Learn Python basics'), 'DONE');
    expect(roadmapService.updateItem).toHaveBeenCalledWith(11, 'DONE');
    expect(await screen.findByText('2 of 2 done (100%)')).toBeInTheDocument();
  });

  it('rolls back the status and shows an alert when the update fails', async () => {
    let reject: (e: unknown) => void = () => undefined;
    vi.mocked(roadmapService.updateItem).mockReturnValue(
      new Promise((_, rej) => {
        reject = rej;
      }),
    );
    renderPage();
    const select = await screen.findByLabelText('Status for Learn Python basics');
    await userEvent.selectOptions(select, 'DONE');
    expect(screen.getByTestId('progress-text')).toHaveTextContent('2 of 2 done');
    expect(select).toHaveValue('DONE');
    reject(makeAxiosError(500, 'Server exploded'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Server exploded');
    expect(screen.getByLabelText('Status for Learn Python basics')).toHaveValue('TODO');
    expect(screen.getByTestId('progress-text')).toHaveTextContent('1 of 2 done (50%)');
  });

  it('shows the 409 message when generating without computed readiness', async () => {
    vi.mocked(roadmapService.getActivePlan).mockResolvedValue(null);
    vi.mocked(roadmapService.generatePlan).mockRejectedValue(makeAxiosError(409, 'Compute readiness for this role first'));
    renderPage('/plan?role=5');
    expect(await screen.findByTestId('no-plan')).toBeInTheDocument();
    expect(screen.getByLabelText('Role')).toHaveValue('5');
    await userEvent.selectOptions(screen.getByLabelText('Skills per week'), '3');
    await userEvent.click(screen.getByRole('button', { name: 'Generate 30-day plan' }));
    expect(roadmapService.generatePlan).toHaveBeenCalledWith({ role_id: 5, skills_per_week: 3 });
    expect(await screen.findByRole('alert')).toHaveTextContent('Compute readiness for this role first');
  });

  it('defaults the role picker to the first goal and shows the generated plan', async () => {
    vi.mocked(roadmapService.getActivePlan).mockResolvedValue(null);
    vi.mocked(roadmapService.generatePlan).mockResolvedValue(makePlan());
    renderPage();
    expect(await screen.findByLabelText('Role')).toHaveValue('4');
    await userEvent.click(screen.getByRole('button', { name: 'Generate 30-day plan' }));
    expect(await screen.findByRole('heading', { name: 'Week 1' })).toBeInTheDocument();
  });

  it('asks for confirmation before generating over an active plan', async () => {
    vi.mocked(roadmapService.generatePlan).mockResolvedValue(makePlan());
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Generate a new plan' }));
    await userEvent.click(screen.getByRole('button', { name: 'Generate 30-day plan' }));
    expect(roadmapService.generatePlan).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Generate new plan' }));
    expect(roadmapService.generatePlan).toHaveBeenCalledWith({ role_id: 4, skills_per_week: 2 });
  });

  it('shows the reassess comparison with a rule-version note', async () => {
    const result: ReassessResult = {
      plan_id: 1,
      baseline: { overall: 55, level: 'Developing', rule_version: 1 },
      current: {
        id: 9,
        student_id: 1,
        role_id: 4,
        role_name: 'Backend Engineer',
        rule_id: 2,
        rule_version: 2,
        overall: 65,
        level: 'Strong',
        coverage: 80,
        category_scores: [],
        evidence: [],
        gaps: [],
        computed_at: '2026-02-10T00:00:00Z',
      },
      overall_delta: 10,
      rule_version_changed: true,
      skill_changes: [{ skill_id: 1, skill_name: 'Python', before: 40, after: 60, delta: 20 }],
    };
    vi.mocked(roadmapService.reassess).mockResolvedValue(result);
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Refresh readiness (reassess)' }));
    expect(await screen.findByTestId('reassess-delta')).toHaveTextContent('+10');
    expect(screen.getByTestId('rule-version-note')).toHaveTextContent('version 1 to version 2');
    const row = screen.getByRole('cell', { name: 'Python' }).closest('tr');
    expect(row).not.toBeNull();
    expect(row).toHaveTextContent('40');
    expect(row).toHaveTextContent('60');
    expect(row).toHaveTextContent('+20');
  });

  it('shows reassess errors such as a missing rule', async () => {
    vi.mocked(roadmapService.reassess).mockRejectedValueOnce(makeAxiosError(409, 'No active readiness rule configured'));
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Refresh readiness (reassess)' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No active readiness rule configured');
    expect(screen.queryByTestId('rule-version-note')).not.toBeInTheDocument();
  });
});
