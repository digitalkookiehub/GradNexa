import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProjectsPanel } from './ProjectsPanel';
import { studentService } from '@/services/studentService';

vi.mock('@/services/studentService', () => ({
  studentService: { listProjects: vi.fn(), createProject: vi.fn(), deleteProject: vi.fn() },
}));

const mocked = vi.mocked(studentService);

describe('ProjectsPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocked.listProjects.mockResolvedValue([]);
  });

  it('requires a title', async () => {
    render(<ProjectsPanel />);
    await screen.findByText('No projects yet.');
    await userEvent.click(screen.getByRole('button', { name: 'Add project' }));
    expect(screen.getByText('Title is required.')).toBeInTheDocument();
    expect(mocked.createProject).not.toHaveBeenCalled();
  });

  it('adds a project with comma-separated skill tags', async () => {
    mocked.createProject.mockResolvedValue({ id: 7, title: 'Chat App', description: null, skills: ['React', 'Node'], url: null });
    render(<ProjectsPanel />);
    await screen.findByText('No projects yet.');
    await userEvent.type(screen.getByLabelText('Title'), 'Chat App');
    await userEvent.type(screen.getByLabelText('Skills'), 'React,Node,');
    await userEvent.click(screen.getByRole('button', { name: 'Add project' }));
    await screen.findByText('Chat App');
    expect(mocked.createProject).toHaveBeenCalledWith({ title: 'Chat App', description: null, skills: ['React', 'Node'], url: null });
  });

  it('deletes a project', async () => {
    mocked.listProjects.mockResolvedValue([{ id: 3, title: 'Old', description: null, skills: [], url: null }]);
    mocked.deleteProject.mockResolvedValue(undefined);
    render(<ProjectsPanel />);
    await userEvent.click(await screen.findByRole('button', { name: 'Delete project Old' }));
    await waitFor(() => expect(screen.queryByText('Old')).not.toBeInTheDocument());
    expect(mocked.deleteProject).toHaveBeenCalledWith(3);
  });

  it('shows the server error when delete fails and keeps the item', async () => {
    mocked.listProjects.mockResolvedValue([{ id: 3, title: 'Old', description: null, skills: [], url: null }]);
    mocked.deleteProject.mockRejectedValue(new Error('Not allowed'));
    render(<ProjectsPanel />);
    await userEvent.click(await screen.findByRole('button', { name: 'Delete project Old' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Not allowed');
    expect(screen.getByText('Old')).toBeInTheDocument();
  });
});
