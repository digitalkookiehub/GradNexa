import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate, formatPercent } from '@/lib/assessment';
import { getErrorMessage } from '@/lib/errors';
import { assessmentService } from '@/services/assessmentService';
import type { HistoryEntry, StudentSkill } from '@/types';

export function HistoryPage() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [skills, setSkills] = useState<StudentSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([assessmentService.history(), assessmentService.mySkills()])
      .then(([h, s]) => {
        if (cancelled) return;
        setHistory(h);
        setSkills(s);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load your history.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold">History</h1>
      <FormMessage message={error} />
      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading...
        </p>
      )}
      {!loading && !error && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Past results</CardTitle>
              <CardDescription>Your submitted assessment attempts.</CardDescription>
            </CardHeader>
            <CardContent>
              {history.length === 0 ? (
                <p className="text-sm text-muted-foreground">You have not completed any assessments yet.</p>
              ) : (
                <ul className="divide-y">
                  {history.map((h) => (
                    <li key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                      <div>
                        <div className="font-medium">{h.assessment_title}</div>
                        <div className="text-muted-foreground">
                          Attempt {h.attempt_no} · {formatDate(h.submitted_at)}
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span>
                          {h.total_score} / {h.max_score} ({formatPercent(h.percentage)})
                        </span>
                        <Link to={`/attempts/${h.attempt_id}/result`} className="text-primary hover:underline">
                          Details
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>My skills</CardTitle>
              <CardDescription>Aggregated from your assessment results.</CardDescription>
            </CardHeader>
            <CardContent>
              {skills.length === 0 ? (
                <p className="text-sm text-muted-foreground">No skill scores yet. Complete an assessment to see them here.</p>
              ) : (
                <ul className="divide-y">
                  {skills.map((s) => (
                    <li key={s.skill_id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                      <div>
                        <div className="font-medium">{s.skill_name}</div>
                        <div className="text-muted-foreground">{s.category_name}</div>
                      </div>
                      <div className="text-right">
                        <div>{formatPercent(s.score)}</div>
                        <div className="text-xs text-muted-foreground">
                          {s.evidence_count} {s.evidence_count === 1 ? 'assessment' : 'assessments'}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
