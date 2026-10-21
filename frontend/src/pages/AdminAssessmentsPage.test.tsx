import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminAssessmentsPage } from './AdminAssessmentsPage';
import { adminAssessmentService } from '@/services/adminAssessmentService';
import { studentService } from '@/services/studentService';

vi.mock('@/services/adminAssessmentService', () => ({
  adminAssessmentService: { list: vi.fn(), create: vi.fn() },
}));
vi.mock('@/services/studentService', () => ({ studentService: { listDepartments: vi.fn() } }));

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminAssessmentsPage />
    </MemoryRouter>,
  );
}

describe('AdminAssessmentsPage department picker', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminAssessmentService.list).mockResolvedValue([]);
    vi.mocked(studentService.listDepartments).mockResolvedValue([{ id: 7, name: 'Computer Science', code: 'CSE' }]);
    vi.mocked(adminAssessmentService.create).mockResolvedValue({} as never);
  });

  it('sends the chosen department_id when creating', async () => {
    renderPage();
    await screen.findByRole('option', { name: 'Computer Science' });
    await userEvent.type(screen.getByLabelText('Title'), 'Dept test');
    await userEvent.selectOptions(screen.getByLabelText('Department (optional)'), '7');
    await userEvent.click(screen.getByRole('button', { name: 'Create assessment' }));
    expect(adminAssessmentService.create).toHaveBeenCalledWith(expect.objectContaining({ title: 'Dept test', department_id: 7 }));
  });

  it('sends department_id null when none is chosen', async () => {
    renderPage();
    await screen.findByRole('option', { name: 'Computer Science' });
    await userEvent.type(screen.getByLabelText('Title'), 'No dept');
    await userEvent.click(screen.getByRole('button', { name: 'Create assessment' }));
    expect(adminAssessmentService.create).toHaveBeenCalledWith(expect.objectContaining({ department_id: null }));
  });
});

describe('AdminAssessmentsPage negative marking', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminAssessmentService.list).mockResolvedValue([]);
    vi.mocked(studentService.listDepartments).mockResolvedValue([]);
    vi.mocked(adminAssessmentService.create).mockResolvedValue({} as never);
  });

  it('sends a number (never a boolean): 0 by default', async () => {
    renderPage();
    await userEvent.type(await screen.findByLabelText('Title'), 'T');
    await userEvent.click(screen.getByRole('button', { name: 'Create assessment' }));
    expect(adminAssessmentService.create).toHaveBeenCalledWith(expect.objectContaining({ negative_marking: 0 }));
  });

  it('sends the fraction the admin types', async () => {
    renderPage();
    await userEvent.type(await screen.findByLabelText('Title'), 'T');
    const field = screen.getByLabelText('Negative marking (0 to 1)');
    await userEvent.clear(field);
    await userEvent.type(field, '0.25');
    await userEvent.click(screen.getByRole('button', { name: 'Create assessment' }));
    expect(adminAssessmentService.create).toHaveBeenCalledWith(expect.objectContaining({ negative_marking: 0.25 }));
  });

  it.each(['1.5', '-0.1'])('rejects %s without calling the API', async (value) => {
    renderPage();
    await userEvent.type(await screen.findByLabelText('Title'), 'T');
    const field = screen.getByLabelText('Negative marking (0 to 1)');
    await userEvent.clear(field);
    await userEvent.type(field, value);
    await userEvent.click(screen.getByRole('button', { name: 'Create assessment' }));
    expect(await screen.findByText(/Negative marking must be a number/)).toBeInTheDocument();
    expect(adminAssessmentService.create).not.toHaveBeenCalled();
  });
});
