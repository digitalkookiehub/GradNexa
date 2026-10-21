import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AcademicRecordForm } from './AcademicRecordForm';

describe('AcademicRecordForm', () => {
  it('rejects out-of-range values without submitting', async () => {
    const onSubmit = vi.fn();
    render(<AcademicRecordForm onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('Semester (1-12)'), '13');
    await userEvent.type(screen.getByLabelText('CGPA (0-10)'), '10.5');
    await userEvent.clear(screen.getByLabelText('Active arrears'));
    await userEvent.type(screen.getByLabelText('Attendance % (optional)'), '120');
    await userEvent.click(screen.getByRole('button', { name: 'Add record' }));
    expect(screen.getByText(/Semester must be a whole number/)).toBeInTheDocument();
    expect(screen.getByText(/CGPA must be a number/)).toBeInTheDocument();
    expect(screen.getByText(/Active arrears must be/)).toBeInTheDocument();
    expect(screen.getByText(/Attendance must be/)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits parsed numbers', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<AcademicRecordForm onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('Semester (1-12)'), '3');
    await userEvent.type(screen.getByLabelText('CGPA (0-10)'), '8.25');
    await userEvent.click(screen.getByRole('button', { name: 'Add record' }));
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({ semester: 3, cgpa: 8.25, active_arrears: 0, attendance_pct: null }),
    );
  });

  it('surfaces a duplicate-semester server error', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('Semester already recorded'));
    render(<AcademicRecordForm onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('Semester (1-12)'), '3');
    await userEvent.type(screen.getByLabelText('CGPA (0-10)'), '8');
    await userEvent.click(screen.getByRole('button', { name: 'Add record' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Semester already recorded');
  });
});
