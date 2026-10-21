import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { RuleForm } from './RuleForm';
import type { ReadinessRule, SkillCategory } from '@/types';

const CATEGORIES: SkillCategory[] = [
  { id: 1, name: 'Technical', scope: 'COMMON', department_id: null },
  { id: 2, name: 'Aptitude', scope: 'COMMON', department_id: null },
];

const PREFILL: ReadinessRule = {
  id: 1,
  version: 1,
  is_active: true,
  weights: { '1': 60, '2': 40 },
  level_thresholds: [
    { level: 'Strong', min_score: 70 },
    { level: 'Developing', min_score: 0 },
  ],
  gap_thresholds: { high_min_gap: 30, medium_min_gap: 15 },
  created_by: 1,
  created_at: '2026-01-01T00:00:00Z',
};

function setup(prefill: ReadinessRule | null = PREFILL) {
  const onSubmit = vi.fn();
  render(<RuleForm categories={CATEGORIES} prefill={prefill} saving={false} onSubmit={onSubmit} onCancel={vi.fn()} />);
  return { onSubmit };
}

describe('RuleForm', () => {
  it('prefills from an existing rule and submits the payload', async () => {
    const { onSubmit } = setup();
    expect(screen.getByLabelText('Technical')).toHaveValue(60);
    await userEvent.click(screen.getByRole('button', { name: 'Create version' }));
    expect(onSubmit).toHaveBeenCalledWith({
      weights: { '1': 60, '2': 40 },
      level_thresholds: [
        { level: 'Strong', min_score: 70 },
        { level: 'Developing', min_score: 0 },
      ],
      gap_thresholds: { high_min_gap: 30, medium_min_gap: 15 },
    });
  });

  it('rejects negative weights and all-zero weights', async () => {
    const { onSubmit } = setup();
    const technical = screen.getByLabelText('Technical');
    await userEvent.clear(technical);
    await userEvent.type(technical, '-5');
    await userEvent.click(screen.getByRole('button', { name: 'Create version' }));
    expect(screen.getByText('Weights must be numbers that are zero or greater.')).toBeInTheDocument();
    await userEvent.clear(technical);
    await userEvent.clear(screen.getByLabelText('Aptitude'));
    await userEvent.click(screen.getByRole('button', { name: 'Create version' }));
    expect(screen.getByText('At least one category needs a weight greater than zero.')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('rejects duplicate level names', async () => {
    const { onSubmit } = setup();
    const name = screen.getByLabelText('Level name 2');
    await userEvent.clear(name);
    await userEvent.type(name, 'strong');
    await userEvent.click(screen.getByRole('button', { name: 'Create version' }));
    expect(screen.getByText('Duplicate level name: strong.')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('requires a level starting at 0 and supports add/remove rows', async () => {
    const { onSubmit } = setup();
    await userEvent.click(screen.getByRole('button', { name: 'Remove level 2' }));
    await userEvent.click(screen.getByRole('button', { name: 'Create version' }));
    expect(screen.getByText(/minimum score of 0/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Add level' }));
    await userEvent.type(screen.getByLabelText('Level name 2'), 'Starter');
    await userEvent.type(screen.getByLabelText('Minimum score 2'), '0');
    await userEvent.click(screen.getByRole('button', { name: 'Create version' }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it('rejects out-of-range level scores', async () => {
    const { onSubmit } = setup();
    const min = screen.getByLabelText('Minimum score 1');
    await userEvent.clear(min);
    await userEvent.type(min, '150');
    await userEvent.click(screen.getByRole('button', { name: 'Create version' }));
    expect(screen.getByText('Level minimum scores must be numbers between 0 and 100.')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('requires the high gap threshold to be at least the medium one', async () => {
    const { onSubmit } = setup();
    const high = screen.getByLabelText('High priority at gap of at least');
    await userEvent.clear(high);
    await userEvent.type(high, '10');
    await userEvent.click(screen.getByRole('button', { name: 'Create version' }));
    expect(screen.getByText(/greater than or equal to the medium-priority gap/)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('starts blank with one level row when there is no prefill', () => {
    setup(null);
    expect(screen.getByLabelText('Level name 1')).toHaveValue('');
    expect(screen.getByLabelText('Technical')).toHaveValue(null);
  });
});
