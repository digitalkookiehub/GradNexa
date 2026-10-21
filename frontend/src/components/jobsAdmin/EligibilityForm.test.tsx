import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { EligibilityForm } from './EligibilityForm';
import type { EligibilityRuleOut } from '@/types/jobAdmin';

const DEPARTMENTS = [
  { id: 1, name: 'CSE', code: 'CSE' },
  { id: 2, name: 'ECE', code: 'ECE' },
];

function setup(initial: EligibilityRuleOut | null = null, readOnly = false) {
  const onSave = vi.fn();
  const onRemove = vi.fn();
  render(<EligibilityForm initial={initial} departments={DEPARTMENTS} saving={false} readOnly={readOnly} onSave={onSave} onRemove={onRemove} />);
  return { onSave, onRemove };
}

describe('EligibilityForm', () => {
  it('shows the separation notice and the all-departments default', () => {
    setup();
    expect(screen.getByText(/checked automatically against student records/)).toHaveTextContent('NOT evaluated');
    expect(screen.getByText(/All departments/)).toBeInTheDocument();
  });

  it('blocks save when a minimum CGPA has no basis', async () => {
    const { onSave } = setup();
    await userEvent.click(screen.getByLabelText('Minimum CGPA'));
    await userEvent.type(screen.getByLabelText('Minimum CGPA (0-10)'), '7');
    await userEvent.click(screen.getByRole('button', { name: 'Save eligibility rule' }));
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText('Choose which CGPA the minimum is checked against.')).toBeInTheDocument();
  });

  it('explains the chosen basis and sends only the enabled criteria', async () => {
    const { onSave } = setup();
    await userEvent.click(screen.getByLabelText('Minimum CGPA'));
    await userEvent.type(screen.getByLabelText('Minimum CGPA (0-10)'), '7.5');
    await userEvent.selectOptions(screen.getByLabelText('CGPA basis'), 'AVERAGE_ALL_SEMESTERS');
    expect(screen.getByText(/average CGPA across all/)).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('CSE'));
    await userEvent.click(screen.getByRole('button', { name: 'Save eligibility rule' }));
    expect(onSave).toHaveBeenCalledWith({ cgpa_min: 7.5, cgpa_basis: 'AVERAGE_ALL_SEMESTERS', department_ids: [1] });
  });

  it('rejects an empty graduation years list and out-of-range attendance', async () => {
    const { onSave } = setup();
    await userEvent.click(screen.getByLabelText('Graduation years'));
    await userEvent.click(screen.getByLabelText('Minimum attendance'));
    await userEvent.type(screen.getByLabelText('Minimum attendance % (0-100)'), '120');
    await userEvent.click(screen.getByRole('button', { name: 'Save eligibility rule' }));
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText(/Enter one or more graduation years/)).toBeInTheDocument();
    expect(screen.getByText(/attendance must be a number between 0 and 100/)).toBeInTheDocument();
  });

  it('removes the rule only after in-page confirmation', async () => {
    const rule: EligibilityRuleOut = {
      cgpa_min: 7,
      cgpa_basis: 'LATEST_SEMESTER',
      max_arrears: null,
      attendance_min: null,
      department_ids: null,
      graduation_years: null,
      custom_notes: [],
    };
    const { onRemove } = setup(rule);
    await userEvent.click(screen.getByRole('button', { name: 'Remove rule' }));
    expect(onRemove).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Confirm remove' }));
    expect(onRemove).toHaveBeenCalledTimes(1);
  });

  it('is read-only for closed jobs', () => {
    setup(null, true);
    expect(screen.queryByRole('button', { name: 'Save eligibility rule' })).not.toBeInTheDocument();
    expect(screen.getByLabelText('Minimum CGPA')).toBeDisabled();
  });
});
