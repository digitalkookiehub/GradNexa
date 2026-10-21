import { useCallback, useEffect, useState } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { DepartmentSelect } from '@/components/admin/DepartmentSelect';
import { PlacementAnalyticsSection } from '@/components/analytics/PlacementAnalyticsSection';
import { BarList } from '@/components/dashboard/BarList';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/lib/assessment';
import { formatDash } from '@/lib/dashboard';
import { getErrorMessage } from '@/lib/errors';
import { dashboardService } from '@/services/dashboardService';
import { studentService } from '@/services/studentService';
import type { Department, PlacementDashboard } from '@/types';

function Tile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-background p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-2xl font-bold tabular-nums">{value}</p>
    </div>
  );
}

export function PlacementDashboardPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [deptError, setDeptError] = useState<string | null>(null);
  const [deptValue, setDeptValue] = useState('');
  const [data, setData] = useState<PlacementDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    studentService
      .listDepartments()
      .then((d) => {
        if (!cancelled) setDepartments(d);
      })
      .catch((err: unknown) => {
        if (!cancelled) setDeptError(getErrorMessage(err, 'Could not load departments for the filter.'));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    dashboardService
      .getPlacement(deptValue === '' ? null : Number(deptValue))
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load the placement dashboard.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [deptValue, reloadKey]);

  const refresh = useCallback((): void => {
    setLoading(true);
    setError(null);
    setReloadKey((k) => k + 1);
  }, []);

  const changeDepartment = (value: string): void => {
    setLoading(true);
    setError(null);
    setDeptValue(value);
  };

  const levelMax = data ? Math.max(0, ...data.level_distribution.map((l) => l.count)) : 0;
  const versions = data?.rule_versions_in_use ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Placement dashboard</h1>
          <p className="text-sm text-muted-foreground">Aggregate figures only. No individual students are shown.</p>
        </div>
        <Button variant="outline" onClick={refresh} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="max-w-xs">
            <DepartmentSelect
              id="placement-department"
              label="Department"
              departments={departments}
              value={deptValue}
              onChange={changeDepartment}
              placeholder="All departments"
            />
          </div>
          <FormMessage message={deptError} />
        </CardContent>
      </Card>

      <FormMessage message={error} />

      {loading && !data && (
        <p role="status" className="text-muted-foreground">
          Loading placement dashboard...
        </p>
      )}

      {data && (
        <div className={loading ? 'space-y-6 opacity-60' : 'space-y-6'} aria-busy={loading}>
          <p className="text-sm text-muted-foreground">
            {data.scope.department_name ?? 'All departments'} · generated {formatDate(data.generated_at)}
            {data.rule ? ` · active rule v${data.rule.version}` : ' · no active readiness rule'}
          </p>

          {versions.length > 1 && (
            <div role="status" className="rounded-md border bg-muted px-3 py-2 text-sm" data-testid="mixed-versions">
              Scores were computed under different rule versions ({versions.map((v) => `v${v}`).join(', ')}), so they may not be directly comparable.
            </div>
          )}

          {data.totals.students === 0 ? (
            <p className="text-muted-foreground" data-testid="no-students">
              There are no students in this scope yet.
            </p>
          ) : (
            <>
              <section aria-label="Summary" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Tile label="Students" value={data.totals.students} />
                <Tile label="Profiles complete" value={data.totals.profile_complete} />
                <Tile label="With a readiness score" value={data.totals.with_readiness_score} />
                <Tile label="With a submitted assessment" value={data.totals.with_assessment_submitted} />
              </section>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Readiness level distribution</CardTitle>
                  <CardDescription>Number of students at each level.</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.level_distribution.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No level data yet.</p>
                  ) : (
                    <BarList
                      ariaLabel="Level distribution"
                      max={levelMax}
                      items={data.level_distribution.map((l) => ({
                        key: l.level ?? 'not-scored',
                        label: l.level ?? 'Not scored',
                        value: l.count,
                        valueText: `${l.count} student(s)`,
                      }))}
                    />
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Department comparison</CardTitle>
                </CardHeader>
                <CardContent>
                  {data.departments.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No department data.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <caption className="sr-only">Department comparison</caption>
                        <thead>
                          <tr className="border-b text-muted-foreground">
                            <th scope="col" className="py-2 pr-4 font-medium">Department</th>
                            <th scope="col" className="py-2 pr-4 font-medium">Students</th>
                            <th scope="col" className="py-2 pr-4 font-medium">Scored</th>
                            <th scope="col" className="py-2 pr-4 font-medium">Avg overall</th>
                            <th scope="col" className="py-2 font-medium">Avg coverage (%)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.departments.map((d) => (
                            <tr key={d.department_id ?? 'none'} className="border-b last:border-0">
                              <th scope="row" className="py-2 pr-4 font-normal">{d.department_name}</th>
                              <td className="py-2 pr-4">{d.students}</td>
                              <td className="py-2 pr-4">{d.scored}</td>
                              <td className="py-2 pr-4">{formatDash(d.avg_overall)}</td>
                              <td className="py-2">{formatDash(d.avg_coverage)}</td>
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
                  <CardTitle className="text-lg">Top skill gaps</CardTitle>
                  <CardDescription>Skills where the most students fall short of role requirements.</CardDescription>
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
                              <td className="py-2 pr-4">{g.students_affected}</td>
                              <td className="py-2">{g.high_priority_students}</td>
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
                  <CardTitle className="text-lg">Assessment participation</CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid gap-4 text-sm sm:grid-cols-3">
                    <div>
                      <dt className="text-muted-foreground">Published assessments</dt>
                      <dd className="text-xl font-semibold tabular-nums">{data.assessment_participation.published_assessments}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Students with attempts</dt>
                      <dd className="text-xl font-semibold tabular-nums">{data.assessment_participation.students_with_attempts}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Submitted attempts</dt>
                      <dd className="text-xl font-semibold tabular-nums">{data.assessment_participation.submitted_attempts}</dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}

      <PlacementAnalyticsSection departmentId={deptValue === '' ? null : Number(deptValue)} reloadKey={reloadKey} />
    </div>
  );
}
