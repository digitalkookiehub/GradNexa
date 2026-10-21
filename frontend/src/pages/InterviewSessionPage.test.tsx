import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { InterviewSessionPage } from './InterviewSessionPage';
import { interviewService } from '@/services/interviewService';
import { makeAxiosError } from '@/test/helpers';
import type { Interview, InterviewResult } from '@/types';

vi.mock('@/services/interviewService', () => ({
  interviewService: { get: vi.fn(), saveAnswers: vi.fn(), finish: vi.fn() },
}));

const interview: Interview = {
  id: 9,
  role_id: 1,
  role_name: 'Backend Dev',
  status: 'IN_PROGRESS',
  started_at: '2026-01-01T00:00:00Z',
  completed_at: null,
  questions: [
    { answer_id: 101, question_id: 1, position: 1, competency: 'Databases', prompt: 'Explain indexes.', min_words: 20, answer_text: null },
    { answer_id: 102, question_id: 2, position: 2, competency: 'APIs', prompt: 'Explain REST.', min_words: 10, answer_text: 'Saved earlier' },
  ],
};

const result: InterviewResult = {
  id: 1,
  interview_id: 9,
  role_name: 'Backend Dev',
  overall: 50,
  competency_scores: [],
  per_question: [],
  computed_at: '2026-01-01T00:00:00Z',
  scoring_version: 1,
  disclaimer: 'x',
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/interview/9']}>
      <Routes>
        <Route path="/interview/:id" element={<InterviewSessionPage />} />
        <Route path="/interview/:id/result" element={<div>result page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('InterviewSessionPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(interviewService.get).mockResolvedValue(interview);
    vi.mocked(interviewService.saveAnswers).mockResolvedValue(undefined);
  });
  afterEach(() => vi.useRealTimers());

  it('shows competency, min-words hint and a live word count', async () => {
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByTestId('competency')).toHaveTextContent('Databases');
    expect(screen.getByTestId('word-count')).toHaveTextContent('0 words');
    expect(screen.getByTestId('word-count')).toHaveTextContent('at least 20');
    await user.type(screen.getByLabelText('Explain indexes.'), 'one two three');
    expect(screen.getByTestId('word-count')).toHaveTextContent('3 words');
  });

  it('autosaves after a debounce and shows Saved', async () => {
    renderPage();
    const box = await screen.findByLabelText('Explain indexes.');
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    await user.type(box, 'abc');
    expect(interviewService.saveAnswers).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(interviewService.saveAnswers).toHaveBeenCalledWith(9, [
      { answer_id: 101, answer_text: 'abc' },
      { answer_id: 102, answer_text: 'Saved earlier' },
    ]);
    expect(await screen.findByText('Saved')).toBeInTheDocument();
  });

  it('shows Not saved when autosave fails', async () => {
    vi.mocked(interviewService.saveAnswers).mockRejectedValue(makeAxiosError(500, 'db down'));
    renderPage();
    const box = await screen.findByLabelText('Explain indexes.');
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    await user.type(box, 'abc');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(await screen.findByText('Not saved')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('db down');
  });

  it('navigates between questions', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByLabelText('Explain indexes.');
    await user.click(screen.getByRole('button', { name: /Go to question 2/ }));
    expect(screen.getByLabelText('Explain REST.')).toHaveValue('Saved earlier');
  });

  it('finishes only after in-page confirmation', async () => {
    const user = userEvent.setup();
    vi.mocked(interviewService.finish).mockResolvedValue(result);
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Finish interview' }));
    expect(interviewService.finish).not.toHaveBeenCalled();
    expect(screen.getByRole('alertdialog')).toHaveTextContent('1 of 2 questions');
    await user.click(screen.getByRole('button', { name: 'Confirm finish' }));
    expect(interviewService.finish).toHaveBeenCalledWith(9);
    expect(await screen.findByText('result page')).toBeInTheDocument();
  });

  it('can cancel the confirmation', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Finish interview' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(interviewService.finish).not.toHaveBeenCalled();
  });

  it('redirects to the result on a 409 from finish', async () => {
    const user = userEvent.setup();
    vi.mocked(interviewService.finish).mockRejectedValue(makeAxiosError(409, 'already finished'));
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Finish interview' }));
    await user.click(screen.getByRole('button', { name: 'Confirm finish' }));
    expect(await screen.findByText('result page')).toBeInTheDocument();
  });

  it('redirects completed interviews to the result', async () => {
    vi.mocked(interviewService.get).mockResolvedValueOnce({ ...interview, status: 'COMPLETED' });
    renderPage();
    expect(await screen.findByText('result page')).toBeInTheDocument();
  });

  it('shows an alert when loading fails', async () => {
    vi.mocked(interviewService.get).mockRejectedValue(makeAxiosError(404, 'Interview not found'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('Interview not found');
  });
});
