import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminUsersPage } from './AdminUsersPage';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { adminUserService } from '@/services/adminUserService';
import { studentService } from '@/services/studentService';
import { AuthStub, makeAxiosError, makeUser } from '@/test/helpers';
import type { AdminUser } from '@/types/adminUsers';
import type { UserRole } from '@/types';

vi.mock('@/services/adminUserService', () => ({
  adminUserService: {
    list: vi.fn(),
    changeRole: vi.fn(),
    listFacultyAssignments: vi.fn(),
    createFacultyAssignment: vi.fn(),
    removeFacultyAssignment: vi.fn(),
  },
}));
vi.mock('@/services/studentService', () => ({ studentService: { listDepartments: vi.fn() } }));

function user(over: Partial<AdminUser> & Pick<AdminUser, 'id' | 'full_name' | 'email' | 'role'>): AdminUser {
  return { is_active: true, created_at: '2026-03-04T10:00:00Z', student: null, ...over };
}

const me = user({ id: 1, full_name: 'Ada', email: 'a@b.com', role: 'ADMIN' });
const asha = user({
  id: 2,
  full_name: 'Asha Rao',
  email: 'asha@x.edu',
  role: 'STUDENT',
  student: { student_id: 20, department_id: 1, department_name: 'CSE', roll_number: 'CSE-101', graduation_year: 2026, profile_complete: true },
});
const ravi = user({
  id: 3,
  full_name: 'Ravi Kumar',
  email: 'ravi@x.edu',
  role: 'STUDENT',
  student: { student_id: 30, department_id: null, department_name: null, roll_number: null, graduation_year: null, profile_complete: false },
});
const prof = user({ id: 4, full_name: 'Prof Iyer', email: 'iyer@x.edu', role: 'FACULTY' });

function page(items: AdminUser[], total = items.length) {
  return { items, total, page: 1, page_size: 25 };
}

function renderAs(role: UserRole = 'ADMIN') {
  return render(
    <AuthStub user={{ ...makeUser(role), id: 1 }}>
      <MemoryRouter initialEntries={['/admin/users']}>
        <Routes>
          <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
            <Route path="/admin/users" element={<AdminUsersPage />} />
          </Route>
          <Route path="*" element={<p>elsewhere</p>} />
        </Routes>
      </MemoryRouter>
    </AuthStub>,
  );
}

