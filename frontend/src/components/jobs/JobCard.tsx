import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { formatDeadline } from '@/lib/jobs';
import type { JobListItem } from '@/types/jobs';
import { EligibilityBadge } from './EligibilityBadge';

export function JobCard({ job }: { job: JobListItem }) {
  return (
    <Card>
      <CardContent className="flex flex-wrap items-start justify-between gap-3 p-4">
        <div className="space-y-1">
          <Link to={`/jobs/${job.id}`} className="font-medium text-primary hover:underline">
            {job.title}
          </Link>
          <p className="text-sm text-muted-foreground">{job.company_name}</p>
          <p className="text-xs text-muted-foreground">
            {job.role_name ? `Role: ${job.role_name} · ` : ''}
            Deadline: {formatDeadline(job.application_deadline)}
            {job.deadline_passed && <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 font-medium text-red-800">Deadline passed</span>}
          </p>
        </div>
        <EligibilityBadge status={job.eligibility_status} />
      </CardContent>
    </Card>
  );
}
