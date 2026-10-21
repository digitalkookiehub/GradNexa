import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { GuidePage } from './GuidePage';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { extractSections, inlineRuns, isOpenableByAdmin, neighbours, OVERVIEW_ID, resolvePage, slugify, WRITTEN_ID } from '@/lib/guide';
import { guideService } from '@/services/guideService';
import { AuthStub, makeAxiosError, makeUser } from '@/test/helpers';
import type { Guide, GuideProcedure } from '@/types/guide';
import type { UserRole } from '@/types';

vi.mock('@/services/guideService', () => ({ guideService: { get: vi.fn() } }));

function proc(over: Partial<GuideProcedure> & Pick<GuideProcedure, 'id' | 'title'>): GuideProcedure {
  return { audience: 'Admin', path: null, summary: 'Summary.', before: [], steps: [], result: [], problems: [], terms: [], tables: [], ...over };
}

const guide: Guide = {
  title: 'GradNexa User Guide',
  tagline: 'From graduate to professional.',
  principles: ['Scores come from fixed rules.'],
  roles: [{ role: 'Student', does: 'Takes assessments.', lands: 'Dashboard' }],
  overview: [
    { id: 'setup', title: 'Admin sets up the college', summary: 'Skills and rules.', goto: 'a-skills' },
    { id: 'evidence', title: 'Student builds evidence', summary: 'Assessments.', goto: 's-readiness' },
  ],
  groups: [
    {
      id: 'admin',
      title: 'Admin: set up the college',
      procedures: [
        proc({
          id: 'a-skills',
          title: '1. Create skills',
          path: '/admin/skills',
          before: ['Departments exist.'],
          steps: [
            { do: 'Click **Skills** in the top menu.', expect: 'The **Skills** page opens.' },
            { do: 'Enter **Category name**, then click **Add category**.', detail: 'Choose a Scope first.' },
          ],
          result: ['A skill list.'],
          problems: [{ problem: 'Select a department.', fix: 'Set Scope to Common.' }],
        }),
        proc({ id: 'a-roles', title: '2. Create roles', path: '/admin/career-roles', steps: [{ do: 'Click **Career roles**.' }] }),
      ],
    },
    {
      id: 'student',
      title: 'Student: step by step',
      procedures: [proc({ id: 's-readiness', title: '7. See your readiness', audience: 'Student', path: '/readiness', steps: [{ do: 'Click **Readiness**.' }] })],
    },
    {
      id: 'config',
      title: 'College configuration (with samples)',
      intro: 'Values in the sample tables are examples only.',
      procedures: [
        proc({
          id: 'c-rule',
          title: 'Readiness rule',
          tables: [
            {
              title: 'Sample level thresholds',
              columns: ['Level name', 'Starts at (minimum score)'],
              rows: [['Needs improvement', '0'], ['Developing', '50'], ['Strong', '75']],
              caption: 'Example only.',
            },
          ],
        }),
      ],
    },
    {
      id: 'reference',
      title: 'Reference',
      procedures: [proc({ id: 'r-terms', title: 'What the numbers mean', terms: [{ term: 'Gap', meaning: 'max(required - yours, 0).' }] })],
    },
  ],
  markdown: ['# GradNexa User Guide', '', '## Part 1 - The big picture', '', 'Text.', '', '<script>window.__x = 1</script>'].join('\n'),
};

function renderAt(role: UserRole, url = '/guide') {
  return render(
    <AuthStub user={makeUser(role)}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
            <Route path="/guide" element={<GuidePage />} />
          </Route>
          <Route path="*" element={<p>elsewhere</p>} />
        </Routes>
      </MemoryRouter>
    </AuthStub>,
  );
}

