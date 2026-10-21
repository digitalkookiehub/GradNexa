import type { CriterionKey, CriterionResult, EligibilityStatus, JobListItem } from '@/types/jobs';

export const ELIGIBILITY_STATUS_LABELS: Record<EligibilityStatus, string> = {
  ELIGIBLE: 'Meets configured criteria',
  NOT_ELIGIBLE: 'Does not meet configured criteria',
  INCOMPLETE_DATA: 'Some data missing',
  NO_RULE: 'No automatic criteria',
};

export const ELIGIBILITY_STATUS_CLASSES: Record<EligibilityStatus, string> = {
  ELIGIBLE: 'bg-green-100 text-green-800',
  NOT_ELIGIBLE: 'bg-red-100 text-red-800',
  INCOMPLETE_DATA: 'bg-amber-100 text-amber-800',
  NO_RULE: 'bg-muted text-muted-foreground',
};

export const RESULT_LABELS: Record<CriterionResult, string> = {
  MET: 'Met',
  NOT_MET: 'Not met',
  UNKNOWN: 'Unknown',
};

export const RESULT_ICONS: Record<CriterionResult, string> = { MET: '✓', NOT_MET: '✗', UNKNOWN: '?' };

export const RESULT_CLASSES: Record<CriterionResult, string> = {
  MET: 'text-green-700',
  NOT_MET: 'text-red-700',
  UNKNOWN: 'text-amber-700',
};

/** Which profile page a student fixes missing data on. */
export function profileLinkFor(key: CriterionKey): { to: string; label: string } {
  if (key === 'department' || key === 'graduation_year') return { to: '/onboarding', label: 'Update your profile' };
  return { to: '/profile/academics', label: 'Update your academics' };
}

export function filterJobs(jobs: JobListItem[], status: EligibilityStatus | 'ALL', search: string): JobListItem[] {
  const q = search.trim().toLowerCase();
  return jobs.filter((j) => {
    if (status !== 'ALL' && j.eligibility_status !== status) return false;
    if (q === '') return true;
    return [j.title, j.company_name, j.role_name ?? ''].some((s) => s.toLowerCase().includes(q));
  });
}

export function formatDeadline(iso: string | null): string {
  if (!iso) return 'No deadline';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString();
}
