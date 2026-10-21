import { render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { InterviewResultPage } from './InterviewResultPage';
import { interviewService } from '@/services/interviewService';
import { makeAxiosError } from '@/test/helpers';
import type { InterviewResult } from '@/types';

vi.mock('@/services/interviewService', () => ({ interviewService: { getResult: vi.fn() } }));

const result: InterviewResult = {
  id: 1,
  interview_id: 9,
  role_name: 'Backend Dev',
  overall: 62.5,
  competency_scores: [{ competency: 'Databases', score: 70, max: 100, questions: 2 }],
  per_question: [
    { question_id: 1, position: 1, prompt: 'Explain indexes.', competency: 'Databases', score: 80, answered: true, too_short: false, covered_concepts: ['B-tree'], missed_concepts: ['Covering index'] },
    { question_id: 2, position: 2, prompt: 'Explain REST.', competency: 'APIs', score: 0, answered: true, too_short: true, covered_concepts: [], missed_concepts: ['Statelessness'] },
    { question_id: 3, position: 3, prompt: 'Explain joins.', competency: 'Databases', score: 0, answered: false, too_short: false, covered_concepts: [], missed_concepts: [] },
  ],
  computed_at: '2026-01-01T00:00:00Z',
  scoring_version: 1,
  disclaimer: 'Coverage of keywords only. Not a hiring prediction.',
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/interview/9/result']}>
      <Routes>
        <Route path="/interview/:id/result" element={<InterviewResultPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('InterviewResultPage', () => {
  beforeEach(() => vi.resetAllMocks());

  it('renders overall, competency bars, concept chips, notes and the disclaimer', async () => {
    vi.mocked(interviewService.getResult).mockResolvedValue(result);
    renderPage();
    expect(await screen.findByTestId('disclaimer')).toHaveTextContent('Coverage of keywords only. Not a hiring prediction.');
    expect(screen.getByTestId('overall')).toHaveTextContent('62.5');
    const bar = screen.getByLabelText('Databases');
    expect(bar.tagName).toBe('PROGRESS');
    expect(bar).toHaveAttribute('value', '70');
    expect(screen.getByRole('list', { name: 'Competency scores' })).toHaveTextContent('70 / 100');
    const q1 = screen.getAllByRole('listitem').find((li) => li.textContent?.includes('Explain indexes.'));
    expect(q1).toBeDefined();
    if (q1) {
      expect(within(q1).getByRole('list', { name: 'Covered concepts' })).toHaveTextContent('B-tree');
      expect(within(q1).getByRole('list', { name: 'Missed concepts' })).toHaveTextContent('Covering index');
    }
    expect(screen.getByTestId('too-short-2')).toBeInTheDocument();
    expect(screen.getByTestId('unanswered-3')).toBeInTheDocument();
    expect(screen.queryByText(/probability|chance of/i)).not.toBeInTheDocument();
  });

  it('handles a null overall and falls back to a default disclaimer', async () => {
    vi.mocked(interviewService.getResult).mockResolvedValue({ ...result, overall: null, disclaimer: '' });
    renderPage();
    expect(await screen.findByTestId('no-overall')).toBeInTheDocument();
    expect(screen.getByTestId('disclaimer')).toHaveTextContent(/keyword-rubric coverage/i);
  });

  it('shows an alert on error', async () => {
    vi.mocked(interviewService.getResult).mockRejectedValue(makeAxiosError(404, 'Result not found'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('Result not found');
  });
});
