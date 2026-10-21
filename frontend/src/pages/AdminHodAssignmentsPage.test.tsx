import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminHodAssignmentsPage } from './AdminHodAssignmentsPage';
import { hodAssignmentService } from '@/services/hodAssignmentService';
import { adminUserService } from '@/services/adminUserService';
import { studentService } from '@/services/studentService';
import { makeAxiosError } from '@/test/helpers';

vi.mock('@/services/hodAssignmentService', () => ({ hodAssignmentService: { list: vi.fn(), create: vi.fn(), remove: vi.fn() } }));
vi.mock('@/services/adminUserService', () => ({ adminUserService: { list: vi.fn() } }));
vi.mock('@/services/studentService', () => ({ studentService: { listDepartments: vi.fn() } }));

const row = { id: 5, hod_user_id: 9, hod_name: 'Dr. Rao', hod_email: 'rao@x.edu', department_id: 1, department_name: 'CSE' };

describe('AdminHodAssignmentsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(hodAssignmentService.list).mockResolvedValue([row]);
    vi.mocked(adminUserService.list).mockResolvedValue({
      items: [{ id: 9, full_name: 'Dr. Rao', email: 'rao@x.edu', role: 'HOD', is_active: true, created_at: '2026-01-01T00:00:00Z', student: null }],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.mocked(studentService.listDepartments).mockResolvedValue([{ id: 1, name: 'CSE', code: 'CSE' }]);
  });

  it('lists assignments', async () => {
    render(<AdminHodAssignmentsPage />);
    expect(await screen.findByText('Dr. Rao')).toBeInTheDocument();
    expect(screen.getByText('rao@x.edu')).toBeInTheDocument();
  });

  it('offers only HOD users to pick from', async () => {
    render(<AdminHodAssignmentsPage />);
    await screen.findByText('rao@x.edu');
    expect(adminUserService.list).toHaveBeenCalledWith({ role: 'HOD', page_size: 100 });
    expect(screen.getByRole('option', { name: 'Dr. Rao (rao@x.edu)' })).toBeInTheDocument();
  });

  it('shows the empty state', async () => {
    vi.mocked(hodAssignmentService.list).mockResolvedValue([]);
    render(<AdminHodAssignmentsPage />);
    expect(await screen.findByText('No HOD assignments yet.')).toBeInTheDocument();
  });

  it('validates then creates an assignment', async () => {
    const user = userEvent.setup();
    vi.mocked(hodAssignmentService.create).mockResolvedValue(row);
    render(<AdminHodAssignmentsPage />);
    await screen.findByText('Dr. Rao');
    await user.click(screen.getByRole('button', { name: 'Add assignment' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Choose a HOD.');
    expect(hodAssignmentService.create).not.toHaveBeenCalled();

    await user.selectOptions(screen.getByLabelText('HOD'), '9');
    await user.selectOptions(screen.getByLabelText('Department'), 'CSE');
    await user.click(screen.getByRole('button', { name: 'Add assignment' }));
    await waitFor(() => expect(hodAssignmentService.create).toHaveBeenCalledWith({ hod_user_id: 9, department_id: 1 }));
    expect(await screen.findByText('Assignment created.')).toBeInTheDocument();
  });

  it('shows the 409 message', async () => {
    const user = userEvent.setup();
    vi.mocked(hodAssignmentService.create).mockRejectedValue(makeAxiosError(409, 'Assignment already exists'));
    render(<AdminHodAssignmentsPage />);
    await screen.findByText('Dr. Rao');
    await user.selectOptions(screen.getByLabelText('HOD'), '9');
    await user.selectOptions(screen.getByLabelText('Department'), 'CSE');
    await user.click(screen.getByRole('button', { name: 'Add assignment' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Assignment already exists');
  });

  it('confirms in-page before deleting, and can cancel', async () => {
    const user = userEvent.setup();
    vi.mocked(hodAssignmentService.remove).mockResolvedValue();
    render(<AdminHodAssignmentsPage />);
    await screen.findByText('Dr. Rao');
    await user.click(screen.getByRole('button', { name: 'Remove Dr. Rao from CSE' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(hodAssignmentService.remove).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Remove Dr. Rao from CSE' }));
    await user.click(screen.getByRole('button', { name: 'Confirm remove' }));
    await waitFor(() => expect(hodAssignmentService.remove).toHaveBeenCalledWith(5));
    expect(await screen.findByText('Assignment removed.')).toBeInTheDocument();
  });

  it('shows an alert when loading fails', async () => {
    vi.mocked(hodAssignmentService.list).mockRejectedValue(new Error('nope'));
    render(<AdminHodAssignmentsPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('nope');
  });
});
