import type { JobStatus } from '@/types/jobAdmin';

const STYLES: Record<JobStatus, string> = {
  DRAFT: 'bg-muted text-muted-foreground',
  OPEN: 'bg-green-100 text-green-800',
  CLOSED: 'bg-red-100 text-red-800',
};

export function StatusBadge({ status }: { status: JobStatus }) {
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[status]}`}>{status}</span>;
}
