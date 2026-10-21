import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { formatDate } from '@/lib/assessment';
import { getErrorMessage } from '@/lib/errors';
import { profileLinkFor, RESULT_CLASSES, RESULT_ICONS, RESULT_LABELS } from '@/lib/jobs';
import { jobService } from '@/services/jobService';
import type { EligibilityCheck, EligibilityStatus } from '@/types/jobs';

const SUMMARY: Record<EligibilityStatus, string> = {
  ELIGIBLE: 'You meet the configured eligibility criteria.',
  NOT_ELIGIBLE: 'You do not meet the configured eligibility criteria.',
  INCOMPLETE_DATA: 'Some of your data is missing, so not every criterion could be checked.',
  NO_RULE: 'This posting has no automatic eligibility criteria.',
};

export function EligibilitySection({ jobId }: { jobId: number }) {
  const [check, setCheck] = useState<EligibilityCheck | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    jobService
      .eligibility(jobId)
      .then((c) => {
        if (!cancelled) {
          setCheck(c);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not check eligibility.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, attempt]);

  const unmet = check ? check.criteria.filter((c) => c.result === 'NOT_MET') : [];

  return (
    <section aria-labelledby="eligibility-heading" className="space-y-3 rounded-md border bg-background p-4">
      <h2 id="eligibility-heading" className="text-lg font-semibold">
        Eligibility
      </h2>
      <p className="text-sm text-muted-foreground">Based on the criteria this posting has configured. It is a separate check from your skills.</p>
      <FormMessage message={error} />
      {error && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setLoading(true);
            setAttempt((a) => a + 1);
          }}
        >
          Retry
        </Button>
      )}
      {loading && (
        <p role="status" className="text-muted-foreground">
          Checking eligibility...
        </p>
      )}
      {check && (
        <>
          <p className="font-medium" data-testid="eligibility-summary">
            {SUMMARY[check.status]}
            {unmet.length > 0 && ` You do not meet: ${unmet.map((c) => c.label).join(', ')}.`}
          </p>
          {check.criteria.length === 0 ? (
            <p className="text-sm text-muted-foreground">There are no automatic criteria to show.</p>
          ) : (
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="p-3 font-medium">Criterion</th>
                    <th className="p-3 font-medium">Required</th>
                    <th className="p-3 font-medium">Your value</th>
                    <th className="p-3 font-medium">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {check.criteria.map((c) => {
                    const link = profileLinkFor(c.key);
                    return (
                      <tr key={c.key} className="border-b last:border-0">
                        <td className="p-3 font-medium">{c.label}</td>
                        <td className="p-3">{c.required}</td>
                        <td className="p-3">{c.actual ?? 'Not available'}</td>
                        <td className="p-3">
                          <span className={`font-medium ${RESULT_CLASSES[c.result]}`}>
                            <span aria-hidden="true">{RESULT_ICONS[c.result]} </span>
                            {RESULT_LABELS[c.result]}
                          </span>
                          {c.result === 'UNKNOWN' && (
                            <p className="text-xs text-muted-foreground">
                              Missing data: your {c.label.toLowerCase()} is not recorded.{' '}
                              <Link to={link.to} className="text-primary hover:underline">
                                {link.label}
                              </Link>
                            </p>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {check.note && <p className="text-sm text-muted-foreground">{check.note}</p>}
          {check.custom_notes.length > 0 && (
            <div className="space-y-1">
              <h3 className="text-sm font-semibold">Not checked automatically</h3>
              <p className="text-xs text-muted-foreground">The placement team added these notes. Please read them yourself.</p>
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {check.custom_notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-xs text-muted-foreground">Checked {formatDate(check.evaluated_at)}</p>
        </>
      )}
    </section>
  );
}
