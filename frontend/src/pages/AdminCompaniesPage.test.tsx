import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminCompaniesPage } from './AdminCompaniesPage';
import { adminJobService } from '@/services/adminJobService';
import { makeAxiosError } from '@/test/helpers';
import type { AdminCompany } from '@/types/jobAdmin';

vi.mock('@/services/adminJobService', () => ({
  adminJobService: { listCompanies: vi.fn(), createCompany: vi.fn(), updateCompany: vi.fn(), deleteCompany: vi.fn() },
}));

const ACME: AdminCompany = { id: 1, name: 'Acme', description: null, website: null, is_active: true, job_count: 2 };

describe('AdminCompaniesPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminJobService.listCompanies).mockResolvedValue([ACME]);
  });

  it('shows the empty state', async () => {
    vi.mocked(adminJobService.listCompanies).mockResolvedValue([]);
    render(<AdminCompaniesPage />);
    expect(await screen.findByText('No companies yet.')).toBeInTheDocument();
  });

  it('shows a load error', async () => {
    vi.mocked(adminJobService.listCompanies).mockRejectedValue(new Error('boom'));
    render(<AdminCompaniesPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
  });

  it('validates name and website before submitting', async () => {
    render(<AdminCompaniesPage />);
    await userEvent.click(await screen.findByRole('button', { name: 'New company' }));
    await userEvent.click(screen.getByRole('button', { name: 'Create company' }));
    expect(screen.getByText('Company name is required.')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Company name'), 'Globex');
    await userEvent.type(screen.getByLabelText('Website (optional)'), 'ftp://globex');
    await userEvent.click(screen.getByRole('button', { name: 'Create company' }));
    expect(screen.getByText(/valid http:\/\/ or https:\/\/ URL/)).toBeInTheDocument();
    expect(adminJobService.createCompany).not.toHaveBeenCalled();
  });

  it('creates a company with trimmed values', async () => {
    vi.mocked(adminJobService.createCompany).mockResolvedValue({ ...ACME, id: 2, name: 'Globex' });
    render(<AdminCompaniesPage />);
    await userEvent.click(await screen.findByRole('button', { name: 'New company' }));
    await userEvent.type(screen.getByLabelText('Company name'), ' Globex ');
    await userEvent.type(screen.getByLabelText('Website (optional)'), 'https://globex.com');
    await userEvent.click(screen.getByRole('button', { name: 'Create company' }));
    expect(adminJobService.createCompany).toHaveBeenCalledWith({ name: 'Globex', description: null, website: 'https://globex.com' });
  });

  it('shows the server message on a duplicate name', async () => {
    vi.mocked(adminJobService.createCompany).mockRejectedValue(makeAxiosError(409, 'Company name already exists'));
    render(<AdminCompaniesPage />);
    await userEvent.click(await screen.findByRole('button', { name: 'New company' }));
    await userEvent.type(screen.getByLabelText('Company name'), 'Acme');
    await userEvent.click(screen.getByRole('button', { name: 'Create company' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Company name already exists');
  });

  it('deactivates a company', async () => {
    vi.mocked(adminJobService.updateCompany).mockResolvedValue({ ...ACME, is_active: false });
    render(<AdminCompaniesPage />);
    await userEvent.click(await screen.findByRole('button', { name: 'Deactivate company Acme' }));
    expect(adminJobService.updateCompany).toHaveBeenCalledWith(1, { is_active: false });
  });

  it('confirms delete in-page and shows the 409 message', async () => {
    vi.mocked(adminJobService.deleteCompany).mockRejectedValue(makeAxiosError(409, 'Company has job postings; deactivate it instead'));
    render(<AdminCompaniesPage />);
    await userEvent.click(await screen.findByRole('button', { name: 'Delete company Acme' }));
    expect(adminJobService.deleteCompany).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));
    expect(adminJobService.deleteCompany).toHaveBeenCalledWith(1);
    expect(await screen.findByRole('alert')).toHaveTextContent('Company has job postings; deactivate it instead');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });
});
