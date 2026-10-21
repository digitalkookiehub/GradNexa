import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminSkillsPage } from './AdminSkillsPage';
import { adminAssessmentService } from '@/services/adminAssessmentService';
import { assessmentService } from '@/services/assessmentService';
import { studentService } from '@/services/studentService';

vi.mock('@/services/adminAssessmentService', () => ({
  adminAssessmentService: { createCategory: vi.fn(), updateCategory: vi.fn(), createSkill: vi.fn(), updateSkill: vi.fn() },
}));
vi.mock('@/services/assessmentService', () => ({
  assessmentService: { listSkillCategories: vi.fn(), listSkills: vi.fn() },
}));
vi.mock('@/services/studentService', () => ({ studentService: { listDepartments: vi.fn() } }));

describe('AdminSkillsPage category department picker', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(assessmentService.listSkillCategories).mockResolvedValue([]);
    vi.mocked(assessmentService.listSkills).mockResolvedValue([]);
    vi.mocked(studentService.listDepartments).mockResolvedValue([{ id: 7, name: 'Computer Science', code: 'CSE' }]);
    vi.mocked(adminAssessmentService.createCategory).mockResolvedValue({ id: 1, name: 'x', scope: 'COMMON', department_id: null });
  });

  it('hides the department picker for COMMON and sends department_id null', async () => {
    render(<AdminSkillsPage />);
    await screen.findByRole('option', { name: 'Common' });
    expect(screen.queryByLabelText('Department (required)')).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Category name'), 'Soft skills');
    await userEvent.click(screen.getByRole('button', { name: 'Add category' }));
    expect(adminAssessmentService.createCategory).toHaveBeenCalledWith({ name: 'Soft skills', scope: 'COMMON', department_id: null });
  });

  it('requires a department for DEPARTMENT scope and sends it', async () => {
    render(<AdminSkillsPage />);
    await screen.findByRole('option', { name: 'Common' });
    await userEvent.type(screen.getByLabelText('Category name'), 'CS core');
    await userEvent.selectOptions(screen.getByLabelText('Scope'), 'DEPARTMENT');
    await userEvent.click(screen.getByRole('button', { name: 'Add category' }));
    expect(screen.getByText('Select a department for a department-scoped category.')).toBeInTheDocument();
    expect(adminAssessmentService.createCategory).not.toHaveBeenCalled();
    await userEvent.selectOptions(screen.getByLabelText('Department (required)'), '7');
    await userEvent.click(screen.getByRole('button', { name: 'Add category' }));
    expect(adminAssessmentService.createCategory).toHaveBeenCalledWith({ name: 'CS core', scope: 'DEPARTMENT', department_id: 7 });
  });

  it('clears the department when switching back to COMMON', async () => {
    render(<AdminSkillsPage />);
    await screen.findByRole('option', { name: 'Common' });
    await userEvent.type(screen.getByLabelText('Category name'), 'Mixed');
    await userEvent.selectOptions(screen.getByLabelText('Scope'), 'DEPARTMENT');
    await userEvent.selectOptions(screen.getByLabelText('Department (required)'), '7');
    await userEvent.selectOptions(screen.getByLabelText('Scope'), 'COMMON');
    expect(screen.queryByLabelText('Department (required)')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Add category' }));
    expect(adminAssessmentService.createCategory).toHaveBeenCalledWith({ name: 'Mixed', scope: 'COMMON', department_id: null });
  });
});
