import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { FormMessage } from '@/components/auth/FormField';
import { JobDetailsForm, type JobFormValues } from '@/components/jobsAdmin/JobDetailsForm';
import { StatusBadge } from '@/components/jobsAdmin/StatusBadge';
import { formatDeadline } from '@/components/jobsAdmin/validation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { adminJobService } from '@/services/adminJobService';
import { adminReadinessService } from '@/services/adminReadinessService';
import type { CareerRole } from '@/types';
import type { AdminCompany, AdminJobSummary, JobListFilters, JobStatus } from '@/types/jobAdmin';

interface PendingAction {
  kind: 'publish' | 'close';
  job: AdminJobSummary;
}

const STATUSES: JobStatus[] = ['DRAFT', 'OPEN', 'CLOSED'];

export function AdminJobsPage() {
  const [jobs, setJobs] = useState<AdminJobSummary[]>([]);
  const [companies, setCompanies] = useState<AdminCompany[]>([]);
  const [roles, setRoles] = useState<CareerRole[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [companyFilter, setCompanyFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [busy, setBusy] = useState(false);

  const loadJobs = useCallback(async (): Promise<void> => {
    const filters: JobListFilters = {};
    if (companyFilter) filters.company_id = Number(companyFilter);
    if (statusFilter) filters.status = statusFilter as JobStatus;
    try {
      setJobs(await adminJobService.listJobs(filters));
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load jobs.'));
    } finally {
      setLoading(false);
    }
  }, [companyFilter, statusFilter]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const list = await adminJobService.listCompanies();
        if (!cancelled) setCompanies(list);
      } catch (err) {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load companies.'));
      }
      try {
        const r = await adminReadinessService.listRoles();
        if (!cancelled) setRoles(r);
      } catch {
        // TPO accounts cannot list roles (403); the picker is simply omitted.
        if (!cancelled) setRoles(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleCreate = async (values: JobFormValues): Promise<void> => {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await adminJobService.createJob({
        company_id: values.company_id,
        title: values.title,
        body: values.body,
        ...(values.role_id !== undefined ? { role_id: values.role_id } : {}),
        ...(values.application_deadline ? { application_deadline: values.application_deadline } : {}),
      });
      setNotice('Job created as a draft. Open it to add skills and an eligibility rule, then publish.');
      setCreating(false);
      await loadJobs();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not create the job.'));
    } finally {
      setSaving(false);
    }
  };

  const handleConfirm = async (): Promise<void> => {
    if (!pending) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (pending.kind === 'publish') await adminJobService.publishJob(pending.job.id);
      else await adminJobService.closeJob(pending.job.id);
      setNotice(pending.kind === 'publish' ? `${pending.job.title} published.` : `${pending.job.title} closed.`);
      setPending(null);
      await loadJobs();
    } catch (err) {
      setError(getErrorMessage(err, pending.kind === 'publish' ? 'Could not publish the job.' : 'Could not close the job.'));
      setPending(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Jobs</h1>
        {!creating && (
          <Button
            onClick={() => {
              setNotice(null);
              setCreating(true);
            }}
          >
            New job
          </Button>
        )}
      </div>
      <FormMessage message={error} />
      <FormMessage message={notice} tone="success" />

      {creating && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">New job</CardTitle>
          </CardHeader>
          <CardContent>
            <JobDetailsForm
              job={null}
              companies={companies}
              roles={roles}
              disabled={false}
              saving={saving}
              submitLabel="Create job"
              onSubmit={(v) => void handleCreate(v)}
              onCancel={() => setCreating(false)}
            />
          </CardContent>
        </Card>
      )}

      {pending && (
        <ConfirmPanel
          title={pending.kind === 'publish' ? `Publish ${pending.job.title}` : `Close ${pending.job.title}`}
          message={
            pending.kind === 'publish'
              ? 'Publishing makes this job visible to students.'
              : 'Closing is permanent. A closed job can no longer be edited or reopened.'
          }
          confirmLabel={pending.kind === 'publish' ? 'Confirm publish' : 'Confirm close'}
          destructive={pending.kind === 'close'}
          busy={busy}
          onConfirm={() => void handleConfirm()}
          onCancel={() => setPending(null)}
        />
      )}

      <div className="flex flex-wrap gap-4">
        <div className="space-y-1">
          <Label htmlFor="filter-company">Filter by company</Label>
          <select id="filter-company" className={SELECT_CLASS} value={companyFilter} onChange={(e) => setCompanyFilter(e.target.value)}>
            <option value="">All companies</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="filter-status">Filter by status</Label>
          <select id="filter-status" className={SELECT_CLASS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading jobs...
        </p>
      )}
      {!loading && jobs.length === 0 && !error && <p className="text-muted-foreground">No jobs found.</p>}
      <ul className="space-y-3">
        {jobs.map((j) => (
          <li key={j.id}>
            <Card>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2 font-medium">
                    {j.title}
                    <StatusBadge status={j.status} />
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {j.company_name}
                    {j.role_name ? ` · ${j.role_name}` : ''}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Deadline: {formatDeadline(j.application_deadline)} · {j.has_eligibility_rule ? 'Eligibility rule set' : 'No eligibility rule'}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button asChild size="sm" variant="outline">
                    <Link to={`/admin/jobs/${j.id}`} aria-label={`Manage job ${j.title}`}>
                      Manage
                    </Link>
                  </Button>
                  {j.status === 'DRAFT' && (
                    <Button size="sm" aria-label={`Publish job ${j.title}`} onClick={() => setPending({ kind: 'publish', job: j })} disabled={busy}>
                      Publish
                    </Button>
                  )}
                  {j.status === 'OPEN' && (
                    <Button size="sm" variant="outline" aria-label={`Close job ${j.title}`} onClick={() => setPending({ kind: 'close', job: j })} disabled={busy}>
                      Close
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
