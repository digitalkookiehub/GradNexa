import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { getErrorMessage, getErrorStatus } from '@/lib/errors';
import { formatScore, GAP_STATUS_LABELS, PRIORITY_CLASSES, PRIORITY_LABELS, sortGaps } from '@/lib/readiness';
import { jobService } from '@/services/jobService';
import type { JobSkillFit } from '@/types/jobs';

export function SkillFitSection({ jobId }: { jobId: number }) {
  const [fit, setFit] = useState<JobSkillFit | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noRule, setNoRule] = useState<string | null>(null);

  const load = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    setNoRule(null);
    try {
      setFit(await jobService.skillFit(jobId));
    } catch (err) {
      setFit(null);
      if (getErrorStatus(err) === 409) setNoRule(getErrorMessage(err, 'No active readiness rule configured.'));
      else setError(getErrorMessage(err, 'Could not load your skill fit.'));
    } finally {
      setLoading(false);
    }
  };

  const sorted = useMemo(() => (fit ? sortGaps(fit.gaps) : []), [fit]);

  return (
    <section aria-labelledby="skill-fit-heading" className="space-y-3 rounded-md border bg-background p-4">
      <h2 id="skill-fit-heading" className="text-lg font-semibold">
        Skill fit
      </h2>
      <p className="text-sm text-muted-foreground">
        How your assessed skills compare with the skills this posting asks for. This looks at skills only.
      </p>
      <Button onClick={() => void load()} disabled={loading}>
        {loading ? 'Checking...' : 'Check my skill fit'}
      </Button>
      <FormMessage message={error} />
      {noRule && (
        <p role="status" data-testid="no-rule" className="text-sm text-muted-foreground">
          {noRule}
        </p>
      )}
      {fit && (
        <div className="space-y-3">
          {fit.overall === null ? (
            <div data-testid="no-overall">
              <p className="text-lg font-semibold">Not enough evidence yet</p>
              <p className="text-sm text-muted-foreground">Complete more assessments so there is evidence behind your skills.</p>
            </div>
          ) : (
            <p className="text-2xl font-semibold" data-testid="skill-fit-overall">
              {formatScore(fit.overall)} <span className="text-base font-normal text-muted-foreground">/ 100</span>
            </p>
          )}
          <p className="text-sm text-muted-foreground" data-testid="skill-fit-coverage">
            Coverage: {formatScore(fit.coverage)}% of the skills have evidence
          </p>
          {sorted.length === 0 ? (
            <p className="text-sm text-muted-foreground">This posting has no skills to compare.</p>
          ) : (
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="p-3 font-medium">Skill</th>
                    <th className="p-3 font-medium">Current</th>
                    <th className="p-3 font-medium">Required</th>
                    <th className="p-3 font-medium">Gap</th>
                    <th className="p-3 font-medium">Status</th>
                    <th className="p-3 font-medium">Priority</th>
                    <th className="p-3 font-medium">Recommended action</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((g) => (
                    <tr key={g.skill_id} className="border-b last:border-0">
                      <td className="p-3 font-medium">{g.skill_name}</td>
                      <td className="p-3">{g.current === null ? 'Not assessed' : formatScore(g.current)}</td>
                      <td className="p-3">{formatScore(g.required)}</td>
                      <td className="p-3">{formatScore(g.gap)}</td>
                      <td className="p-3">{GAP_STATUS_LABELS[g.status]}</td>
                      <td className="p-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_CLASSES[g.priority]}`} data-testid="priority-badge">
                          {PRIORITY_LABELS[g.priority]}
                        </span>
                      </td>
                      <td className="p-3">{g.recommended_action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      <Link to="/assessments" className="block text-sm text-primary hover:underline">
        Take assessments to build evidence
      </Link>
    </section>
  );
}
