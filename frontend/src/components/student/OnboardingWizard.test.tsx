import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { OnboardingWizard } from './OnboardingWizard';
import { studentService } from '@/services/studentService';
import type { StudentProfile } from '@/types';

vi.mock('@/services/studentService', () => ({
  studentService: {
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
    listDepartments: vi.fn(),
    listAcademicRecords: vi.fn(),
    createAcademicRecord: vi.fn(),
    updateAcademicRecord: vi.fn(),
  },
}));

const mocked = vi.mocked(studentService);

const emptyProfile: StudentProfile = {
  id: 1,
  user_id: 1,
  college_id: 1,
  department_id: null,
  department_name: null,
  roll_number: null,
  graduation_year: null,
  phone: null,
  profile_complete: false,
};

function renderWizard() {
  return render(
    <MemoryRouter initialEntries={['/onboarding']}>
      <Routes>
        <Route path="/onboarding" element={<OnboardingWizard />} />
        <Route path="/dashboard" element={<div>dashboard page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

async function fillPersonal(): Promise<void> {
  await userEvent.type(screen.getByLabelText('Roll number'), '21CS001');
  await userEvent.type(screen.getByLabelText('Graduation year'), '2026');
  await userEvent.type(screen.getByLabelText('Phone'), '9876543210');
}

describe('OnboardingWizard', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocked.getProfile.mockResolvedValue(emptyProfile);
    mocked.listDepartments.mockResolvedValue([{ id: 5, name: 'Computer Science', code: 'CSE' }]);
    mocked.listAcademicRecords.mockResolvedValue([]);
  });

  it('blocks step 1 when fields are invalid and does not call the API', async () => {
    renderWizard();
    await screen.findByLabelText('Roll number');
    await userEvent.type(screen.getByLabelText('Graduation year'), '99');
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByText('Roll number is required.')).toBeInTheDocument();
    expect(screen.getByText(/4-digit year/)).toBeInTheDocument();
    expect(screen.getByText('Phone number is required.')).toBeInTheDocument();
    expect(mocked.updateProfile).not.toHaveBeenCalled();
  });

  it('shows the server error (duplicate roll number) and stays on step 1', async () => {
    mocked.updateProfile.mockRejectedValue(new Error('Roll number already exists'));
    renderWizard();
    await screen.findByLabelText('Roll number');
    await fillPersonal();
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Roll number already exists');
    expect(screen.getByLabelText('Roll number')).toBeInTheDocument();
  });

  it('requires an academic record before moving to department', async () => {
    mocked.updateProfile.mockResolvedValue(emptyProfile);
    renderWizard();
    await screen.findByLabelText('Roll number');
    await fillPersonal();
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    await screen.findByText('No semester records yet.');
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Add at least one semester record');
  });

  it('completes all three steps and navigates to /dashboard', async () => {
    mocked.updateProfile
      .mockResolvedValueOnce({ ...emptyProfile, roll_number: '21CS001', graduation_year: 2026, phone: '9876543210' })
      .mockResolvedValueOnce({ ...emptyProfile, department_id: 5, profile_complete: true });
    mocked.createAcademicRecord.mockResolvedValue({ id: 1, semester: 1, cgpa: 8.5, active_arrears: 0, attendance_pct: null });
    renderWizard();
    await screen.findByLabelText('Roll number');
    await fillPersonal();
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));

    await screen.findByText('No semester records yet.');
    await userEvent.type(screen.getByLabelText('Semester (1-12)'), '1');
    await userEvent.type(screen.getByLabelText('CGPA (0-10)'), '8.5');
    await userEvent.click(screen.getByRole('button', { name: 'Add record' }));
    await screen.findByText('Semester 1');
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));

    await userEvent.selectOptions(await screen.findByLabelText('Department'), '5');
    await userEvent.click(screen.getByRole('button', { name: /confirm and finish/i }));
    await waitFor(() => expect(screen.getByText('dashboard page')).toBeInTheDocument());
    expect(mocked.updateProfile).toHaveBeenLastCalledWith({ department_id: 5 });
  });
});
