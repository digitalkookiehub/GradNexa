import { useCallback, useEffect, useState } from 'react';
import { StatTile } from '@/components/analytics/StatTile';
import { FormMessage } from '@/components/auth/FormField';
import { StudentsTable } from '@/components/facultyDashboard/StudentsTable';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/lib/assessment';
import { formatDash } from '@/lib/dashboard';
import { getErrorMessage } from '@/lib/errors';
import { facultyDashboardService } from '@/services/facultyDashboardService';
import type { FacultyDashboard } from '@/types';

export function FacultyDashboardPage() {
  const [data, setData] = useState<FacultyDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    facultyDashboardService
      .get()
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load the faculty dashboard.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const refresh = useCallback((): void => {
    setLoading(true);
    setError(null);
    setReloadKey((k) => k + 1);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Faculty dashboard</h1>
          <p className="text-sm text-muted-foreground">Students assigned to you.</p>
        </div>
        <Button variant="outline" onClick={refresh} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </Button>
      </div>

      <FormMessage message={error} />

      {loading && !data && (
        <p role="status" className="text-muted-foreground">
          Loading faculty dashboard...
        </p>
      )}

      {data && (
        <div className={loading ? 'space-y-6 opacity-60' : 'space-y-6'} aria-busy={loading}>
          <p className="text-sm text-muted-foreground">Generated {formatDate(data.generated_at)}</p>

          {data.totals.assigned_students === 0 && data.students.length === 0 ? (
            <p className="text-muted-foreground" data-testid="no-students">
              No students are assigned to you yet.
            </p>
          ) : (
            <>
              <section aria-label="Summary" className="grid gap-4 sm:grid-cols-3">
                <StatTile label="Assigned students" value={data.totals.assigned_students} />
                <StatTile label="With a readiness score" value={data.totals.with_readiness_score} />
                <StatTile label="Needing support" value={data.totals.needing_support} />
              </section>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Assigned students</CardTitle>
                  <CardDescription>
                    &quot;Needs support&quot; is a configured rule-based heuristic, not a prediction. The reasons that triggered it are listed next to each flag.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <StudentsTable students={data.students} />
                </CardContent>
              </Card>

              <div className="grid gap-6 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Top skill gaps</CardTitle>
                    <CardDescription>Across your assigned students.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {data.top_gaps.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No skill gaps recorded yet.</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                          <caption className="sr-only">Top skill gaps</caption>
                          <thead>
                            <tr className="border-b text-muted-foreground">
                              <th scope="col" className="py-2 pr-4 font-medium">Skill</th>
                              <th scope="col" className="py-2 pr-4 font-medium">Students affected</th>
                              <th scope="col" className="py-2 font-medium">High priority</th>
                            </tr>
                          </thead>
                          <tbody>
                            {data.top_gaps.map((g) => (
                              <tr key={g.skill_id} className="border-b last:border-0">
                                <th scope="row" className="py-2 pr-4 font-normal">{g.skill_name}</th>
                                <td className="py-2 pr-4 tabular-nums">{g.students_affected}</td>
                                <td className="py-2 tabular-nums">{g.high_priority_students}</td>
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
                    <CardTitle className="text-lg">Assessment performance</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {data.assessment_performance.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No submitted assessments yet.</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                          <caption className="sr-only">Assessment performance</caption>
                          <thead>
                            <tr className="border-b text-muted-foreground">
                              <th scope="col" className="py-2 pr-4 font-medium">Assessment</th>
                              <th scope="col" className="py-2 pr-4 font-medium">Submitted attempts</th>
                              <th scope="col" className="py-2 font-medium">Average (%)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {data.assessment_performance.map((a) => (
                              <tr key={a.assessment_id} className="border-b last:border-0">
                                <th scope="row" className="py-2 pr-4 font-normal">{a.title}</th>
                                <td className="py-2 pr-4 tabular-nums">{a.attempts_submitted}</td>
                                <td className="py-2 tabular-nums">{formatDash(a.average_percentage)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
