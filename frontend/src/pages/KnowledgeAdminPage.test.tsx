import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KnowledgeAdminPage } from './KnowledgeAdminPage';
import { validateKnowledgeFile } from '@/lib/knowledge';
import { knowledgeService } from '@/services/knowledgeService';
import { studentService } from '@/services/studentService';
import { AuthStub, makeAxiosError, makeUser } from '@/test/helpers';
import type { UserRole } from '@/types';
import type { KnowledgeDocument } from '@/types/knowledge';

vi.mock('@/services/knowledgeService', () => ({
  knowledgeService: { upload: vi.fn(), list: vi.fn(), chunks: vi.fn(), remove: vi.fn(), approve: vi.fn(), archive: vi.fn() },
}));
vi.mock('@/services/studentService', () => ({ studentService: { listDepartments: vi.fn() } }));

const doc: KnowledgeDocument = {
  id: 3,
  title: 'Placement Handbook',
  source_type: 'PLACEMENT_GUIDE',
  department_id: null,
  department_name: null,
  original_filename: 'hb.pdf',
  content_type: 'application/pdf',
  size_bytes: 2048,
  status: 'PENDING',
  uploaded_by: 1,
  approved_by: null,
  approved_at: null,
  chunk_count: 12,
  created_at: '2026-01-01T00:00:00Z',
};

function renderPage(role: UserRole) {
  return render(
    <AuthStub user={makeUser(role)}>
      <KnowledgeAdminPage />
    </AuthStub>,
  );
}

function makeFile(name: string, type: string, size = 100): File {
  const f = new File(['x'], name, { type });
  Object.defineProperty(f, 'size', { value: size });
  return f;
}

describe('validateKnowledgeFile', () => {
  it('accepts pdf/docx/txt/md and rejects others and oversize', () => {
    expect(validateKnowledgeFile(makeFile('a.md', 'text/markdown'))).toBeNull();
    expect(validateKnowledgeFile(makeFile('a.txt', 'text/plain'))).toBeNull();
    expect(validateKnowledgeFile(makeFile('a.exe', 'application/octet-stream'))).toMatch(/Only PDF/);
    expect(validateKnowledgeFile(makeFile('a.pdf', 'application/pdf', 11 * 1024 * 1024))).toMatch(/larger/);
  });
});

describe('KnowledgeAdminPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(studentService.listDepartments).mockResolvedValue([{ id: 1, name: 'CSE', code: 'CSE' }]);
    vi.mocked(knowledgeService.list).mockResolvedValue([doc]);
    vi.mocked(knowledgeService.chunks).mockResolvedValue({ total: 0, chunks: [] });
  });

  it('shows approve/archive for admin only', async () => {
    renderPage('ADMIN');
    await screen.findByText('Placement Handbook');
    expect(screen.getByRole('button', { name: 'Approve Placement Handbook' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Archive Placement Handbook' })).toBeInTheDocument();
    expect(screen.getByText(/Only approved documents are searchable/)).toBeInTheDocument();
  });

  it('hides approve/archive for faculty', async () => {
    renderPage('FACULTY');
    await screen.findByText('Placement Handbook');
    expect(screen.queryByRole('button', { name: /Approve/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Archive/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete Placement Handbook' })).toBeInTheDocument();
  });

  it('approves after in-page confirmation', async () => {
    vi.mocked(knowledgeService.approve).mockResolvedValue({ ...doc, status: 'APPROVED' });
    renderPage('ADMIN');
    await screen.findByText('Placement Handbook');
    await userEvent.click(screen.getByRole('button', { name: 'Approve Placement Handbook' }));
    expect(knowledgeService.approve).not.toHaveBeenCalled();
    const dialog = screen.getByRole('alertdialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Approve' }));
    expect(knowledgeService.approve).toHaveBeenCalledWith(3);
    expect(await screen.findByText(/Document approved/)).toBeInTheDocument();
  });

  it('cancelling archive does not call the service', async () => {
    renderPage('ADMIN');
    await screen.findByText('Placement Handbook');
    await userEvent.click(screen.getByRole('button', { name: 'Archive Placement Handbook' }));
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Cancel' }));
    expect(knowledgeService.archive).not.toHaveBeenCalled();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('deletes after confirmation and shows errors', async () => {
    vi.mocked(knowledgeService.remove).mockRejectedValue(makeAxiosError(403, 'Not allowed'));
    renderPage('FACULTY');
    await screen.findByText('Placement Handbook');
    await userEvent.click(screen.getByRole('button', { name: 'Delete Placement Handbook' }));
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Delete' }));
    expect(knowledgeService.remove).toHaveBeenCalledWith(3);
    expect(await screen.findByRole('alert')).toHaveTextContent('Not allowed');
  });

  it('pages through chunks', async () => {
    const mk = (i: number) => ({ id: i, chunk_index: i, content: `<b>chunk ${i}</b>`, heading: null });
    vi.mocked(knowledgeService.chunks).mockImplementation((_id, _limit, offset) =>
      Promise.resolve({ total: 8, chunks: offset === 0 ? [mk(0), mk(1)] : [mk(5), mk(6)] }),
    );
    renderPage('ADMIN');
    await screen.findByText('Placement Handbook');
    await userEvent.click(screen.getByRole('button', { name: 'View Placement Handbook' }));
    expect(await screen.findByText('<b>chunk 0</b>')).toBeInTheDocument();
    expect(screen.getByTestId('chunk-range')).toHaveTextContent('1-5 of 8');
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByText('<b>chunk 5</b>')).toBeInTheDocument();
    expect(knowledgeService.chunks).toHaveBeenLastCalledWith(3, 5, 5);
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
  });

  it('rejects a bad file type client-side', async () => {
    renderPage('ADMIN');
    await screen.findByText('Placement Handbook');
    const input = screen.getByLabelText('Document file');
    await userEvent.upload(input, makeFile('bad.exe', 'application/octet-stream'), { applyAccept: false });
    expect(await screen.findByText(/Only PDF, DOCX, TXT or MD/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Title'), 'T');
    await userEvent.click(screen.getByRole('button', { name: 'Upload document' }));
    expect(knowledgeService.upload).not.toHaveBeenCalled();
  });

  it('maps a 422 upload error', async () => {
    vi.mocked(knowledgeService.upload).mockRejectedValue(makeAxiosError(422, 'No extractable text found (OCR is not implemented in this phase)'));
    renderPage('ADMIN');
    await screen.findByText('Placement Handbook');
    await userEvent.type(screen.getByLabelText('Title'), 'Scan');
    await userEvent.upload(screen.getByLabelText('Document file'), makeFile('s.pdf', 'application/pdf'));
    await userEvent.click(screen.getByRole('button', { name: 'Upload document' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be used.*OCR is not implemented/);
  });

  it('uploads successfully and refreshes', async () => {
    vi.mocked(knowledgeService.upload).mockResolvedValue(doc);
    renderPage('FACULTY');
    await screen.findByText('Placement Handbook');
    await userEvent.type(screen.getByLabelText('Title'), 'New');
    await userEvent.upload(screen.getByLabelText('Document file'), makeFile('n.txt', 'text/plain'));
    await userEvent.click(screen.getByRole('button', { name: 'Upload document' }));
    expect(await screen.findByText(/stays pending/)).toBeInTheDocument();
    expect(knowledgeService.upload).toHaveBeenCalledWith(expect.objectContaining({ title: 'New', source_type: 'OTHER', department_id: null }));
    expect(knowledgeService.list).toHaveBeenCalledTimes(2);
  });
});
