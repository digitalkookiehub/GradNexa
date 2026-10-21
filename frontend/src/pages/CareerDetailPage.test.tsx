import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CareerDetailPage } from './CareerDetailPage';
import { roadmapService } from '@/services/roadmapService';
import type { RoleDetailView } from '@/types';

vi.mock('@/services/roadmapService', () => ({
  roadmapService: { getRole: vi.fn(), getGoals: vi.fn(), saveGoals: vi.fn() },
}));

function makeRole(overrides: Partial<RoleDetailView> = {}): RoleDetailView {
  return {
    id: 4,
    department_id: null,
    name: 'Backend Engineer',
    description: 'Builds APIs',
    is_active: true,
    is_goal: false,
    skills: [{ skill_id: 1, skill_name: 'Python', required_level: 70, weight: 3 }],
    my_readiness: null,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/careers/4']}>
      <Routes>
        <Route path="/careers/:id" element={<CareerDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CareerDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('shows skills, links and a prompt to compute readiness when my_readiness is null', async () => {
    vi.mocked(roadmapService.getRole).mockResolvedValue(makeRole());
    renderPage();
    expect(await screen.findByRole('heading', { name: 'Backend Engineer' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'Python' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Compute it on the readiness page' })).toHaveAttribute('href', '/readiness');
    expect(screen.getByRole('link', { name: 'View skill gaps' })).toHaveAttribute('href', '/readiness/gaps?role=4');
    expect(screen.getByRole('link', { name: 'Generate 30-day plan' })).toHaveAttribute('href', '/plan?role=4');
    expect(screen.queryByText(/probab|chance/i)).not.toBeInTheDocument();
  });

  it('shows the readiness summary when present', async () => {
    vi.mocked(roadmapService.getRole).mockResolvedValue(
      makeRole({ my_readiness: { overall: 64.5, level: 'Developing', coverage: 50, rule_version: 2, computed_at: '2026-01-01T00:00:00Z' } }),
    );
    renderPage();
    const box = await screen.findByTestId('my-readiness');
    expect(box).toHaveTextContent('64.5');
    expect(box).toHaveTextContent('Developing');
    expect(box).toHaveTextContent('coverage 50%');
    expect(screen.queryByRole('link', { name: 'Compute it on the readiness page' })).not.toBeInTheDocument();
  });

  it('shows not enough evidence when overall is null', async () => {
    vi.mocked(roadmapService.getRole).mockResolvedValue(
      makeRole({ my_readiness: { overall: null, level: null, coverage: 0, rule_version: 2, computed_at: '2026-01-01T00:00:00Z' } }),
    );
    renderPage();
    expect(await screen.findByText(/Not enough evidence yet/)).toBeInTheDocument();
  });

  it('toggles the goal by saving the full goal list', async () => {
    vi.mocked(roadmapService.getRole).mockResolvedValue(makeRole());
    vi.mocked(roadmapService.getGoals).mockResolvedValue([{ career_role_id: 9, role_name: 'Other', priority: 1 }]);
    vi.mocked(roadmapService.saveGoals).mockResolvedValue();
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Add Backend Engineer to my goals' }));
    expect(roadmapService.saveGoals).toHaveBeenCalledWith([
      { career_role_id: 9, priority: 1 },
      { career_role_id: 4, priority: 2 },
    ]);
    expect(await screen.findByRole('button', { name: 'Remove Backend Engineer from my goals' })).toBeInTheDocument();
  });

  it('shows an error when the role cannot be loaded', async () => {
    vi.mocked(roadmapService.getRole).mockRejectedValue(new Error('missing'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('missing');
  });
});
