import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { InterviewPage } from './InterviewPage';
import { interviewService } from '@/services/interviewService';
import { roadmapService } from '@/services/roadmapService';
import { makeAxiosError } from '@/test/helpers';
import type { ExplorerRole, Interview } from '@/types';

vi.mock('@/services/interviewService', () => ({ interviewService: { start: vi.fn(), list: vi.fn() } }));
vi.mock('@/services/roadmapService', () => ({ roadmapService: { listRoles: vi.fn() } }));

const roles: ExplorerRole[] = [
  { id: 1, department_id: null, name: 'Alpha Role', description: null, is_active: true, is_goal: false },
  { id: 2, department_id: null, name: 'Zed Role', description: null, is_active: true, is_goal: true },
];

const started: Interview = {
  id: 77,
  role_id: 2,
  role_name: 'Zed Role',
  status: 'IN_PROGRESS',
  started_at: '2026-01-01T00:00:00Z',
  completed_at: null,
  questions: [],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/interview']}>
      <Routes>
        <Route path="/interview" element={<InterviewPage />} />
        <Route path="/interview/:id" element={<div>session page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('InterviewPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(roadmapService.listRoles).mockResolvedValue(roles);
    vi.mocked(interviewService.list).mockResolvedValue([]);
  });

  it('lists career-goal roles first and starts an interview', async () => {
    const user = userEvent.setup();
    vi.mocked(interviewService.start).mockResolvedValue(started);
    renderPage();
    const select = await screen.findByLabelText('Role');
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.textContent);
    expect(options).toEqual(['Zed Role (career goal)', 'Alpha Role']);
    await user.clear(screen.getByLabelText(/Number of questions/));
    await user.type(screen.getByLabelText(/Number of questions/), '3');
    await user.click(screen.getByRole('button', { name: 'Start' }));
    expect(interviewService.start).toHaveBeenCalledWith(2, 3);
    expect(await screen.findByText('session page')).toBeInTheDocument();
  });

  it('shows the 409 message when no questions are configured', async () => {
    const user = userEvent.setup();
    vi.mocked(interviewService.start).mockRejectedValue(makeAxiosError(409, 'No interview questions configured for this role'));
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Start' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No interview questions configured for this role');
  });

  it('shows history with links to results and resume links', async () => {
    vi.mocked(interviewService.list).mockResolvedValue([
      { id: 5, role_id: 1, role_name: 'Alpha Role', status: 'COMPLETED', started_at: '2026-01-01T00:00:00Z', completed_at: '2026-01-01T01:00:00Z', overall: 61 },
      { id: 6, role_id: 2, role_name: 'Zed Role', status: 'IN_PROGRESS', started_at: '2026-01-02T00:00:00Z', completed_at: null, overall: null },
    ]);
    renderPage();
    expect(await screen.findByRole('link', { name: 'View result' })).toHaveAttribute('href', '/interview/5/result');
    expect(screen.getByRole('link', { name: 'Continue' })).toHaveAttribute('href', '/interview/6');
    expect(screen.getByTestId('in-progress-note')).toBeInTheDocument();
  });

  it('shows empty history', async () => {
    renderPage();
    expect(await screen.findByTestId('no-history')).toBeInTheDocument();
  });

  it('shows an alert with retry when loading fails', async () => {
    const user = userEvent.setup();
    vi.mocked(roadmapService.listRoles).mockRejectedValueOnce(makeAxiosError(500, 'boom'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(screen.getByLabelText('Role')).toBeInTheDocument());
  });
});
