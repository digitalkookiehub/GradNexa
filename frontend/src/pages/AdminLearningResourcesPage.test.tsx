import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminLearningResourcesPage } from './AdminLearningResourcesPage';
import { adminResourceService } from '@/services/adminResourceService';
import { assessmentService } from '@/services/assessmentService';
import { AuthStub, makeUser } from '@/test/helpers';
import type { AdminLearningResource, UserRole } from '@/types';

vi.mock('@/services/adminResourceService', () => ({
  adminResourceService: { list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn(), approve: vi.fn(), unapprove: vi.fn() },
}));
vi.mock('@/services/assessmentService', () => ({ assessmentService: { listSkills: vi.fn() } }));

const resource: AdminLearningResource = {
  id: 5,
  skill_id: 1,
  skill_name: 'Python',
  title: 'Python Tutorial',
  url: 'https://example.com/py',
  description: null,
  is_approved: false,
  approved_by: null,
  approved_at: null,
  created_by: 2,
};

function renderPage(role: UserRole) {
  return render(
    <AuthStub user={makeUser(role)}>
      <AdminLearningResourcesPage />
    </AuthStub>,
  );
}

describe('AdminLearningResourcesPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(assessmentService.listSkills).mockResolvedValue([{ id: 1, name: 'Python', description: null, category_id: 1, category_name: 'Tech' }]);
    vi.mocked(adminResourceService.list).mockResolvedValue([resource]);
  });

  it('rejects non-http URLs and accepts a valid one', async () => {
    vi.mocked(adminResourceService.create).mockResolvedValue(resource);
    renderPage('FACULTY');
    await screen.findByText('Python Tutorial');
    await screen.findAllByRole('option', { name: 'Python' });
    await userEvent.selectOptions(screen.getByLabelText('Skill'), '1');
    await userEvent.type(screen.getByLabelText('Title'), 'New one');
    await userEvent.type(screen.getByLabelText('URL'), 'javascript:alert(1)');
    await userEvent.click(screen.getByRole('button', { name: 'Add resource' }));
    expect(screen.getByText('The URL must start with http:// or https://.')).toBeInTheDocument();
    expect(adminResourceService.create).not.toHaveBeenCalled();

    await userEvent.clear(screen.getByLabelText('URL'));
    await userEvent.type(screen.getByLabelText('URL'), 'not a url');
    await userEvent.click(screen.getByRole('button', { name: 'Add resource' }));
    expect(screen.getByText(/Enter a valid URL/)).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText('URL'));
    await userEvent.type(screen.getByLabelText('URL'), 'https://example.com/ok');
    await userEvent.click(screen.getByRole('button', { name: 'Add resource' }));
    expect(adminResourceService.create).toHaveBeenCalledWith({ skill_id: 1, title: 'New one', url: 'https://example.com/ok', description: null });
  });

  it('hides approve controls from faculty and notes that editing resets approval', async () => {
    renderPage('FACULTY');
    await screen.findByText('Python Tutorial');
    expect(screen.queryByRole('button', { name: 'Approve Python Tutorial' })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Edit Python Tutorial' }));
    expect(screen.getByText(/resets approval/)).toBeInTheDocument();
  });

  it('requires an in-page confirmation before an admin approves', async () => {
    vi.mocked(adminResourceService.approve).mockResolvedValue({ ...resource, is_approved: true });
    renderPage('ADMIN');
    await userEvent.click(await screen.findByRole('button', { name: 'Approve Python Tutorial' }));
    expect(adminResourceService.approve).not.toHaveBeenCalled();
    expect(screen.getByRole('alertdialog', { name: 'Approve this resource?' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Approve' }));
    expect(adminResourceService.approve).toHaveBeenCalledWith(5);
    expect(await screen.findByText('Resource approved.')).toBeInTheDocument();
  });

  it('passes filters to the list call', async () => {
    renderPage('ADMIN');
    await screen.findByText('Python Tutorial');
    await userEvent.selectOptions(screen.getByLabelText('Approval'), 'false');
    expect(adminResourceService.list).toHaveBeenLastCalledWith({ skillId: undefined, approved: false });
  });

  it('shows an error alert when loading fails', async () => {
    vi.mocked(adminResourceService.list).mockRejectedValue(new Error('nope'));
    renderPage('ADMIN');
    expect(await screen.findByRole('alert')).toHaveTextContent('nope');
  });
});
