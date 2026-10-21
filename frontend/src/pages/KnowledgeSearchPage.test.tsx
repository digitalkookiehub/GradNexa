import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KnowledgeSearchPage } from './KnowledgeSearchPage';
import { knowledgeService } from '@/services/knowledgeService';
import { makeAxiosError } from '@/test/helpers';

vi.mock('@/services/knowledgeService', () => ({ knowledgeService: { search: vi.fn() } }));

describe('KnowledgeSearchPage', () => {
  beforeEach(() => vi.resetAllMocks());

  it('renders passages as plain text with citation info', async () => {
    vi.mocked(knowledgeService.search).mockResolvedValue({
      query: 'q',
      insufficient_evidence: false,
      message: null,
      passages: [{ document_id: 1, document_title: 'Course Doc', source_type: 'SYLLABUS', chunk_id: 1, chunk_index: 0, snippet: '<b>bold?</b>', score: 1, query_coverage: 1 }],
    });
    render(<KnowledgeSearchPage />);
    await userEvent.type(screen.getByLabelText('Search'), 'python');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));
    expect(await screen.findByText('<b>bold?</b>')).toBeInTheDocument();
    expect(screen.getByText('Course Doc')).toBeInTheDocument();
    expect(screen.getByText('Syllabus', { selector: 'p.text-xs' })).toBeInTheDocument();
  });

  it('shows the API insufficient-evidence message exactly', async () => {
    vi.mocked(knowledgeService.search).mockResolvedValue({ query: 'q', insufficient_evidence: true, message: 'No approved document covers this.', passages: [] });
    render(<KnowledgeSearchPage />);
    await userEvent.type(screen.getByLabelText('Search'), 'zzz');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));
    expect(await screen.findByText('No approved document covers this.')).toBeInTheDocument();
  });

  it('shows errors and rejects empty queries', async () => {
    render(<KnowledgeSearchPage />);
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Enter something');
    vi.mocked(knowledgeService.search).mockRejectedValue(makeAxiosError(500, 'fail'));
    await userEvent.type(screen.getByLabelText('Search'), 'a');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));
    expect(await screen.findByText('fail')).toBeInTheDocument();
  });
});
