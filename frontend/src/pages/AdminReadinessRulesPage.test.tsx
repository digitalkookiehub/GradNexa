import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminReadinessRulesPage } from './AdminReadinessRulesPage';
import { adminReadinessService } from '@/services/adminReadinessService';
import { assessmentService } from '@/services/assessmentService';
import type { ReadinessRule } from '@/types';

vi.mock('@/services/adminReadinessService', () => ({
  adminReadinessService: { listRules: vi.fn(), createRule: vi.fn(), activateRule: vi.fn() },
}));
vi.mock('@/services/assessmentService', () => ({ assessmentService: { listSkillCategories: vi.fn() } }));

function rule(id: number, version: number, active: boolean): ReadinessRule {
  return {
    id,
    version,
    is_active: active,
    weights: { '1': 100 },
    level_thresholds: [{ level: 'Strong', min_score: 0 }],
    gap_thresholds: { high_min_gap: 30, medium_min_gap: 15 },
    created_by: 1,
    created_at: '2026-01-01T00:00:00Z',
  };
}

describe('AdminReadinessRulesPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(assessmentService.listSkillCategories).mockResolvedValue([{ id: 1, name: 'Technical', scope: 'COMMON', department_id: null }]);
    vi.mocked(adminReadinessService.listRules).mockResolvedValue([rule(1, 1, true), rule(2, 2, false)]);
  });

  it('shows the active badge and activates only after in-page confirmation', async () => {
    vi.mocked(adminReadinessService.activateRule).mockResolvedValue(rule(2, 2, true));
    render(<AdminReadinessRulesPage />);
    expect(await screen.findByText('Active')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Activate version 1' })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Activate version 2' }));
    expect(adminReadinessService.activateRule).not.toHaveBeenCalled();
    await userEvent.click(within_dialog());
    expect(adminReadinessService.activateRule).toHaveBeenCalledWith(2);
  });

  it('shows the server 422 message when creating a version fails', async () => {
    vi.mocked(adminReadinessService.createRule).mockRejectedValue(new Error('Invalid thresholds'));
    render(<AdminReadinessRulesPage />);
    await userEvent.click(await screen.findByRole('button', { name: 'Create new version' }));
    await userEvent.click(screen.getByRole('button', { name: 'Create version' }));
    expect(adminReadinessService.createRule).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid thresholds');
  });
});

function within_dialog(): HTMLElement {
  return screen.getByRole('alertdialog').querySelector('button') as HTMLElement;
}
