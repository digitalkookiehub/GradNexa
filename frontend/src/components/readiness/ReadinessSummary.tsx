import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/lib/assessment';
import { formatScore } from '@/lib/readiness';
import type { ReadinessResult } from '@/types';

interface ReadinessSummaryProps {
  result: ReadinessResult;
}

export function ReadinessSummary({ result }: ReadinessSummaryProps) {
  const coverage = Math.max(0, Math.min(100, result.coverage));
  const partial = coverage < 100;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{result.role_name ?? 'General readiness'}</CardTitle>
          <CardDescription>
            Rule version {result.rule_version} · computed {formatDate(result.computed_at)}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {result.overall === null ? (
            <div className="space-y-1" data-testid="no-overall">
              <p className="text-xl font-semibold">Not enough evidence yet</p>
              <p className="text-sm text-muted-foreground">
                Complete more assessments so there is evidence behind your skills.{' '}
                <Link to="/assessments" className="text-primary hover:underline">
                  Go to assessments
                </Link>
              </p>
            </div>
          ) : (
            <div className="flex flex-wrap items-baseline gap-3">
              <span className="text-4xl font-bold" data-testid="overall-score">
                {formatScore(result.overall)}
                <span className="text-lg font-normal text-muted-foreground"> / 100</span>
              </span>
              {result.level && (
                <span className="rounded-full bg-primary/10 px-3 py-1 text-sm font-medium text-primary" data-testid="level">
                  {result.level}
                </span>
              )}
            </div>
          )}

          <div className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <label htmlFor="coverage-meter" className="font-medium">
                Evidence coverage
              </label>
              <span data-testid="coverage-value">{formatScore(coverage)}%</span>
            </div>
            <progress id="coverage-meter" className="h-2 w-full" value={coverage} max={100} aria-label="Evidence coverage" />
            {partial && result.overall !== null && (
              <p className="text-sm text-muted-foreground">
                This score is based on partial evidence ({formatScore(coverage)}% coverage). It may change as you complete more assessments.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Category breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          {result.category_scores.length === 0 ? (
            <p className="text-sm text-muted-foreground">No category data.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">Category</th>
                    <th className="py-2 pr-4 font-medium">Weight</th>
                    <th className="py-2 pr-4 font-medium">Score</th>
                    <th className="py-2 font-medium">Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {result.category_scores.map((c) => (
                    <tr key={c.category_id} className="border-b last:border-0">
                      <td className="py-2 pr-4">{c.category_name}</td>
                      <td className="py-2 pr-4">{formatScore(c.weight)}</td>
                      <td className="py-2 pr-4">{c.score === null ? 'No evidence' : formatScore(c.score)}</td>
                      <td className="py-2">{c.evidence_count} result(s)</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Evidence</CardTitle>
          <CardDescription>The skill scores this readiness result is based on.</CardDescription>
        </CardHeader>
        <CardContent>
          {result.evidence.length === 0 ? (
            <p className="text-sm text-muted-foreground">No skill evidence recorded yet.</p>
          ) : (
            <ul className="divide-y text-sm">
              {result.evidence.map((e) => (
                <li key={e.skill_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span>
                    {e.skill_name} <span className="text-muted-foreground">({e.category_name})</span>
                  </span>
                  <span>
                    {formatScore(e.score)} · {e.evidence_count} result(s)
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
