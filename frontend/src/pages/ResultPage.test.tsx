import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ResultPage } from './ResultPage';
import { assessmentService } from '@/services/assessmentService';

vi.mock('@/services/assessmentService', () => ({ assessmentService: { getResult: vi.fn() } }));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/attempts/7/result']}>
      <Routes>
        <Route path="/attempts/:attemptId/result" element={<ResultPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ResultPage', () => {
  beforeEach(() => vi.resetAllMocks());

  it('renders overall score and per-skill breakdown', async () => {
    vi.mocked(assessmentService.getResult).mockResolvedValue({
      id: 1,
      attempt_id: 7,
      assessment_id: 3,
      assessment_title: 'Aptitude Basics',
      assessment_version: 2,
      total_score: 7,
      max_score: 10,
      percentage: 70,
      per_skill_scores: [
        { skill_id: 1, skill_name: 'Logic', score: 4, max: 5, percentage: 80 },
        { skill_id: 2, skill_name: 'Verbal', score: 3, max: 5, percentage: 60 },
      ],
      computed_at: new Date().toISOString(),
    });
    renderPage();
    expect(await screen.findByText('Aptitude Basics')).toBeInTheDocument();
    expect(screen.getByTestId('overall-percentage')).toHaveTextContent('70%');
    expect(screen.getByText('Score: 7 / 10')).toBeInTheDocument();
    expect(screen.getByText('Logic')).toBeInTheDocument();
    expect(screen.getByText('Verbal')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Back to assessments' })).toHaveAttribute('href', '/assessments');
    expect(screen.queryByText(/correct answer/i)).not.toBeInTheDocument();
  });

  it('shows an error when the result is unavailable', async () => {
    vi.mocked(assessmentService.getResult).mockRejectedValue(new Error('Result not found'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('Result not found');
  });
});
