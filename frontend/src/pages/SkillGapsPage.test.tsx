import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SkillGapsPage } from './SkillGapsPage';
import { sortGaps } from '@/lib/readiness';
import { readinessService } from '@/services/readinessService';
import { makeAxiosError } from '@/test/helpers';
import type { Gap } from '@/types';

vi.mock('@/services/readinessService', () => ({
  readinessService: { listRoles: vi.fn(), gaps: vi.fn() },
}));

function gap(overrides: Partial<Gap>): Gap {
  return {
    skill_id: 1,
    skill_name: 'Skill',
    current: 40,
    required: 70,
    gap: 30,
    status: 'GAP',
    priority: 'HIGH',
    recommended_action: 'Practise more',
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <SkillGapsPage />
    </MemoryRouter>,
  );
}

describe('SkillGapsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(readinessService.listRoles).mockResolvedValue([
      { id: 5, department_id: null, name: 'Backend Engineer', description: null, is_active: true },
    ]);
  });

  it('sorts HIGH first with UNASSESSED and READY last and renders priority badges', async () => {
    vi.mocked(readinessService.gaps).mockResolvedValue([
      gap({ skill_id: 1, skill_name: 'Unassessed skill', current: null, gap: null, status: 'NO_EVIDENCE', priority: 'UNASSESSED', recommended_action: 'Take an assessment' }),
      gap({ skill_id: 2, skill_name: 'Ready skill', current: 90, gap: 0, status: 'READY', priority: 'NONE', recommended_action: 'Maintain' }),
      gap({ skill_id: 3, skill_name: 'Low skill', gap: 5, priority: 'LOW' }),
      gap({ skill_id: 4, skill_name: 'High skill', gap: 40, priority: 'HIGH' }),
      gap({ skill_id: 5, skill_name: 'Medium skill', gap: 15, priority: 'MEDIUM' }),
    ]);
    renderPage();
    await screen.findByText('High skill');
    const rows = screen.getAllByRole('row').slice(1);
    const names = rows.map((r) => within(r).getAllByRole('cell')[0].textContent);
    expect(names).toEqual(['High skill', 'Medium skill', 'Low skill', 'Ready skill', 'Unassessed skill']);
    const badges = screen.getAllByTestId('priority-badge').map((b) => b.textContent);
    expect(badges).toEqual(['High', 'Medium', 'Low', 'None', 'Unassessed']);
    expect(within(rows[4]).getByText('Not assessed')).toBeInTheDocument();
    expect(readinessService.gaps).toHaveBeenCalledWith(5);
  });

  it('asks the student to compute first on 404', async () => {
    vi.mocked(readinessService.gaps).mockRejectedValue(makeAxiosError(404, 'No readiness computed'));
    renderPage();
    expect(await screen.findByTestId('compute-first')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go to readiness' })).toHaveAttribute('href', '/readiness');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows an error alert on other failures', async () => {
    vi.mocked(readinessService.gaps).mockRejectedValue(new Error('boom'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
  });

  it('sortGaps does not mutate its input', () => {
    const input = [gap({ skill_id: 1, priority: 'LOW' }), gap({ skill_id: 2, priority: 'HIGH' })];
    sortGaps(input);
    expect(input[0].skill_id).toBe(1);
  });
});
