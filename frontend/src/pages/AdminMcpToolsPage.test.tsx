import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminMcpToolsPage } from './AdminMcpToolsPage';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { mcpAdminService } from '@/services/mcpAdminService';
import { AuthStub, makeAxiosError, makeUser } from '@/test/helpers';
import type { UserRole } from '@/types';

vi.mock('@/services/mcpAdminService', () => ({ mcpAdminService: { list: vi.fn(), setEnabled: vi.fn() } }));

const tool = { name: 'get_readiness', description: 'Reads readiness', allowed_roles: ['STUDENT'], enabled: true };

function renderAs(role: UserRole) {
  return render(
    <AuthStub user={makeUser(role)}>
      <MemoryRouter initialEntries={['/admin/mcp-tools']}>
        <Routes>
          <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
            <Route path="/admin/mcp-tools" element={<AdminMcpToolsPage />} />
          </Route>
          <Route path="*" element={<p>elsewhere</p>} />
        </Routes>
      </MemoryRouter>
    </AuthStub>,
  );
}

describe('AdminMcpToolsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(mcpAdminService.list).mockResolvedValue([tool]);
  });

  it('renders tools with role chips', async () => {
    renderAs('ADMIN');
    expect(await screen.findByText('get_readiness')).toBeInTheDocument();
    expect(screen.getByText('STUDENT')).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: 'Enable get_readiness' })).toBeChecked();
  });

  it('toggles optimistically and keeps the saved value', async () => {
    vi.mocked(mcpAdminService.setEnabled).mockResolvedValue({ ...tool, enabled: false });
    renderAs('ADMIN');
    await userEvent.click(await screen.findByRole('switch'));
    expect(mcpAdminService.setEnabled).toHaveBeenCalledWith('get_readiness', false);
    await waitFor(() => expect(screen.getByRole('switch')).not.toBeChecked());
  });

  it('rolls back and shows an error when the save fails', async () => {
    vi.mocked(mcpAdminService.setEnabled).mockRejectedValue(makeAxiosError(500, 'boom'));
    renderAs('ADMIN');
    await userEvent.click(await screen.findByRole('switch'));
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
    expect(screen.getByRole('switch')).toBeChecked();
  });

  it('shows an error state with retry on load failure', async () => {
    vi.mocked(mcpAdminService.list).mockRejectedValueOnce(makeAxiosError(500, 'down'));
    renderAs('ADMIN');
    expect(await screen.findByRole('alert')).toHaveTextContent('down');
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('get_readiness')).toBeInTheDocument();
  });

  it('is gated away from non-admins', () => {
    renderAs('FACULTY');
    expect(screen.queryByText('MCP tools')).not.toBeInTheDocument();
    expect(mcpAdminService.list).not.toHaveBeenCalled();
  });
});
