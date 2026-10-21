import { useEffect, useState } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDash } from '@/lib/dashboard';
import { getErrorMessage } from '@/lib/errors';
import { placementAnalyticsService } from '@/services/placementAnalyticsService';
import type { PlacementAnalytics } from '@/types';
import { MonthTrendTable } from './MonthTrendTable';

interface PlacementAnalyticsSectionProps {
  departmentId: number | null;
  /** Changing this value refetches (the page's Refresh button). */
  reloadKey: number;
}

export function PlacementAnalyticsSection({ departmentId, reloadKey }: PlacementAnalyticsSectionProps) {
  const [data, setData] = useState<PlacementAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    placementAnalyticsService
      .get(departmentId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load placement analytics.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [departmentId, reloadKey]);

  return (
    <section aria-labelledby="placement-analytics-heading" className="space-y-6">
      <div>
        <h2 id="placement-analytics-heading" className="text-xl font-semibold">Analytics</h2>
        <p className="text-sm text-muted-foreground">Aggregate figures only. No individual students are shown.</p>
      </div>

      <FormMessage message={error} />

      {loading && !data && (
        <p role="status" className="text-muted-foreground">
          Loading analytics...
        </p>
      )}

      {data && (
        <div className={loading ? 'space-y-6 opacity-60' : 'space-y-6'} aria-busy={loading}>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Role readiness</CardTitle>
              <CardDescription>Average readiness for each career role, among students who scored for it.</CardDescription>
            </CardHeader>
            <CardContent>
              {data.role_readiness.length === 0 ? (
                <p className="text-sm text-muted-foreground">No role readiness data yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <caption className="sr-only">Role readiness</caption>
                    <thead>
                      <tr className="border-b text-muted-foreground">
                        <th scope="col" className="py-2 pr-4 font-medium">Role</th>
                        <th scope="col" className="py-2 pr-4 font-medium">Students with this goal</th>
                        <th scope="col" className="py-2 pr-4 font-medium">Students scored</th>
                        <th scope="col" className="py-2 pr-4 font-medium">Avg overall</th>
                        <th scope="col" className="py-2 font-medium">Avg coverage (%)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.role_readiness.map((r) => (
                        <tr key={r.role_id} className="border-b last:border-0">
                          <th scope="row" className="py-2 pr-4 font-normal">{r.role_name}</th>
                          <td className="py-2 pr-4 tabular-nums">{r.students_with_goal}</td>
                          <td className="py-2 pr-4 tabular-nums">{r.students_scored}</td>
                          <td className="py-2 pr-4 tabular-nums">{formatDash(r.average_overall)}</td>
                          <td className="py-2 tabular-nums">{formatDash(r.average_coverage)}</td>
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
              <CardTitle className="text-lg">Eligibility (separate from readiness)</CardTitle>
              <CardDescription>
                Student counts per job against its eligibility criteria. This is not a readiness score and not a prediction of selection.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {data.company_eligibility.length === 0 ? (
                <p className="text-sm text-muted-foreground">No jobs with eligibility data yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <caption className="sr-only">Eligibility by job</caption>
                    <thead>
                      <tr className="border-b text-muted-foreground">
                        <th scope="col" className="py-2 pr-4 font-medium">Job</th>
                        <th scope="col" className="py-2 pr-4 font-medium">Company</th>
                        <th scope="col" className="py-2 pr-4 font-medium">Eligible</th>
                        <th scope="col" className="py-2 pr-4 font-medium">Not eligible</th>
                        <th scope="col" className="py-2 pr-4 font-medium">Incomplete data</th>
                        <th scope="col" className="py-2 font-medium">No criteria</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.company_eligibility.map((c) => (
                        <tr key={c.job_id} className="border-b last:border-0">
                          <th scope="row" className="py-2 pr-4 font-normal">{c.job_title}</th>
                          <td className="py-2 pr-4">{c.company_name}</td>
                          <td className="py-2 pr-4 tabular-nums">{c.eligible}</td>
                          <td className="py-2 pr-4 tabular-nums">{c.not_eligible}</td>
                          <td className="py-2 pr-4 tabular-nums">{c.incomplete_data}</td>
                          <td className="py-2 tabular-nums">{c.no_rule_students}</td>
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
              <CardTitle className="text-lg">Readiness progress over time</CardTitle>
            </CardHeader>
            <CardContent>
              {data.progress_trends.length === 0 ? (
                <p className="text-sm text-muted-foreground">No progress data yet.</p>
              ) : (
                <MonthTrendTable
                  caption="Readiness progress by month"
                  countLabel="Students scored"
                  averageLabel="Avg overall"
                  rows={data.progress_trends.map((t) => ({ month: t.month, count: t.students_scored, average: t.average_overall }))}
                />
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </section>
  );
}
