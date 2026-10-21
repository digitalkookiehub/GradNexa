import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminAssessmentDetailPage } from './AdminAssessmentDetailPage';
import { adminAssessmentService } from '@/services/adminAssessmentService';
import { assessmentService } from '@/services/assessmentService';
import { studentService } from '@/services/studentService';
import type { AdminAssessmentDetail } from '@/types/assessment';

vi.mock('@/services/adminAssessmentService', () => ({
  adminAssessmentService: { get: vi.fn(), update: vi.fn(), addQuestion: vi.fn(), updateQuestion: vi.fn(), deleteQuestion: vi.fn() },
}));
vi.mock('@/services/assessmentService', () => ({ assessmentService: { listSkills: vi.fn() } }));
vi.mock('@/services/studentService', () => ({ studentService: { listDepartments: vi.fn() } }));

function detail(over: Partial<AdminAssessmentDetail> = {}): AdminAssessmentDetail {
  return {
    id: 5,
    series_key: 's',
    version: 1,
    title: 'Programming Test',
    type: 'TECHNICAL',
    department_id: null,
    time_limit_min: 30,
    max_attempts: 3,
    negative_marking: 0.25,
    status: 'DRAFT',
    question_count: 0,
    total_marks: 0,
    created_by: 1,
    questions: [],
    ...over,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/assessments/5']}>
      <Routes>
        <Route path="/admin/assessments/:id" element={<AdminAssessmentDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('AdminAssessmentDetailPage negative marking', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminAssessmentService.get).mockResolvedValue(detail());
    vi.mocked(adminAssessmentService.update).mockResolvedValue(detail());
    vi.mocked(assessmentService.listSkills).mockResolvedValue([]);
    vi.mocked(studentService.listDepartments).mockResolvedValue([]);
  });

  it('shows the stored fraction, not a ticked box', async () => {
    renderPage();
    expect(await screen.findByLabelText('Negative marking (0 to 1)')).toHaveValue(0.25);
  });

  it('saving another change keeps 0.25 instead of turning it into 1', async () => {
    renderPage();
    const title = await screen.findByLabelText('Title');
    await userEvent.clear(title);
    await userEvent.type(title, 'Renamed');
    await userEvent.click(screen.getByRole('button', { name: 'Save details' }));
    await waitFor(() =>
      expect(adminAssessmentService.update).toHaveBeenCalledWith(5, expect.objectContaining({ title: 'Renamed', negative_marking: 0.25 })),
    );
  });

  it('is read-only once published', async () => {
    vi.mocked(adminAssessmentService.get).mockResolvedValue(detail({ status: 'PUBLISHED' }));
    renderPage();
    expect(await screen.findByLabelText('Negative marking (0 to 1)')).toBeDisabled();
  });
});
