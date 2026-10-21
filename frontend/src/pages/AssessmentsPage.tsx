import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { getErrorMessage } from '@/lib/errors';
import { TYPE_LABELS } from '@/lib/assessment';
import { assessmentService } from '@/services/assessmentService';
import type { StudentAssessment } from '@/types';

export function AssessmentsPage() {
  const [items, setItems] = useState<StudentAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    assessmentService
      .list()
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load assessments.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Assessments</h1>
        <p className="text-sm text-muted-foreground">Take assessments to build your verified skill profile.</p>
      </div>
      <FormMessage message={error} />
      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading assessments...
        </p>
      )}
      {!loading && !error && items.length === 0 && <p className="text-muted-foreground">No assessments are available right now.</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        {items.map((a) => {
          const limitReached = a.max_attempts !== null && a.attempts_used >= a.max_attempts && a.in_progress_attempt_id === null;
          return (
            <Card key={a.id} data-testid={`assessment-${a.id}`}>
              <CardHeader>
                <CardTitle>{a.title}</CardTitle>
                <CardDescription>
                  {TYPE_LABELS[a.type]} · v{a.version}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <div>{a.question_count} questions · {a.total_marks} marks</div>
                <div>{a.time_limit_min !== null ? `Time limit: ${a.time_limit_min} min` : 'No time limit'}</div>
                <div>
                  Attempts: {a.attempts_used}
                  {a.max_attempts !== null ? ` / ${a.max_attempts}` : ' (unlimited)'}
                </div>
                {a.negative_marking > 0 && (
                  <div className="text-muted-foreground">
                    Negative marking applies: a wrong answer loses {a.negative_marking} of that question's marks.
                  </div>
                )}
              </CardContent>
              <CardFooter>
                {a.in_progress_attempt_id !== null ? (
                  <Button asChild>
                    <Link to={`/assessments/${a.id}/attempt`}>Resume</Link>
                  </Button>
                ) : limitReached ? (
                  <p className="text-sm font-medium text-destructive">Attempt limit reached</p>
                ) : (
                  <Button asChild>
                    <Link to={`/assessments/${a.id}/attempt`}>Start</Link>
                  </Button>
                )}
              </CardFooter>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
