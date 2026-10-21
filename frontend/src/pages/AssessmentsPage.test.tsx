import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AssessmentsPage } from './AssessmentsPage';
import { assessmentService } from '@/services/assessmentService';
import type { StudentAssessment } from '@/types';

vi.mock('@/services/assessmentService', () => ({ assessmentService: { list: vi.fn() } }));

function make(overrides: Partial<StudentAssessment>): StudentAssessment {
  return {
    id: 1,
    series_key: 's',
    version: 1,
    title: 'Aptitude Basics',
    type: 'APTITUDE',
    department_id: null,
    time_limit_min: 30,
    max_attempts: 2,
    negative_marking: 0,
    status: 'PUBLISHED',
    question_count: 10,
    total_marks: 10,
    attempts_used: 0,
    in_progress_attempt_id: null,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <AssessmentsPage />
    </MemoryRouter>,
  );
}

describe('AssessmentsPage', () => {
  beforeEach(() => vi.resetAllMocks());

  it('shows Start for a fresh assessment with limits and attempts', async () => {
    vi.mocked(assessmentService.list).mockResolvedValue([make({})]);
    renderPage();
    expect(await screen.findByRole('link', { name: 'Start' })).toHaveAttribute('href', '/assessments/1/attempt');
    expect(screen.getByText('Time limit: 30 min')).toBeInTheDocument();
    expect(screen.getByText('Attempts: 0 / 2')).toBeInTheDocument();
  });

  it('shows Resume when an attempt is in progress', async () => {
    vi.mocked(assessmentService.list).mockResolvedValue([make({ in_progress_attempt_id: 5, attempts_used: 1 })]);
    renderPage();
    expect(await screen.findByRole('link', { name: 'Resume' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Start' })).not.toBeInTheDocument();
  });

  it('shows limit reached and no Start button', async () => {
    vi.mocked(assessmentService.list).mockResolvedValue([make({ attempts_used: 2 })]);
    renderPage();
    expect(await screen.findByText('Attempt limit reached')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Start' })).not.toBeInTheDocument();
  });

  it('shows an error alert when loading fails', async () => {
    vi.mocked(assessmentService.list).mockRejectedValue(new Error('boom'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
  });
});
