import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ScoreBreakdown } from '@/components/assessment/ScoreBreakdown';
import { FormMessage } from '@/components/auth/FormField';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate, formatPercent } from '@/lib/assessment';
import { getErrorMessage } from '@/lib/errors';
import { assessmentService } from '@/services/assessmentService';
import type { AssessmentResult } from '@/types';

export function ResultPage() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const id = Number(attemptId);
  const invalid = !Number.isInteger(id);
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isInteger(id)) return;
    let cancelled = false;
    assessmentService
      .getResult(id)
      .then((r) => {
        if (!cancelled) setResult(r);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load the result.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {loading && !invalid && (
        <p role="status" className="text-muted-foreground">
          Loading result...
        </p>
      )}
      <FormMessage message={invalid ? 'Invalid attempt.' : error} />
      {result && (
        <Card>
          <CardHeader>
            <CardTitle>{result.assessment_title}</CardTitle>
            <CardDescription>
              Version {result.assessment_version} · {formatDate(result.computed_at)}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <div className="text-4xl font-bold" data-testid="overall-percentage">
                {formatPercent(result.percentage)}
              </div>
              <div className="text-sm text-muted-foreground">
                Score: {result.total_score} / {result.max_score}
              </div>
            </div>
            <section aria-labelledby="skill-breakdown">
              <h2 id="skill-breakdown" className="mb-3 text-lg font-semibold">
                Skill breakdown
              </h2>
              <ScoreBreakdown scores={result.per_skill_scores} />
            </section>
          </CardContent>
        </Card>
      )}
      <div className="flex gap-4 text-sm">
        <Link to="/assessments" className="text-primary hover:underline">
          Back to assessments
        </Link>
        <Link to="/assessments/history" className="text-primary hover:underline">
          View history
        </Link>
      </div>
    </div>
  );
}
