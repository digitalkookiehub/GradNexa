import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AssistantPage } from './AssistantPage';
import { assistantService } from '@/services/assistantService';
import { jobService } from '@/services/jobService';
import { roadmapService } from '@/services/roadmapService';
import { makeAxiosError } from '@/test/helpers';
import type { AssistantAnswer } from '@/types/assistant';

vi.mock('@/services/assistantService', () => ({ assistantService: { query: vi.fn() } }));
vi.mock('@/services/jobService', () => ({ jobService: { list: vi.fn() } }));
vi.mock('@/services/roadmapService', () => ({ roadmapService: { listRoles: vi.fn() } }));

const answer: AssistantAnswer = {
  question: 'q',
  answer_sections: [{ heading: 'Readiness', text: 'You are <script>alert(1)</script> at 60', facts: [{ label: 'Score', value: '60' }] }],
  citations: [{ document_id: 1, document_title: 'Handbook', source_type: 'POLICY', chunk_id: 9, chunk_index: 0, snippet: '<img src=x onerror=alert(1)>' }],
  tools_used: ['get_readiness'],
  intent: 'readiness',
  insufficient_evidence: false,
  llm_used: false,
  notes: ['Rule based note'],
};

describe('AssistantPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(roadmapService.listRoles).mockResolvedValue([
      { id: 1, department_id: null, name: 'Zed', description: null, is_active: true, is_goal: false },
      { id: 2, department_id: null, name: 'Goal Role', description: null, is_active: true, is_goal: true },
    ]);
    vi.mocked(jobService.list).mockResolvedValue([]);
  });

  it('shows the no-LLM note and puts goal roles first', async () => {
    render(<AssistantPage />);
    expect(screen.getByTestId('no-llm-note')).toHaveTextContent('No AI language model is used yet.');
    const opts = await screen.findAllByRole('option', { name: /Goal Role|Zed/ });
    expect(opts[0]).toHaveTextContent('Goal Role (your goal)');
  });

  it('asks, renders answer plainly with citations, notes and llm_used', async () => {
    vi.mocked(assistantService.query).mockResolvedValue(answer);
    render(<AssistantPage />);
    await userEvent.type(screen.getByLabelText('Your question'), 'How ready am I?');
    expect(screen.getByTestId('char-count')).toHaveTextContent('15/1000');
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(assistantService.query).toHaveBeenCalledWith({ question: 'How ready am I?' });
    expect(await screen.findByText('You are <script>alert(1)</script> at 60')).toBeInTheDocument();
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument();
    expect(screen.getByText('Handbook')).toBeInTheDocument();
    expect(screen.getByText('get_readiness')).toBeInTheDocument();
    expect(screen.getByText('Rule based note')).toBeInTheDocument();
    expect(screen.getByTestId('llm-used')).toHaveTextContent('Language model used: No');
    expect(document.querySelector('script, img')).toBeNull();
  });

  it('sends role and job ids', async () => {
    vi.mocked(assistantService.query).mockResolvedValue(answer);
    render(<AssistantPage />);
    await screen.findAllByRole('option', { name: /Goal Role/ });
    await userEvent.selectOptions(screen.getByLabelText('Career role (optional)'), '2');
    await userEvent.type(screen.getByLabelText('Your question'), 'x');
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(assistantService.query).toHaveBeenCalledWith({ question: 'x', role_id: 2 });
  });

  it('example chip fills the input', async () => {
    render(<AssistantPage />);
    await userEvent.click(screen.getByRole('button', { name: 'What should I study next?' }));
    expect(screen.getByLabelText('Your question')).toHaveValue('What should I study next?');
  });

  it('shows insufficient evidence message from API', async () => {
    vi.mocked(assistantService.query).mockResolvedValue({
      ...answer,
      insufficient_evidence: true,
      citations: [],
      answer_sections: [{ heading: '', text: 'Not enough approved evidence exists.', facts: [] }],
    });
    render(<AssistantPage />);
    await userEvent.type(screen.getByLabelText('Your question'), 'obscure');
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(await screen.findByText('Not enough approved evidence exists.')).toBeInTheDocument();
  });

  it('shows 409 and 422 errors', async () => {
    vi.mocked(assistantService.query).mockRejectedValueOnce(makeAxiosError(409, 'Complete your profile first.'));
    render(<AssistantPage />);
    await userEvent.type(screen.getByLabelText('Your question'), 'a');
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Complete your profile first.');
    vi.mocked(assistantService.query).mockRejectedValueOnce(makeAxiosError(422, 'Question too long'));
    await userEvent.type(screen.getByLabelText('Your question'), 'b');
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(await screen.findByText('Question too long')).toBeInTheDocument();
  });

  it('clears the conversation', async () => {
    vi.mocked(assistantService.query).mockResolvedValue(answer);
    render(<AssistantPage />);
    await userEvent.type(screen.getByLabelText('Your question'), 'hello');
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
    await screen.findByText('Readiness');
    await userEvent.click(screen.getByRole('button', { name: 'Clear conversation' }));
    expect(screen.queryByText('Readiness')).not.toBeInTheDocument();
  });
});
