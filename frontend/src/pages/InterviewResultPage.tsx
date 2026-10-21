import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/lib/assessment';
import { formatDash } from '@/lib/dashboard';
import { getErrorMessage } from '@/lib/errors';
import { DEFAULT_DISCLAIMER } from '@/lib/interview';
import { interviewService } from '@/services/interviewService';
import type { InterviewResult } from '@/types';

const PROGRESS_CLASS =
  'h-2 w-full overflow-hidden rounded bg-muted [&::-moz-progress-bar]:bg-primary [&::-webkit-progress-bar]:bg-muted [&::-webkit-progress-value]:bg-primary';

function ConceptChips({ label, items, tone }: { label: string; items: string[]; tone: 'covered' | 'missed' }) {
  const color = tone === 'covered' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-900';
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">None</p>
      ) : (
        <ul className="flex flex-wrap gap-2" aria-label={label}>
          {items.map((c) => (
            <li key={c} className={`rounded-full px-3 py-1 text-xs ${color}`}>
              {c}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function InterviewResultPage() {
  const { id } = useParams<{ id: string }>();
  const interviewId = Number(id);
  const [result, setResult] = useState<InterviewResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!Number.isInteger(interviewId)) return;
    let cancelled = false;
    interviewService
      .getResult(interviewId)
      .then((r) => {
        if (cancelled) return;
        setResult(r);
        setError(null);
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
  }, [interviewId, attempt]);

  const retry = useCallback((): void => {
    setLoading(true);
    setError(null);
    setAttempt((a) => a + 1);
  }, []);

  if (!Number.isInteger(interviewId)) return <FormMessage message="Invalid interview." />;
  if (loading) {
    return (
      <p role="status" className="py-12 text-center text-muted-foreground">
        Loading result...
      </p>
    );
  }
  if (error || !result) {
    return (
      <div className="mx-auto max-w-md space-y-4 py-12">
        <FormMessage message={error ?? 'Could not load the result.'} />
        <div className="flex gap-3">
          <Button variant="outline" onClick={retry}>
            Retry
          </Button>
          <Link to="/interview" className="self-center text-primary hover:underline">
            Back to interviews
          </Link>
        </div>
      </div>
    );
  }

  const disclaimer = result.disclaimer || DEFAULT_DISCLAIMER;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Interview result: {result.role_name}</h1>
        <p className="text-sm text-muted-foreground">Computed {formatDate(result.computed_at)}</p>
      </div>

      <div role="note" className="rounded-md border bg-muted px-3 py-2 text-sm" data-testid="disclaimer">
        {disclaimer}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Keyword coverage</CardTitle>
        </CardHeader>
        <CardContent>
          {result.overall === null ? (
            <p data-testid="no-overall">No coverage score could be computed.</p>
          ) : (
            <p className="text-3xl font-bold" data-testid="overall">
              {formatDash(result.overall)}
              <span className="text-base font-normal text-muted-foreground"> / 100</span>
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">By competency</CardTitle>
        </CardHeader>
        <CardContent>
          {result.competency_scores.length === 0 ? (
            <p className="text-sm text-muted-foreground">No competency scores.</p>
          ) : (
            <ul className="space-y-3" aria-label="Competency scores">
              {result.competency_scores.map((c) => (
                <li key={c.competency} className="space-y-1">
                  <div className="flex flex-wrap justify-between gap-2 text-sm">
                    <label htmlFor={`comp-${c.competency}`} className="font-medium">
                      {c.competency}
                    </label>
                    <span className="text-muted-foreground">
                      {formatDash(c.score)} / {formatDash(c.max)} · {c.questions} question{c.questions === 1 ? '' : 's'}
                    </span>
                  </div>
                  <progress id={`comp-${c.competency}`} className={PROGRESS_CLASS} max={c.max > 0 ? c.max : 100} value={c.score} />
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Question by question</CardTitle>
        </CardHeader>
        <CardContent>
          {result.per_question.length === 0 ? (
            <p className="text-sm text-muted-foreground">No questions.</p>
          ) : (
            <ol className="space-y-4" aria-label="Question results">
              {result.per_question.map((q) => (
                <li key={q.question_id} className="space-y-2 rounded-md border p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <p className="text-sm font-medium">
                      {q.position}. {q.prompt}
                    </p>
                    <span className="text-sm text-muted-foreground">Score {formatDash(q.score)}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{q.competency}</p>
                  {!q.answered && (
                    <p className="text-sm" data-testid={`unanswered-${q.question_id}`}>
                      Not answered.
                    </p>
                  )}
                  {q.answered && q.too_short && (
                    <p className="text-sm" data-testid={`too-short-${q.question_id}`}>
                      This answer was too short to be scored fully.
                    </p>
                  )}
                  {q.answered && (
                    <div className="grid gap-3 sm:grid-cols-2">
                      <ConceptChips label="Covered concepts" items={q.covered_concepts} tone="covered" />
                      <ConceptChips label="Missed concepts" items={q.missed_concepts} tone="missed" />
                    </div>
                  )}
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>

      <Link to="/interview" className="text-primary hover:underline">
        Back to interviews
      </Link>
    </div>
  );
}
