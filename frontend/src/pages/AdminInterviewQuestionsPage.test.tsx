import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminInterviewQuestionsPage } from './AdminInterviewQuestionsPage';
import { adminInterviewService } from '@/services/adminInterviewService';
import { assessmentService } from '@/services/assessmentService';
import { readinessService } from '@/services/readinessService';
import type { BankQuestion } from '@/types';

vi.mock('@/services/adminInterviewService', () => ({
  adminInterviewService: { list: vi.fn(), create: vi.fn(), update: vi.fn(), deactivate: vi.fn() },
}));
vi.mock('@/services/assessmentService', () => ({ assessmentService: { listSkills: vi.fn() } }));
vi.mock('@/services/readinessService', () => ({ readinessService: { listRoles: vi.fn() } }));

const bank: BankQuestion = {
  id: 4,
  role_id: 1,
  role_name: 'Backend Dev',
  skill_id: null,
  competency: 'Databases',
  prompt: 'Explain indexes.',
  rubric: [{ concept: 'B-tree', keywords: ['btree'], weight: 1 }],
  min_words: 20,
  is_active: true,
  created_by: 1,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminInterviewQuestionsPage />
    </MemoryRouter>,
  );
}

async function openForm(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.click(await screen.findByRole('button', { name: 'New question' }));
  await user.type(screen.getByLabelText('Competency'), 'APIs');
  await user.type(screen.getByLabelText('Prompt'), 'Explain REST.');
}

describe('AdminInterviewQuestionsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminInterviewService.list).mockResolvedValue([bank]);
    vi.mocked(readinessService.listRoles).mockResolvedValue([{ id: 1, department_id: null, name: 'Backend Dev', description: null, is_active: true }]);
    vi.mocked(assessmentService.listSkills).mockResolvedValue([]);
    vi.mocked(adminInterviewService.create).mockResolvedValue(bank);
    vi.mocked(adminInterviewService.deactivate).mockResolvedValue(undefined);
  });

  it('lists questions and applies filters', async () => {
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByText('Explain indexes.')).toBeInTheDocument();
    await screen.findByRole('option', { name: 'Backend Dev' });
    await user.selectOptions(screen.getByLabelText('Filter by role'), '1');
    await user.selectOptions(screen.getByLabelText('Status'), 'true');
    expect(adminInterviewService.list).toHaveBeenLastCalledWith({ role_id: 1, active: true });
  });

  it('shows the empty state', async () => {
    vi.mocked(adminInterviewService.list).mockResolvedValue([]);
    renderPage();
    expect(await screen.findByTestId('no-questions')).toBeInTheDocument();
  });

  it('requires at least one concept', async () => {
    const user = userEvent.setup();
    renderPage();
    await openForm(user);
    await user.click(screen.getByRole('button', { name: 'Remove concept 1' }));
    await user.click(screen.getByRole('button', { name: 'Create question' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('at least one rubric concept');
    expect(adminInterviewService.create).not.toHaveBeenCalled();
  });

  it('requires a keyword per concept and a positive weight', async () => {
    const user = userEvent.setup();
    renderPage();
    await openForm(user);
    await user.type(screen.getByLabelText('Concept 1 name'), 'Stateless');
    await user.click(screen.getByRole('button', { name: 'Create question' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Concept 1 needs at least one keyword');
    await user.type(screen.getByLabelText('Concept 1 keywords'), 'stateless,');
    await user.clear(screen.getByLabelText('Concept 1 weight'));
    await user.type(screen.getByLabelText('Concept 1 weight'), '0');
    await user.click(screen.getByRole('button', { name: 'Create question' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('weight greater than 0');
    expect(adminInterviewService.create).not.toHaveBeenCalled();
  });

  it('submits a valid question', async () => {
    const user = userEvent.setup();
    renderPage();
    await openForm(user);
    await user.type(screen.getByLabelText('Concept 1 name'), 'Stateless');
    await user.type(screen.getByLabelText('Concept 1 keywords'), 'stateless,');
    await user.click(screen.getByRole('button', { name: 'Create question' }));
    expect(adminInterviewService.create).toHaveBeenCalledWith({
      role_id: null,
      skill_id: null,
      competency: 'APIs',
      prompt: 'Explain REST.',
      min_words: 30,
      rubric: [{ concept: 'Stateless', keywords: ['stateless'], weight: 1 }],
    });
  });

  it('deactivates only after in-page confirmation', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /Deactivate Explain indexes/ }));
    expect(adminInterviewService.deactivate).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Deactivate' }));
    expect(adminInterviewService.deactivate).toHaveBeenCalledWith(4);
  });
});