describe('GuidePage (left sidebar, step-by-step)', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(guideService.get).mockResolvedValue(guide);
    window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('lists every section and procedure in a sidebar and opens on the overview', async () => {
    renderAt('ADMIN');
    const sidebar = await screen.findByRole('navigation', { name: 'Guide contents' });
    expect(within(sidebar).getByRole('heading', { name: 'Admin: set up the college' })).toBeInTheDocument();
    expect(within(sidebar).getByRole('heading', { name: 'Student: step by step' })).toBeInTheDocument();
    for (const title of ['1. Create skills', '2. Create roles', '7. See your readiness', 'What the numbers mean', 'Written guide (full text)']) {
      expect(within(sidebar).getByRole('button', { name: title })).toBeInTheDocument();
    }
    expect(within(sidebar).getByRole('button', { name: 'How the application works' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('heading', { level: 1, name: 'How the application works' })).toBeInTheDocument();
    expect(screen.getByRole('table')).toHaveTextContent('Takes assessments.');
  });

  it('shows numbered steps with bold UI names, expected results, results and troubleshooting', async () => {
    renderAt('ADMIN');
    const sidebar = await screen.findByRole('navigation', { name: 'Guide contents' });
    await userEvent.click(within(sidebar).getByRole('button', { name: '1. Create skills' }));
    expect(screen.getByRole('heading', { level: 1, name: '1. Create skills' })).toBeInTheDocument();
    expect(screen.getByText('Departments exist.')).toBeInTheDocument();
    const steps = screen.getAllByRole('listitem').filter((li) => li.textContent?.includes('Step '));
    expect(steps).toHaveLength(2);
    expect(screen.getAllByText('Skills', { selector: 'strong' }).length).toBeGreaterThan(0);
    expect(screen.getByText(/You should see:/)).toBeInTheDocument();
    expect(screen.getByText('Choose a Scope first.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'When you are done' })).toBeInTheDocument();
    expect(screen.getByText('Select a department.')).toBeInTheDocument();
    expect(screen.getByText('Set Scope to Common.')).toBeInTheDocument();
    expect(sidebar).toBeInTheDocument();
  });

  it('opens a procedure straight from the URL and falls back to the overview for unknown ids', async () => {
    renderAt('ADMIN', '/guide?p=a-roles');
    expect(await screen.findByRole('heading', { level: 1, name: '2. Create roles' })).toBeInTheDocument();
  });

  it('falls back to the overview for an unknown page id', async () => {
    renderAt('ADMIN', '/guide?p=nope');
    expect(await screen.findByRole('heading', { level: 1, name: 'How the application works' })).toBeInTheDocument();
  });

  it('moves with the Previous and Next buttons in sidebar order', async () => {
    renderAt('ADMIN', '/guide?p=a-skills');
    await screen.findByRole('heading', { level: 1, name: '1. Create skills' });
    await userEvent.click(screen.getByRole('button', { name: /Next: 2\. Create roles/ }));
    expect(screen.getByRole('heading', { level: 1, name: '2. Create roles' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Previous: 1\. Create skills/ }));
    expect(screen.getByRole('heading', { level: 1, name: '1. Create skills' })).toBeInTheDocument();
  });

  it('jumps to a procedure from the overview flow', async () => {
    renderAt('ADMIN');
    await userEvent.click(await screen.findByRole('button', { name: /Student builds evidence/ }));
    expect(screen.getByRole('heading', { level: 1, name: '7. See your readiness' })).toBeInTheDocument();
  });

  it('lets the reader tick steps off', async () => {
    renderAt('ADMIN', '/guide?p=a-skills');
    await screen.findByRole('heading', { level: 1, name: '1. Create skills' });
    expect(screen.getByText(/0 of 2 ticked off/)).toBeInTheDocument();
    const first = screen.getByRole('button', { name: 'Mark step 1 done' });
    await userEvent.click(first);
    expect(first).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText(/1 of 2 ticked off/)).toBeInTheDocument();
  });

  it('offers Open this page for pages an admin can open', async () => {
    renderAt('ADMIN', '/guide?p=a-skills');
    expect(await screen.findByRole('link', { name: /Open this page/ })).toHaveAttribute('href', '/admin/skills');
  });

  it('does not offer Open this page for student-only pages', async () => {
    renderAt('ADMIN', '/guide?p=s-readiness');
    expect(await screen.findByRole('heading', { level: 1, name: '7. See your readiness' })).toBeInTheDocument();
    expect(screen.getByText('/readiness')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Open this page/ })).toBeNull();
  });

  it('renders sample tables with headers, rows and a caption', async () => {
    renderAt('ADMIN', '/guide?p=c-rule');
    const table = await screen.findByRole('table', { name: '' });
    expect(within(table).getByRole('columnheader', { name: 'Level name' })).toBeInTheDocument();
    expect(within(table).getByRole('cell', { name: 'Developing' })).toBeInTheDocument();
    expect(within(table).getAllByRole('row')).toHaveLength(4);
    expect(screen.getByText('Sample level thresholds')).toBeInTheDocument();
    expect(screen.getByText('Example only.')).toBeInTheDocument();
  });

  it('shows the section intro above a procedure', async () => {
    renderAt('ADMIN', '/guide?p=c-rule');
    expect(await screen.findByText('Values in the sample tables are examples only.')).toBeInTheDocument();
  });

  it('lists the configuration section in the sidebar', async () => {
    renderAt('ADMIN');
    const sidebar = await screen.findByRole('navigation', { name: 'Guide contents' });
    expect(within(sidebar).getByRole('heading', { name: 'College configuration (with samples)' })).toBeInTheDocument();
    expect(within(sidebar).getByRole('button', { name: 'Readiness rule' })).toBeInTheDocument();
  });

  it('shows glossary pages as definitions', async () => {
    renderAt('ADMIN', '/guide?p=r-terms');
    expect(await screen.findByText('Gap')).toBeInTheDocument();
    expect(screen.getByText('max(required - yours, 0).')).toBeInTheDocument();
  });

  it('shows the written guide without rendering raw HTML', async () => {
    const { container } = renderAt('ADMIN', `/guide?p=${WRITTEN_ID}`);
    expect(await screen.findByRole('heading', { level: 2, name: 'Part 1 - The big picture' })).toBeInTheDocument();
    expect(container.querySelector('script')).toBeNull();
  });

  it.each<UserRole>(['STUDENT', 'FACULTY', 'TPO', 'HOD'])('redirects %s away without loading the guide', async (role) => {
    renderAt(role);
    expect(await screen.findByText('elsewhere')).toBeInTheDocument();
    expect(guideService.get).not.toHaveBeenCalled();
  });

  it('shows an error and retries', async () => {
    vi.mocked(guideService.get).mockRejectedValueOnce(makeAxiosError(500, 'boom'));
    renderAt('ADMIN');
    expect(await screen.findByText('boom')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('navigation', { name: 'Guide contents' })).toBeInTheDocument();
    expect(guideService.get).toHaveBeenCalledTimes(2);
  });
});