describe('AdminUsersPage - users tab', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminUserService.list).mockResolvedValue(page([me, asha, ravi, prof]));
    vi.mocked(adminUserService.listFacultyAssignments).mockResolvedValue([]);
    vi.mocked(studentService.listDepartments).mockResolvedValue([{ id: 1, name: 'CSE', code: 'CSE' }]);
  });

  it.each<UserRole>(['STUDENT', 'FACULTY', 'TPO', 'HOD'])('redirects %s away', async (role) => {
    renderAs(role);
    expect(await screen.findByText('elsewhere')).toBeInTheDocument();
    expect(adminUserService.list).not.toHaveBeenCalled();
  });

  it('lists users with student columns and profile status', async () => {
    renderAs();
    const table = await screen.findByRole('table', { name: 'Users in your college' });
    expect(within(table).getByText('Asha Rao')).toBeInTheDocument();
    expect(within(table).getByText('CSE-101')).toBeInTheDocument();
    expect(within(table).getByText('Complete')).toBeInTheDocument();
    expect(within(table).getByText('Incomplete')).toBeInTheDocument();
    expect(within(table).getByText('(you)')).toBeInTheDocument();
    expect(screen.getByText('Showing 1-4 of 4')).toBeInTheDocument();
  });

  it('does not offer a role change for yourself', async () => {
    renderAs();
    await screen.findByText('Asha Rao');
    expect(screen.queryByRole('button', { name: 'Change role of Ada' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Change role of Asha Rao' })).toBeInTheDocument();
  });

  it('applies the search, role and department filters and resets to page 1', async () => {
    const u = userEvent.setup();
    renderAs();
    await screen.findByText('Asha Rao');
    await u.type(screen.getByLabelText('Search name, email or roll number'), 'asha');
    await u.selectOptions(screen.getByLabelText('Role'), 'STUDENT');
    await u.selectOptions(screen.getByLabelText('Student department'), 'CSE');
    await u.click(screen.getByRole('button', { name: 'Search' }));
    await waitFor(() =>
      expect(adminUserService.list).toHaveBeenLastCalledWith({ search: 'asha', role: 'STUDENT', department_id: 1, page: 1, page_size: 25 }),
    );
  });

  it('shows an empty state', async () => {
    vi.mocked(adminUserService.list).mockResolvedValue(page([]));
    renderAs();
    expect(await screen.findByText('No users match these filters.')).toBeInTheDocument();
  });

  it('pages through results', async () => {
    const u = userEvent.setup();
    vi.mocked(adminUserService.list).mockResolvedValue(page([asha], 30));
    renderAs();
    expect(await screen.findByText('Showing 1-25 of 30')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
    await u.click(screen.getByRole('button', { name: 'Next' }));
    await waitFor(() => expect(adminUserService.list).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })));
  });

  it('confirms in the page before changing a role, then reports and reloads', async () => {
    const u = userEvent.setup();
    vi.mocked(adminUserService.changeRole).mockResolvedValue({
      id: 2,
      role: 'FACULTY',
      previous_role: 'STUDENT',
      removed_faculty_assignments: 0,
      removed_hod_assignments: 0,
    });
    renderAs();
    await screen.findByText('Asha Rao');
    await u.click(screen.getByRole('button', { name: 'Change role of Asha Rao' }));
    await u.selectOptions(screen.getByLabelText('New role for Asha Rao'), 'FACULTY');
    await u.click(screen.getByRole('button', { name: 'Apply' }));
    const dialog = screen.getByRole('alertdialog', { name: 'Change role to Faculty?' });
    expect(dialog).toHaveTextContent('takes effect immediately');
    expect(adminUserService.changeRole).not.toHaveBeenCalled();
    await u.click(within(dialog).getByRole('button', { name: 'Change role' }));
    await waitFor(() => expect(adminUserService.changeRole).toHaveBeenCalledWith(2, 'FACULTY'));
    expect(await screen.findByText('Asha Rao is now Faculty.')).toBeInTheDocument();
    expect(vi.mocked(adminUserService.list).mock.calls.length).toBeGreaterThan(1);
  });

  it('warns that leaving Faculty removes assignments and reports how many were removed', async () => {
    const u = userEvent.setup();
    vi.mocked(adminUserService.changeRole).mockResolvedValue({
      id: 4,
      role: 'STUDENT',
      previous_role: 'FACULTY',
      removed_faculty_assignments: 3,
      removed_hod_assignments: 0,
    });
    renderAs();
    await screen.findByText('Prof Iyer');
    await u.click(screen.getByRole('button', { name: 'Change role of Prof Iyer' }));
    await u.selectOptions(screen.getByLabelText('New role for Prof Iyer'), 'STUDENT');
    await u.click(screen.getByRole('button', { name: 'Apply' }));
    expect(screen.getByRole('alertdialog')).toHaveTextContent('faculty-to-student assignments will be removed');
    await u.click(screen.getByRole('button', { name: 'Change role' }));
    expect(await screen.findByText(/3 faculty assignment\(s\) removed/)).toBeInTheDocument();
  });

  it('can cancel a pending change without calling the API', async () => {
    const u = userEvent.setup();
    renderAs();
    await screen.findByText('Asha Rao');
    await u.click(screen.getByRole('button', { name: 'Change role of Asha Rao' }));
    await u.click(screen.getByRole('button', { name: 'Apply' }));
    await u.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Cancel' }));
    expect(adminUserService.changeRole).not.toHaveBeenCalled();
    expect(screen.queryByRole('alertdialog')).toBeNull();
  });

  it('shows the server message when a change is refused', async () => {
    const u = userEvent.setup();
    vi.mocked(adminUserService.changeRole).mockRejectedValue(makeAxiosError(409, 'You cannot change your own role'));
    renderAs();
    await screen.findByText('Asha Rao');
    await u.click(screen.getByRole('button', { name: 'Change role of Asha Rao' }));
    await u.click(screen.getByRole('button', { name: 'Apply' }));
    await u.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Change role' }));
    expect(await screen.findByText('You cannot change your own role')).toBeInTheDocument();
  });

  it('shows an error when loading fails', async () => {
    vi.mocked(adminUserService.list).mockRejectedValue(makeAxiosError(500, 'boom'));
    renderAs();
    expect(await screen.findByText('boom')).toBeInTheDocument();
  });
});

