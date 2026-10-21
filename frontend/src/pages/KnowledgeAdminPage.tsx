import { useCallback, useEffect, useState } from 'react';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { FormMessage } from '@/components/auth/FormField';
import { KnowledgeDocumentDetail } from '@/components/knowledge/KnowledgeDocumentDetail';
import { KnowledgeUploadForm } from '@/components/knowledge/KnowledgeUploadForm';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/errors';
import { SOURCE_TYPES, STATUS_CLASSES, STATUS_LABELS, sourceTypeLabel } from '@/lib/knowledge';
import { formatBytes } from '@/lib/resume';
import { knowledgeService } from '@/services/knowledgeService';
import { studentService } from '@/services/studentService';
import type { Department } from '@/types';
import type { KnowledgeDocument } from '@/types/knowledge';

type PendingAction = { kind: 'approve' | 'archive' | 'delete'; doc: KnowledgeDocument };

export function KnowledgeAdminPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [acting, setActing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    studentService
      .listDepartments()
      .then((d) => {
        if (!cancelled) setDepartments(d);
      })
      .catch(() => {
        // Departments are optional for upload; the form still works without them.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    knowledgeService
      .list({ status: statusFilter, source_type: sourceFilter })
      .then((d) => {
        if (cancelled) return;
        setDocuments(d);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load documents.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [statusFilter, sourceFilter, attempt]);

  const handleConfirm = useCallback(async (): Promise<void> => {
    if (!pending) return;
    setActing(true);
    setError(null);
    setMessage(null);
    try {
      if (pending.kind === 'approve') await knowledgeService.approve(pending.doc.id);
      else if (pending.kind === 'archive') await knowledgeService.archive(pending.doc.id);
      else {
        await knowledgeService.remove(pending.doc.id);
        setSelectedId((id) => (id === pending.doc.id ? null : id));
      }
      setMessage(pending.kind === 'approve' ? 'Document approved. It is now searchable.' : pending.kind === 'archive' ? 'Document archived.' : 'Document deleted.');
      setPending(null);
      setAttempt((a) => a + 1);
    } catch (err) {
      setError(getErrorMessage(err, 'That action failed.'));
      setPending(null);
    } finally {
      setActing(false);
    }
  }, [pending]);

  const confirmCopy = (p: PendingAction): { title: string; message: string; label: string; destructive: boolean } => {
    if (p.kind === 'approve') {
      return { title: 'Approve this document?', message: `"${p.doc.title}" will become searchable and may be cited in assistant answers.`, label: 'Approve', destructive: false };
    }
    if (p.kind === 'archive') {
      return { title: 'Archive this document?', message: `"${p.doc.title}" will no longer be searchable.`, label: 'Archive', destructive: true };
    }
    return { title: 'Delete this document?', message: `"${p.doc.title}" and its chunks will be permanently removed.`, label: 'Delete', destructive: true };
  };

  const selected = documents.find((d) => d.id === selectedId) ?? null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Knowledge base</h1>
        <p className="text-sm text-muted-foreground">
          Only approved documents are searchable. {isAdmin ? 'You can approve or archive documents.' : 'An administrator must approve a document before it becomes searchable.'}
        </p>
      </div>

      <FormMessage message={error} />
      <FormMessage message={message} tone="success" />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Upload a document</CardTitle>
        </CardHeader>
        <CardContent>
          <KnowledgeUploadForm
            departments={departments}
            onUploaded={() => {
              setMessage('Document uploaded. It stays pending until an administrator approves it.');
              setError(null);
              setAttempt((a) => a + 1);
            }}
          />
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="kb-filter-status">Status</Label>
          <select id="kb-filter-status" className={SELECT_CLASS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="PENDING">Pending approval</option>
            <option value="APPROVED">Approved</option>
            <option value="ARCHIVED">Archived</option>
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="kb-filter-source">Source type</Label>
          <select id="kb-filter-source" className={SELECT_CLASS} value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
            <option value="">All source types</option>
            {SOURCE_TYPES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {pending && (
        <ConfirmPanel
          title={confirmCopy(pending).title}
          message={confirmCopy(pending).message}
          confirmLabel={confirmCopy(pending).label}
          destructive={confirmCopy(pending).destructive}
          busy={acting}
          onConfirm={() => void handleConfirm()}
          onCancel={() => setPending(null)}
        />
      )}

      {selected && <KnowledgeDocumentDetail key={selected.id} document={selected} onClose={() => setSelectedId(null)} />}

      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading documents...
        </p>
      )}
      {!loading && documents.length === 0 && !error && <p className="text-muted-foreground">No documents match these filters.</p>}
      {!loading && error && documents.length === 0 && (
        <Button variant="outline" onClick={() => setAttempt((a) => a + 1)}>
          Retry
        </Button>
      )}
      <ul className="space-y-3" aria-label="Documents">
        {documents.map((d) => (
          <li key={d.id}>
            <Card>
              <CardContent className="space-y-2 p-4 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">{d.title}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[d.status] ?? ''}`} data-testid={`status-${d.id}`}>
                    {STATUS_LABELS[d.status] ?? d.status}
                  </span>
                </div>
                <p className="text-muted-foreground">
                  {sourceTypeLabel(d.source_type)} | {d.department_name ?? 'All departments'} | {d.original_filename} ({formatBytes(d.size_bytes)}) | {d.chunk_count} chunks
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={() => setSelectedId(d.id)} aria-label={`View ${d.title}`}>
                    View
                  </Button>
                  {isAdmin && d.status !== 'APPROVED' && (
                    <Button size="sm" onClick={() => setPending({ kind: 'approve', doc: d })} aria-label={`Approve ${d.title}`}>
                      Approve
                    </Button>
                  )}
                  {isAdmin && d.status !== 'ARCHIVED' && (
                    <Button variant="outline" size="sm" onClick={() => setPending({ kind: 'archive', doc: d })} aria-label={`Archive ${d.title}`}>
                      Archive
                    </Button>
                  )}
                  <Button variant="outline" size="sm" onClick={() => setPending({ kind: 'delete', doc: d })} aria-label={`Delete ${d.title}`}>
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
