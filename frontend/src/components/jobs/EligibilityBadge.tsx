import { ELIGIBILITY_STATUS_CLASSES, ELIGIBILITY_STATUS_LABELS } from '@/lib/jobs';
import type { EligibilityStatus } from '@/types/jobs';

export function EligibilityBadge({ status }: { status: EligibilityStatus }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ELIGIBILITY_STATUS_CLASSES[status]}`} data-testid="eligibility-badge">
      {ELIGIBILITY_STATUS_LABELS[status]}
    </span>
  );
}
