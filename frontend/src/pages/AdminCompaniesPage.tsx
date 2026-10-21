import { useCallback, useEffect, useState } from 'react';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { FormMessage } from '@/components/auth/FormField';
import { CompanyForm } from '@/components/jobsAdmin/CompanyForm';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getErrorMessage } from '@/lib/errors';
import { adminJobService } from '@/services/adminJobService';
import type { AdminCompany, CompanyInput } from '@/types/jobAdmin';

type Editor = { mode: 'closed' } | { mode: 'new' } | { mode: 'edit'; company: AdminCompany };

export function AdminCompaniesPage() {
  const [companies, setCompanies] = useState<AdminCompany[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editor, setEditor] = useState<Editor>({ mode: 'closed' });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<AdminCompany | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (): Promise<void> => {
    try {
      setCompanies(await adminJobService.listCompanies());
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load companies.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleSubmit = async (payload: CompanyInput): Promise<void> => {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      if (editor.mode === 'edit') {
        await adminJobService.updateCompany(editor.company.id, payload);
        setNotice('Company saved.');
      } else {
        await adminJobService.createCompany(payload);
        setNotice('Company created.');
      }
      setEditor({ mode: 'closed' });
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the company.'));
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (company: AdminCompany): Promise<void> => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await adminJobService.updateCompany(company.id, { is_active: !company.is_active });
      setNotice(company.is_active ? `${company.name} deactivated.` : `${company.name} reactivated.`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not update the company.'));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (!deleting) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await adminJobService.deleteCompany(deleting.id);
      setNotice(`${deleting.name} deleted.`);
      setDeleting(null);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not delete the company.'));
      setDeleting(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Companies</h1>
        {editor.mode === 'closed' && (
          <Button
            onClick={() => {
              setNotice(null);
              setEditor({ mode: 'new' });
            }}
          >
            New company
          </Button>
        )}
      </div>
      <FormMessage message={error} />
      <FormMessage message={notice} tone="success" />

      {editor.mode !== 'closed' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{editor.mode === 'edit' ? `Edit company: ${editor.company.name}` : 'New company'}</CardTitle>
          </CardHeader>
          <CardContent>
            <CompanyForm
              key={editor.mode === 'edit' ? editor.company.id : 'new'}
              company={editor.mode === 'edit' ? editor.company : null}
              saving={saving}
              onSubmit={(p) => void handleSubmit(p)}
              onCancel={() => setEditor({ mode: 'closed' })}
            />
          </CardContent>
        </Card>
      )}

      {deleting && (
        <ConfirmPanel
          title={`Delete ${deleting.name}`}
          message="This permanently removes the company. Companies with job postings cannot be deleted; deactivate them instead."
          confirmLabel="Confirm delete"
          destructive
          busy={busy}
          onConfirm={() => void handleDelete()}
          onCancel={() => setDeleting(null)}
        />
      )}

      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading companies...
        </p>
      )}
      {!loading && companies.length === 0 && !error && <p className="text-muted-foreground">No companies yet.</p>}
      <ul className="space-y-3">
        {companies.map((c) => (
          <li key={c.id}>
            <Card>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <div className="font-medium">
                    {c.name}
                    {!c.is_active && <span className="ml-2 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">Inactive</span>}
                  </div>
                  {c.description && <div className="text-sm text-muted-foreground">{c.description}</div>}
                  {c.website && <div className="text-sm text-muted-foreground">{c.website}</div>}
                  <div className="text-xs text-muted-foreground">
                    {c.job_count} {c.job_count === 1 ? 'job' : 'jobs'}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" aria-label={`Edit company ${c.name}`} onClick={() => setEditor({ mode: 'edit', company: c })} disabled={busy}>
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    aria-label={`${c.is_active ? 'Deactivate' : 'Reactivate'} company ${c.name}`}
                    onClick={() => void handleToggleActive(c)}
                    disabled={busy}
                  >
                    {c.is_active ? 'Deactivate' : 'Reactivate'}
                  </Button>
                  <Button size="sm" variant="outline" aria-label={`Delete company ${c.name}`} onClick={() => setDeleting(c)} disabled={busy}>
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
