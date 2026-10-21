import { describeRule } from './validation';
import type { EligibilityRuleOut } from '@/types/jobAdmin';

export function EligibilitySummary({ rule }: { rule: EligibilityRuleOut | null }) {
  if (!rule) {
    return <p className="text-sm text-muted-foreground">No eligibility rule is set. Students will see no automatic eligibility check for this job.</p>;
  }
  const { checked, notes } = describeRule(rule);
  return (
    <div className="space-y-3 text-sm" aria-label="Eligibility summary" role="group">
      <div>
        <div className="font-medium">Checked automatically against student records</div>
        <ul className="list-disc pl-5">
          {checked.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>
      {notes.length > 0 && (
        <div>
          <div className="font-medium">Additional notes (shown to students, not evaluated)</div>
          <ul className="list-disc pl-5">
            {notes.map((n, i) => (
              <li key={`${i}-${n}`}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
