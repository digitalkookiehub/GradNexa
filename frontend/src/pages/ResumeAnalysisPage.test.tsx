import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ResumeAnalysisPage } from './ResumeAnalysisPage';
import { resumeService } from '@/services/resumeService';
import { makeAxiosError } from '@/test/helpers';
import type { ResumeAnalysis } from '@/types/resume';

vi.mock('@/services/resumeService', () => ({
  resumeService: { getAnalysis: vi.fn(), getText: vi.fn(), listAnalyses: vi.fn() },
}));

const TEXT = 'Skills: Python, SQL\nEducation\nB.Tech in CS from XYZ\nPython projects';
const pyFirst = TEXT.indexOf('Python');
const pySecond = TEXT.lastIndexOf('Python');
const sqlAt = TEXT.indexOf('SQL');
const eduAt = TEXT.indexOf('B.Tech');
const eduText = 'B.Tech in CS from XYZ';

function makeAnalysis(overrides: Partial<ResumeAnalysis> = {}): ResumeAnalysis {
  return {
    id: 9,
    resume_id: 1,
    role_id: 5,
    role_name: 'Backend Engineer',
    extractor_version: 'v1',
    created_at: '2026-01-01T00:00:00Z',
    extracted: {
      sections_found: ['Skills', 'Education'],
      skills: [
        {
          skill_id: 1,
          skill_name: 'Python',
          spans: [
            { start: pyFirst, end: pyFirst + 6, text: 'Python' },
            { start: pySecond, end: pySecond + 6, text: 'Python' },
          ],
        },
        { skill_id: 2, skill_name: 'SQL', spans: [{ start: sqlAt, end: sqlAt + 3, text: 'SQL' }] },
      ],
      education: [{ text: eduText, span: { start: eduAt, end: eduAt + eduText.length, text: eduText } }],
      projects: [],
      experience: [],
      certifications: [],
    },
    role_match: {
      match_percent: 66.7,
      found: [{ skill_id: 1, skill_name: 'Python', required_level: 3, weight: 1 }],
      missing: [{ skill_id: 3, skill_name: 'Docker', required_level: 2, weight: 1 }],
    },
    jd_match: { match_percent: 50, skills_in_jd: [{ skill_id: 1, skill_name: 'Python', in_resume: true }, { skill_id: 4, skill_name: 'Kafka', in_resume: false }] },
    notes: ['Only part of the resume could be read.'],
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/resume/1/analysis']}>
      <Routes>
        <Route path="/resume/:id/analysis" element={<ResumeAnalysisPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ResumeAnalysisPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(resumeService.getAnalysis).mockResolvedValue(makeAnalysis());
    vi.mocked(resumeService.getText).mockResolvedValue(TEXT);
    vi.mocked(resumeService.listAnalyses).mockResolvedValue([
      { id: 9, created_at: '2026-01-01T00:00:00Z', role_name: 'Backend Engineer', has_jd: true, role_match_percent: 66.7 },
    ]);
  });

  it('renders matches, missing list with link, jd flags, notes and history', async () => {
    renderPage();
    expect(await screen.findByTestId('role-match-percent')).toHaveTextContent('66.7%');
    expect(screen.getByTestId('jd-match-percent')).toHaveTextContent('50%');
    const missing = screen.getByRole('list', { name: 'Role skills missing' });
    expect(within(missing).getByText('Docker')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /role's skills/ })).toHaveAttribute('href', '/careers/5');
    expect(screen.getByText('Not in resume')).toBeInTheDocument();
    expect(screen.getByText('In resume')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Only part of the resume could be read.');
    expect(screen.getByText(/not a readiness score/)).toBeInTheDocument();
    expect(screen.getByRole('list', { name: 'Analysis history' })).toHaveTextContent('role match 66.7%');
    expect(screen.getByRole('list', { name: 'Education' })).toHaveTextContent(eduText);
  });

  it('highlights exact slices of the text for every span', async () => {
    renderPage();
    const source = await screen.findByTestId('source-text');
    expect(source.textContent).toBe(TEXT);
    const marks = Array.from(source.querySelectorAll('mark')).map((m) => m.textContent);
    expect(marks).toEqual(['Python', 'SQL', eduText, 'Python']);
  });

  it('marks only the selected skill spans as active', async () => {
    const user = userEvent.setup();
    renderPage();
    const source = await screen.findByTestId('source-text');
    await user.click(screen.getByRole('button', { name: /^SQL/ }));
    const active = Array.from(source.querySelectorAll('mark[data-active="true"]')).map((m) => m.textContent);
    expect(active).toEqual(['SQL']);
    await user.click(screen.getByRole('button', { name: /^Python/ }));
    expect(source.querySelectorAll('mark[data-active="true"]')).toHaveLength(2);
    await user.click(screen.getByRole('button', { name: eduText }));
    expect(Array.from(source.querySelectorAll('mark[data-active="true"]')).map((m) => m.textContent)).toEqual([eduText]);
  });

  it('ignores out-of-range spans without crashing and keeps text intact', async () => {
    const analysis = makeAnalysis();
    analysis.extracted.skills[1].spans = [{ start: 5, end: 9999, text: 'bad' }];
    vi.mocked(resumeService.getAnalysis).mockResolvedValue(analysis);
    renderPage();
    const source = await screen.findByTestId('source-text');
    expect(source.textContent).toBe(TEXT);
    expect(Array.from(source.querySelectorAll('mark')).map((m) => m.textContent)).not.toContain('bad');
  });

  it('shows an empty state when there is no analysis yet', async () => {
    vi.mocked(resumeService.getAnalysis).mockRejectedValue(makeAxiosError(404, 'none'));
    vi.mocked(resumeService.listAnalyses).mockResolvedValue([]);
    renderPage();
    expect(await screen.findByTestId('no-analysis')).toBeInTheDocument();
  });

  it('shows an error when loading fails', async () => {
    vi.mocked(resumeService.getAnalysis).mockRejectedValue(makeAxiosError(500, 'server down'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('server down');
  });

  it('shows a source text error without hiding the analysis', async () => {
    vi.mocked(resumeService.getText).mockRejectedValue(makeAxiosError(500, 'no text'));
    renderPage();
    expect(await screen.findByTestId('role-match-percent')).toBeInTheDocument();
    expect(screen.getAllByRole('alert').some((a) => a.textContent === 'no text')).toBe(true);
  });

  it('handles empty extracted text', async () => {
    vi.mocked(resumeService.getText).mockResolvedValue('');
    renderPage();
    expect(await screen.findByText(/nothing to highlight/)).toBeInTheDocument();
  });

  it('renders null match percent as not enough data', async () => {
    const a = makeAnalysis();
    a.role_match = { match_percent: null, found: [], missing: [] };
    vi.mocked(resumeService.getAnalysis).mockResolvedValue(a);
    renderPage();
    expect(await screen.findByTestId('role-match-percent')).toHaveTextContent('Not enough data');
  });
});
