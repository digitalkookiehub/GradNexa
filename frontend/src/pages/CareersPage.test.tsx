import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CareersPage } from './CareersPage';
import { roadmapService } from '@/services/roadmapService';
import { studentService } from '@/services/studentService';
import type { ExplorerRole } from '@/types';

vi.mock('@/services/roadmapService', () => ({
  roadmapService: { listRoles: vi.fn(), getGoals: vi.fn(), saveGoals: vi.fn() },
}));
vi.mock('@/services/studentService', () => ({ studentService: { listDepartments: vi.fn() } }));

function role(id: number, name: string, isGoal = false): ExplorerRole {
  return { id, department_id: 1, name, description: `${name} desc`, is_active: true, is_goal: isGoal };
}

describe('CareersPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(roadmapService.listRoles).mockResolvedValue([role(1, 'Backend Engineer', true), role(2, 'Data Analyst'), role(3, 'QA Engineer')]);
    vi.mocked(roadmapService.getGoals).mockResolvedValue([{ career_role_id: 1, role_name: 'Backend Engineer', priority: 1 }]);
    vi.mocked(roadmapService.saveGoals).mockResolvedValue();
    vi.mocked(studentService.listDepartments).mockResolvedValue([{ id: 1, name: 'Computer Science', code: 'CSE' }]);
  });

  function renderPage() {
    return render(
      <MemoryRouter>
        <CareersPage />
      </MemoryRouter>,
    );
  }

  it('lists roles with department and filters by search', async () => {
    renderPage();
    expect(await screen.findByRole('link', { name: 'Data Analyst' })).toHaveAttribute('href', '/careers/2');
    expect(screen.getAllByText('Computer Science').length).toBe(3);
    await userEvent.type(screen.getByLabelText('Search roles'), 'qa');
    expect(screen.queryByRole('link', { name: 'Data Analyst' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'QA Engineer' })).toBeInTheDocument();
  });

  it('toggles goals, reorders them and saves the new priorities', async () => {
    renderPage();
    await screen.findByRole('link', { name: 'Data Analyst' });
    await userEvent.click(screen.getByRole('button', { name: 'Add Data Analyst to my goals' }));
    const list = screen.getByRole('list', { name: 'Goal priority order' });
    expect(within(list).getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Move Data Analyst up' }));
    const items = within(screen.getByRole('list', { name: 'Goal priority order' })).getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('Data Analyst');

    await userEvent.click(screen.getByRole('button', { name: 'Save goals' }));
    expect(roadmapService.saveGoals).toHaveBeenCalledWith([
      { career_role_id: 2, priority: 1 },
      { career_role_id: 1, priority: 2 },
    ]);
    expect(await screen.findByText('Goals saved.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save goals' })).toBeDisabled();
  });

  it('removes a goal from the panel and shows save errors', async () => {
    vi.mocked(roadmapService.saveGoals).mockRejectedValue(new Error('boom'));
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Remove Backend Engineer' }));
    expect(screen.getByText(/No goals yet/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Save goals' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
  });

  it('shows an error with retry when loading fails', async () => {
    vi.mocked(roadmapService.listRoles).mockRejectedValueOnce(new Error('down'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('down');
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByRole('link', { name: 'Data Analyst' })).toBeInTheDocument();
  });
});
