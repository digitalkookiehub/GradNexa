import { useCallback, useEffect, useState } from 'react';
import { StatTile } from '@/components/analytics/StatTile';
import { MonthTrendTable } from '@/components/analytics/MonthTrendTable';
import { FormMessage } from '@/components/auth/FormField';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { BarList } from '@/components/dashboard/BarList';
import { SkillHeatmap } from '@/components/hodDashboard/SkillHeatmap';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { formatDate } from '@/lib/assessment';
import { getErrorMessage, getErrorStatus } from '@/lib/errors';
import { hodDashboardService } from '@/services/hodDashboardService';
import type { HodDashboard, HodScope } from '@/types';

function hodErrorMessage(err: unknown): string {
  const message = getErrorMessage(err, 'Could not load the HOD dashboard.');
  if (getErrorStatus(err) === 403) {
    if (/no department assigned/i.test(message)) {
      return 'No department is assigned to your account yet. Ask an administrator to assign you a department.';
    }
    return `You do not have access to this department. ${message}`;
  }
  return message;
}

export function HodDashboardPage() {
  const [assigned, setAssigned] = useState<HodScope | null>(null);
  const [deptValue, setDeptValue] = useState('');
  const [data, setData] = useState<HodDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    hodDashboardService
      .get(deptValue === '' ? null : Number(deptValue))
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setError(null);
        // The unfiltered response lists every assigned department; keep it for the select.
        if (deptValue === '') setAssigned(d.scope);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(hodErrorMessage(err));
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

  const options = assigned ? assigned.department_ids.map((id, i) => ({ id, name: assigned.department_names[i] ?? `Department ${id}` })) : [];
  const levelMax = data ? Math.max(0, ...data.level_distribution.map((l) => l.count)) : 0;
  const roleMax = data ? Math.max(0, ...data.career_role_distribution.map((r) => r.students)) : 0;
  const versions = data?.rule_versions_in_use ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">HOD dashboard</h1>
          <p className="text-sm text-muted-foreground">Aggregate figures only. No individual students are shown.</p>
        </div>
        <Button variant="outline" onClick={refresh} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </Button>
      </div>

      {options.length > 1 && (
        <Card>
          <CardContent className="p-4">
            <div className="max-w-xs space-y-2">
              <Label htmlFor="hod-department">Department</Label>
              <select
                id="hod-department"
                className={SELECT_CLASS}
                value={deptValue}
                onChange={(e) => changeDepartment(e.target.value)}
              >
                <option value="">All my departments</option>
                {options.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
            </div>
          </CardContent>
        </Card>
      )}

      <FormMessage message={error} />

      {loading && !data && !error && (
        <p role="status" className="text-muted-foreground">
          Loading HOD dashboard...
        </p>
      )}

      {data && (
        <div className={loading ? 'space-y-6 opacity-60' : 'space-y-6'} aria-busy={loading}>
          <p className="text-sm text-muted-foreground">
            {data.scope.department_names.length > 0 ? data.scope.department_names.join(', ') : 'No departments'} · generated{' '}
            {formatDate(data.generated_at)}
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
                <StatTile label="Students" value={data.totals.students} />
                <StatTile label="Profiles complete" value={data.totals.profile_complete} />
                <StatTile label="With a readiness score" value={data.totals.with_readiness_score} />
                <StatTile label="With a submitted assessment" value={data.totals.with_assessment_submitted} />
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
                  <CardTitle className="text-lg">Skill heatmap</CardTitle>
                  <CardDescription>Average skill score (0 to 100) among the students assessed on each skill.</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.skill_heatmap.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No skill scores yet.</p>
                  ) : (
                    <SkillHeatmap cells={data.skill_heatmap} />
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Career role goals</CardTitle>
                  <CardDescription>Number of students targeting each role.</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.career_role_distribution.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No career goals set yet.</p>
                  ) : (
                    <BarList
                      ariaLabel="Career role distribution"
                      max={roleMax}
                      items={data.career_role_distribution.map((r) => ({
                        key: String(r.role_id),
                        label: r.role_name,
                        value: r.students,
                        valueText: `${r.students} student(s)`,
                      }))}
                    />
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Assessment trends</CardTitle>
                </CardHeader>
                <CardContent>
                  {data.assessment_trends.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No submitted assessments yet.</p>
                  ) : (
                    <MonthTrendTable
                      caption="Assessment trends by month"
                      countLabel="Submitted attempts"
                      averageLabel="Average (%)"
                      rows={data.assessment_trends.map((t) => ({ month: t.month, count: t.submitted_attempts, average: t.average_percentage }))}
                    />
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Training priorities</CardTitle>
                  <CardDescription>Skills where the most students fall short of role requirements.</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.training_priorities.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No training priorities recorded yet.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <caption className="sr-only">Training priorities</caption>
                        <thead>
                          <tr className="border-b text-muted-foreground">
                            <th scope="col" className="py-2 pr-4 font-medium">Skill</th>
                            <th scope="col" className="py-2 pr-4 font-medium">Students affected</th>
                            <th scope="col" className="py-2 font-medium">High priority</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.training_priorities.map((g) => (
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
            </>
          )}
        </div>
      )}
    </div>
  );
}
