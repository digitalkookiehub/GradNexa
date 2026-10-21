import { useEffect, useState, type FormEvent } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { MAX_JD_CHARS } from '@/lib/resume';
import { jobService } from '@/services/jobService';
import type { JobListItem } from '@/types/jobs';
import type { ExplorerRole } from '@/types/roadmap';
import type { AnalyzePayload } from '@/types/resume';

interface AnalyzeFormProps {
  resumeId: number;
  roles: ExplorerRole[];
  initialJobId?: number | null;
  busy: boolean;
  error: string | null;
  onSubmit: (payload: AnalyzePayload) => void;
  onCancel: () => void;
}

export function AnalyzeForm({ resumeId, roles, initialJobId = null, busy, error, onSubmit, onCancel }: AnalyzeFormProps) {
  const [roleValue, setRoleValue] = useState('');
  const [jd, setJd] = useState('');
  const [jobValue, setJobValue] = useState(initialJobId === null ? '' : String(initialJobId));
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const jobId = `analyze-job-${resumeId}`;

  useEffect(() => {
    let cancelled = false;
    jobService
      .list()
      .then((j) => {
        if (cancelled) return;
        setJobs(j);
        setJobValue((cur) => (j.some((x) => String(x.id) === cur) ? cur : ''));
      })
      .catch((err: unknown) => {
        if (!cancelled) setJobsError(getErrorMessage(err, 'Could not load job postings; you can still paste a job description.'));
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const goals = roles.filter((r) => r.is_goal && r.is_active);
  const others = roles.filter((r) => !r.is_goal && r.is_active);
  const roleId = `analyze-role-${resumeId}`;
  const jdId = `analyze-jd-${resumeId}`;

  const handleSubmit = (e: FormEvent): void => {
    e.preventDefault();
    const payload: AnalyzePayload = {};
    if (roleValue !== '') payload.role_id = Number(roleValue);
    if (jobValue !== '') payload.job_id = Number(jobValue);
    else if (jd.trim() !== '') payload.jd_text = jd;
    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-md border bg-background p-4" aria-label="Analyze resume">
      <p className="text-sm text-muted-foreground">
        All fields are optional. A job posting and a pasted job description cannot be combined. Matching is keyword-based against your college&apos;s configured skills, so it can miss synonyms.
      </p>
      <div className="space-y-2">
        <Label htmlFor={roleId}>Target role (optional)</Label>
        <select id={roleId} className={SELECT_CLASS} value={roleValue} onChange={(e) => setRoleValue(e.target.value)} disabled={busy}>
          <option value="">No target role</option>
          {goals.length > 0 && (
            <optgroup label="Your goals">
              {goals.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </optgroup>
          )}
          {others.length > 0 && (
            <optgroup label="Other roles">
              {others.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </optgroup>
          )}
        </select>
      </div>
      <div className="space-y-2">
        <Label htmlFor={jobId}>Compare with a job posting (optional)</Label>
        <select id={jobId} className={SELECT_CLASS} value={jobValue} onChange={(e) => setJobValue(e.target.value)} disabled={busy || jd.trim() !== ''}>
          <option value="">No job posting</option>
          {jobs.map((j) => (
            <option key={j.id} value={j.id}>
              {j.title} - {j.company_name}
            </option>
          ))}
        </select>
        {jd.trim() !== '' && <p className="text-xs text-muted-foreground">Clear the pasted job description to pick a job posting instead.</p>}
        <FormMessage message={jobsError} />
      </div>
      <div className="space-y-2">
        <Label htmlFor={jdId}>Job description (optional)</Label>
        <textarea
          id={jdId}
          className="min-h-28 w-full rounded-md border bg-background px-3 py-2 text-sm"
          value={jd}
          maxLength={MAX_JD_CHARS}
          onChange={(e) => setJd(e.target.value)}
          disabled={busy || jobValue !== ''}
          placeholder="Paste a job description to see which of its skills appear in your resume"
        />
        <p className="text-xs text-muted-foreground">
          {jd.length} / {MAX_JD_CHARS}
        </p>
      </div>
      <FormMessage message={error} />
      <div className="flex gap-2">
        <Button type="submit" disabled={busy}>
          {busy ? 'Analyzing...' : 'Run analysis'}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