describe('AdminUsersPage - faculty assignments tab', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(studentService.listDepartments).mockResolvedValue([]);
    vi.mocked(adminUserService.list).mockImplementation(async (q) =>
      q?.role === 'FACULTY' ? page([prof]) : q?.role === 'STUDENT' ? page([asha, ravi]) : page([me, asha, prof]),
    );
    vi.mocked(adminUserService.listFacultyAssignments).mockResolvedValue([
      { id: 7, faculty_user_id: 4, faculty_name: 'Prof Iyer', faculty_email: 'iyer@x.edu', student_id: 20, student_name: 'Asha Rao', student_email: 'asha@x.edu' },
    ]);
  });

  async function openTab() {
    const u = userEvent.setup();
    renderAs();
    await u.click(await screen.findByRole('tab', { name: 'Faculty assignments' }));
    await screen.findByText('Current assignments');
    return u;
  }

  it('lists current assignments with names', async () => {
    await openTab();
    const table = screen.getByRole('table', { name: 'Faculty assignments' });
    expect(within(table).getByText('Prof Iyer')).toBeInTheDocument();
    expect(within(table).getByText('asha@x.edu')).toBeInTheDocument();
  });

  it('finds a student, then creates an assignment using the student id', async () => {
    const u = await openTab();
    vi.mocked(adminUserService.createFacultyAssignment).mockResolvedValue();
    await u.selectOptions(screen.getByLabelText('Faculty member'), '4');
    await u.type(screen.getByLabelText('Find a student (name, email or roll number)'), 'asha');
    await u.click(screen.getByRole('button', { name: 'Find student' }));
    await waitFor(() => expect(adminUserService.list).toHaveBeenCalledWith({ role: 'STUDENT', search: 'asha', page_size: 10 }));
    await u.selectOptions(await screen.findByLabelText('Student'), '20');
    await u.click(screen.getByRole('button', { name: 'Add assignment' }));
    await waitFor(() => expect(adminUserService.createFacultyAssignment).toHaveBeenCalledWith(4, 20));
    expect(await screen.findByText('Assignment created.')).toBeInTheDocument();
  });

  it('validates before creating', async () => {
    const u = await openTab();
    await u.click(screen.getByRole('button', { name: 'Add assignment' }));
    expect(await screen.findByText('Choose a faculty member.')).toBeInTheDocument();
    await u.selectOptions(screen.getByLabelText('Faculty member'), '4');
    await u.click(screen.getByRole('button', { name: 'Add assignment' }));
    expect(await screen.findByText('Search for a student and choose one.')).toBeInTheDocument();
    expect(adminUserService.createFacultyAssignment).not.toHaveBeenCalled();
  });

  it('confirms before removing, and can cancel', async () => {
    const u = await openTab();
    vi.mocked(adminUserService.removeFacultyAssignment).mockResolvedValue();
    await u.click(screen.getByRole('button', { name: 'Remove Asha Rao from Prof Iyer' }));
    await u.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(adminUserService.removeFacultyAssignment).not.toHaveBeenCalled();
    await u.click(screen.getByRole('button', { name: 'Remove Asha Rao from Prof Iyer' }));
    await u.click(screen.getByRole('button', { name: 'Confirm remove' }));
    await waitFor(() => expect(adminUserService.removeFacultyAssignment).toHaveBeenCalledWith(7));
    expect(await screen.findByText('Assignment removed.')).toBeInTheDocument();
  });
});