describe('guide helpers', () => {
  it('slugifies headings and extracts sections outside code fences', () => {
    expect(slugify('Part 4 - Student guide')).toBe('part-4-student-guide');
    expect(extractSections('## A\n```\n## nope\n```\n## B').map((s) => s.title)).toEqual(['A', 'B']);
  });

  it('splits **bold** UI names from plain text and never interprets HTML', () => {
    expect(inlineRuns('Click **Save** now')).toEqual([
      { text: 'Click ', bold: false },
      { text: 'Save', bold: true },
      { text: ' now', bold: false },
    ]);
    expect(inlineRuns('<b>x</b>')).toEqual([{ text: '<b>x</b>', bold: false }]);
  });

  it('computes sidebar order, neighbours and fallbacks', () => {
    expect(neighbours(guide, OVERVIEW_ID)).toEqual({ prev: null, next: 'a-skills' });
    expect(neighbours(guide, 'a-roles')).toEqual({ prev: 'a-skills', next: 's-readiness' });
    expect(neighbours(guide, WRITTEN_ID).next).toBeNull();
    expect(resolvePage(guide, 'a-roles')).toBe('a-roles');
    expect(resolvePage(guide, 'nope')).toBe(OVERVIEW_ID);
    expect(resolvePage(guide, null)).toBe(OVERVIEW_ID);
  });

  it('decides which pages the admin can open', () => {
    expect(isOpenableByAdmin('/admin/skills')).toBe(true);
    expect(isOpenableByAdmin('/placement')).toBe(true);
    expect(isOpenableByAdmin('/readiness')).toBe(false);
    expect(isOpenableByAdmin(null)).toBe(false);
  });
});
