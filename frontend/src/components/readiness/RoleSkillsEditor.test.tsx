import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { RoleSkillsEditor } from './RoleSkillsEditor';
import type { Skill } from '@/types';

const SKILLS: Skill[] = [
  { id: 1, name: 'Python', description: null, category_id: 1, category_name: 'Technical' },
  { id: 2, name: 'SQL', description: null, category_id: 1, category_name: 'Technical' },
];

function setup() {
  const onSave = vi.fn();
  render(
    <RoleSkillsEditor skills={SKILLS} initial={[{ skill_id: 1, skill_name: 'Python', required_level: 70, weight: 2 }]} saving={false} onSave={onSave} />,
  );
  return { onSave };
}

describe('RoleSkillsEditor', () => {
  it('excludes already-added skills from the picker and saves the bulk payload', async () => {
    const { onSave } = setup();
    expect(screen.queryByRole('option', { name: /Python/ })).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('Add a skill'), '2');
    await userEvent.click(screen.getByRole('button', { name: 'Add skill' }));
    const req = screen.getByLabelText('Required level for SQL');
    await userEvent.clear(req);
    await userEvent.type(req, '55');
    await userEvent.click(screen.getByRole('button', { name: 'Save skills' }));
    expect(onSave).toHaveBeenCalledWith([
      { skill_id: 1, required_level: 70, weight: 2 },
      { skill_id: 2, required_level: 55, weight: 1 },
    ]);
  });

  it('validates required level range and positive weight', async () => {
    const { onSave } = setup();
    const req = screen.getByLabelText('Required level for Python');
    await userEvent.clear(req);
    await userEvent.type(req, '101');
    await userEvent.click(screen.getByRole('button', { name: 'Save skills' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Required level for Python must be between 0 and 100.');
    await userEvent.clear(req);
    await userEvent.type(req, '50');
    const wt = screen.getByLabelText('Weight for Python');
    await userEvent.clear(wt);
    await userEvent.type(wt, '0');
    await userEvent.click(screen.getByRole('button', { name: 'Save skills' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Weight for Python must be greater than 0.');
    expect(onSave).not.toHaveBeenCalled();
  });

  it('removes a skill row', async () => {
    const { onSave } = setup();
    await userEvent.click(screen.getByRole('button', { name: 'Remove Python' }));
    await userEvent.click(screen.getByRole('button', { name: 'Save skills' }));
    expect(onSave).toHaveBeenCalledWith([]);
  });
});
