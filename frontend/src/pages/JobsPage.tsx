import { useEffect, useMemo, useState } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { JobCard } from '@/components/jobs/JobCard';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { ELIGIBILITY_STATUS_LABELS, filterJobs } from '@/lib/jobs';
import { jobService } from '@/services/jobService';
import type { EligibilityStatus, JobListItem } from '@/types/jobs';

const STATUSES: EligibilityStatus[] = ['ELIGIBLE', 'NOT_ELIGIBLE', 'INCOMPLETE_DATA', 'NO_RULE'];

export function JobsPage() {
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<EligibilityStatus | 'ALL'>('ALL');
  const [search, setSearch] = useState('');

  useEffect(() => {
    let cancelled = false;
    jobService
      .list()
      .then((j) => {
        if (!cancelled) setJobs(j);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load job postings.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const visible = useMemo(() => filterJobs(jobs, status, search), [jobs, status, search]);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="text-2xl font-semibold">Jobs</h1>
      <p className="text-sm text-muted-foreground">
        Open postings from your college. The badge shows whether you meet the criteria the posting has configured. It says nothing about whether
        you would be chosen.
      </p>
      <div className="flex flex-wrap gap-4">
        <div className="space-y-1">
          <Label htmlFor="jobs-search">Search</Label>
          <Input id="jobs-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Title, company or role" />
        </div>
        <div className="space-y-1">
          <Label htmlFor="jobs-status">Eligibility</Label>
          <select id="jobs-status" className={SELECT_CLASS} value={status} onChange={(e) => setStatus(e.target.value as EligibilityStatus | 'ALL')}>
            <option value="ALL">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {ELIGIBILITY_STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
      </div>
      <FormMessage message={error} />
      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading jobs...
        </p>
      )}
      {!loading && !error && jobs.length === 0 && <p className="text-muted-foreground">There are no open job postings right now.</p>}
      {!loading && jobs.length > 0 && visible.length === 0 && <p className="text-muted-foreground">No postings match your filters.</p>}
      <div className="space-y-3">
        {visible.map((j) => (
          <JobCard key={j.id} job={j} />
        ))}
      </div>
    </div>
  );
}
