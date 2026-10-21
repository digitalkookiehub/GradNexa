import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { getErrorMessage } from '@/lib/errors';
import { formatScore } from '@/lib/readiness';
import { PLAN_STATUS_LABELS } from '@/lib/roadmap';
import { roadmapService } from '@/services/roadmapService';
import type { PlanHistoryEntry } from '@/types';

export function PlanProgressPage() {
  const [plans, setPlans] = useState<PlanHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    roadmapService
      .history()
      .then((p) => {
        if (cancelled) return;
        setPlans(p);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load your plan history.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Plan history</h1>
        <Link to="/plan" className="text-sm text-primary hover:underline">
          Back to my plan
        </Link>
      </div>
      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading plan history...
        </p>
      )}
      {error && (
        <div className="space-y-3">
          <FormMessage message={error} />
          <Button variant="outline" onClick={() => setAttempt((a) => a + 1)}>
            Retry
          </Button>
        </div>
      )}
      {!loading && !error && plans.length === 0 && <p className="text-muted-foreground">You have not generated any plans yet.</p>}
      <ul className="space-y-3" aria-label="Plans">
        {plans.map((p) => (
          <li key={p.id}>
            <Card>
              <CardContent className="space-y-2 p-4 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">{p.role_name}</span>
                  <span className="text-muted-foreground">
                    {PLAN_STATUS_LABELS[p.status]} · started {p.starts_on}
                  </span>
                </div>
                <progress className="h-2 w-full" value={p.progress.percent} max={100} aria-label={`Progress for plan ${p.id}`} />
                <p className="text-muted-foreground">
                  {p.progress.done} of {p.progress.total} done ({formatScore(p.progress.percent)}%)
                </p>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
