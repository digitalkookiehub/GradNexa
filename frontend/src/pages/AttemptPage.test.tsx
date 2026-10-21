import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AxiosError, type AxiosResponse } from 'axios';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AttemptPage } from './AttemptPage';
import { assessmentService } from '@/services/assessmentService';
import type { AssessmentResult, Attempt } from '@/types';

vi.mock('@/services/assessmentService', () => ({
  assessmentService: { startAttempt: vi.fn(), saveAnswers: vi.fn(), submit: vi.fn() },
}));

function conflict(detail: string): AxiosError {
  return new AxiosError('conflict', 'ERR_BAD_REQUEST', undefined, undefined, {
    status: 409,
    data: { detail },
  } as AxiosResponse);
}

function makeAttempt(overrides: Partial<Attempt> = {}): Attempt {
  return {
    id: 7,
    assessment_id: 3,
    attempt_no: 1,
    status: 'IN_PROGRESS',
    started_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
    answers: {},
    questions: [
      {
        id: 11,
        body: 'Pick one',
        options: [
          { id: 'a', text: 'Alpha' },
          { id: 'b', text: 'Beta' },
        ],
        marks: 1,
        position: 1,
        skill_id: 1,
        skill_name: 'Logic',
        multi_select: false,
      },
      {
        id: 12,
        body: 'Pick many',
        options: [
          { id: 'a', text: 'One' },
          { id: 'b', text: 'Two' },
        ],
        marks: 2,
        position: 2,
        skill_id: 1,
        skill_name: 'Logic',
        multi_select: true,
      },
    ],
    ...overrides,
  };
}

const result: AssessmentResult = {
  id: 1,
  attempt_id: 7,
  assessment_id: 3,
  assessment_title: 'T',
  assessment_version: 1,
  total_score: 1,
  max_score: 3,
  percentage: 33,
  per_skill_scores: [],
  computed_at: new Date().toISOString(),
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/assessments/3/attempt']}>
      <Routes>
        <Route path="/assessments/:id/attempt" element={<AttemptPage />} />
        <Route path="/attempts/:attemptId/result" element={<div>result page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('AttemptPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(assessmentService.saveAnswers).mockResolvedValue(1);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows the countdown timer', async () => {
    vi.mocked(assessmentService.startAttempt).mockResolvedValue(makeAttempt());
    renderPage();
    const timer = await screen.findByRole('timer');
    expect(timer).toHaveTextContent(/^(09:5\d|10:00)$/);
  });

  it('renders radios for single-select and checkboxes for multi-select', async () => {
    vi.mocked(assessmentService.startAttempt).mockResolvedValue(makeAttempt());
    renderPage();
    expect(await screen.findByRole('radio', { name: 'Alpha' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Go to question 2/ }));
    expect(screen.getByRole('checkbox', { name: 'One' })).toBeInTheDocument();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
  });

  it('auto-saves answers after a debounce', async () => {
    vi.mocked(assessmentService.startAttempt).mockResolvedValue(makeAttempt());
    renderPage();
    fireEvent.click(await screen.findByRole('radio', { name: 'Beta' }));
    expect(assessmentService.saveAnswers).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(assessmentService.saveAnswers).toHaveBeenCalledWith(7, { '11': ['b'] });
  });

  it('requires in-page confirmation before submitting', async () => {
    vi.mocked(assessmentService.startAttempt).mockResolvedValue(makeAttempt());
    vi.mocked(assessmentService.submit).mockResolvedValue(result);
    renderPage();
    fireEvent.click(await screen.findByRole('radio', { name: 'Alpha' }));
    fireEvent.click(screen.getByRole('button', { name: 'Submit attempt' }));
    expect(assessmentService.submit).not.toHaveBeenCalled();
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Keep working' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Submit attempt' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm submit' }));
    expect(await screen.findByText('result page')).toBeInTheDocument();
    expect(assessmentService.saveAnswers).toHaveBeenCalledWith(7, { '11': ['a'] });
    expect(assessmentService.submit).toHaveBeenCalledWith(7);
  });

  it('supports selecting several options on a multi-select question', async () => {
    vi.mocked(assessmentService.startAttempt).mockResolvedValue(makeAttempt());
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /Go to question 2/ }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'One' }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Two' }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(assessmentService.saveAnswers).toHaveBeenLastCalledWith(7, { '12': ['a', 'b'] });
  });

  it('shows the server message when starting hits a 409', async () => {
    vi.mocked(assessmentService.startAttempt).mockRejectedValue(conflict('Maximum attempts reached'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('Maximum attempts reached');
    expect(screen.getByRole('link', { name: 'Back to assessments' })).toBeInTheDocument();
  });

  it('handles a 409 while saving by locking the attempt and offering the result', async () => {
    vi.mocked(assessmentService.startAttempt).mockResolvedValue(makeAttempt());
    vi.mocked(assessmentService.saveAnswers).mockRejectedValue(conflict('Attempt already finished'));
    renderPage();
    fireEvent.click(await screen.findByRole('radio', { name: 'Alpha' }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(await screen.findByRole('alert')).toHaveTextContent('Attempt already finished');
    expect(screen.getByRole('link', { name: 'View result' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Beta' })).toBeDisabled();
  });

  it('auto-submits when the timer expires', async () => {
    vi.mocked(assessmentService.startAttempt).mockResolvedValue(
      makeAttempt({ expires_at: new Date(Date.now() + 2000).toISOString() }),
    );
    vi.mocked(assessmentService.submit).mockResolvedValue(result);
    renderPage();
    await screen.findByRole('timer');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3500);
    });
    await waitFor(() => expect(assessmentService.submit).toHaveBeenCalledWith(7));
    expect(await screen.findByText('result page')).toBeInTheDocument();
  });
});
