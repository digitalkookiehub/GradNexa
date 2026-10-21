import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { BarList } from '@/components/dashboard/BarList';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/lib/assessment';
import { formatDash, notImplementedLabel } from '@/lib/dashboard';
import { getErrorMessage } from '@/lib/errors';
import { SHORT_DISCLAIMER } from '@/lib/interview';
import { PRIORITY_CLASSES, PRIORITY_LABELS } from '@/lib/readiness';
import { dashboardService } from '@/services/dashboardService';
import type { DashboardReadiness, StudentDashboard } from '@/types';

const QUICK_LINKS: { to: string; label: string }[] = [
  { to: '/assessments', label: 'Take an assessment' },
  { to: '/readiness', label: 'Readiness details' },
  { to: '/readiness/gaps', label: 'Skill gaps' },
  { to: '/careers', label: 'Explore careers' },
  { to: '/plan', label: 'My plan' },
  { to: '/profile/projects', label: 'Projects & certifications' },
];

function ReadinessBlock({ r, title }: { r: DashboardReadiness; title: string }) {
  const partial = r.coverage < 100;
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">{title}</h3>
      {r.overall === null ? (
        <div data-testid="no-overall">
          <p className="text-lg font-semibold">Not enough evidence yet</p>
          <p className="text-sm text-muted-foreground">
            Complete more assessments to build evidence.{' '}
            <Link to="/readiness" className="text-primary hover:underline">
              View readiness
            </Link>
          </p>
        </div>
      ) : (
        <div className="flex flex-wrap items-baseline gap-3">
          <span className="text-3xl font-bold" data-testid="overall-score">
            {formatDash(r.overall)}
            <span className="text-base font-normal text-muted-foreground"> / 100</span>
          </span>
          {r.level && <span className="rounded-full bg-primary/10 px-3 py-1 text-sm font-medium text-primary">{r.level}</span>}
        </div>
      )}
      <p className="text-sm text-muted-foreground" data-testid="coverage-line">
        Coverage {formatDash(r.coverage)}%{partial && r.overall !== null ? ' (partial evidence, this score may change)' : ''} · rule v{r.rule_version} · computed{' '}
        {formatDate(r.computed_at)}
      </p>
    </div>
  );
}

export function DashboardPage() {
  const [data, setData] = useState<StudentDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    dashboardService
      .getStudent()
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load your dashboard.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const retry = useCallback((): void => {
    setLoading(true);
    setError(null);
    setAttempt((a) => a + 1);
  }, []);

  if (loading) {
    return (
      <p role="status" className="py-12 text-center text-muted-foreground">
        Loading your dashboard...
      </p>
    );
  }
  if (error || !data) {
    return (
      <div className="mx-auto max-w-md space-y-4 py-12">
        <FormMessage message={error ?? 'Could not load your dashboard.'} />
        <Button variant="outline" onClick={retry}>
          Retry
        </Button>
      </div>
    );
  }

  const meta = [data.profile.department_name, data.profile.roll_number ? `Roll no. ${data.profile.roll_number}` : null].filter(Boolean).join(' · ');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Your dashboard</h1>
        {meta && <p className="text-sm text-muted-foreground">{meta}</p>}
      </div>

      {!data.rule_active && (
        <div role="status" className="rounded-md border bg-muted px-3 py-2 text-sm" data-testid="no-rule">
          Readiness scoring has not been configured yet, so no readiness scores are available. Please check back later.
        </div>
      )}

      <nav aria-label="Quick links" className="flex flex-wrap gap-2">
        {QUICK_LINKS.map((l) => (
          <Link key={l.to} to={l.to} className="rounded-md border bg-background px-3 py-1.5 text-sm hover:bg-accent">
            {l.label}
          </Link>
        ))}
      </nav>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Readiness</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {data.readiness.general ? (
              <ReadinessBlock r={data.readiness.general} title="General readiness" />
            ) : (
              <div data-testid="no-general">
                <p className="text-lg font-semibold">Not enough evidence yet</p>
                <p className="text-sm text-muted-foreground">
                  {data.rule_active ? 'Complete assessments to get a readiness score. ' : ''}
                  <Link to="/readiness" className="text-primary hover:underline">
                    Go to readiness
                  </Link>
                </p>
              </div>
            )}
            {data.readiness.roles.length > 0 && (
              <ul className="divide-y text-sm" aria-label="Role readiness">
                {data.readiness.roles.map((r) => (
                  <li key={r.role_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                    <span className="font-medium">{r.role_name}</span>
                    <span className="text-muted-foreground">
                      {r.overall === null ? 'Not enough evidence' : `${formatDash(r.overall)}${r.level ? ` (${r.level})` : ''}`} · coverage {formatDash(r.coverage)}%
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Skills</CardTitle>
            <CardDescription>Scores out of 100 with the number of results behind each.</CardDescription>
          </CardHeader>
          <CardContent>
            {data.skills.length === 0 ? (
              <p className="text-sm text-muted-foreground" data-testid="no-skills">
                No skill scores yet.{' '}
                <Link to="/assessments" className="text-primary hover:underline">
                  Take an assessment
                </Link>
              </p>
            ) : (
              <BarList
                ariaLabel="Skill scores"
                max={100}
                items={data.skills.map((s) => ({
                  key: String(s.skill_id),
                  label: s.skill_name,
                  hint: s.category_name,
                  value: s.score,
                  valueText: `${formatDash(s.score)} / 100 · ${s.evidence_count} result(s)`,
                }))}
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Top skill gaps</CardTitle>
          </CardHeader>
          <CardContent>
            {data.top_gaps.length === 0 ? (
              <p className="text-sm text-muted-foreground" data-testid="no-gaps">
                No skill gaps to show yet. Set a career goal and take assessments to see them.
              </p>
            ) : (
              <ul className="divide-y text-sm" aria-label="Top skill gaps">
                {data.top_gaps.map((g) => (
                  <li key={`${g.role_id}-${g.skill_id}`} className="space-y-1 py-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium">
                        {g.skill_name} <span className="font-normal text-muted-foreground">for {g.role_name}</span>
                      </span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_CLASSES[g.priority]}`}>{PRIORITY_LABELS[g.priority]} priority</span>
                    </div>
                    <p className="text-muted-foreground">
                      Current {g.current === null ? 'no evidence' : formatDash(g.current)} · required {formatDash(g.required)}
                      {g.gap !== null ? ` · gap ${formatDash(g.gap)}` : ''}
                    </p>
                    {g.recommended_action && <p>{g.recommended_action}</p>}
                    <Link to={`/readiness/gaps?role=${g.role_id}`} className="text-primary hover:underline">
                      See gaps for {g.role_name}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Learning plan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.plan ? (
              <>
                <p className="text-sm font-medium">
                  {data.plan.role_name} <span className="font-normal text-muted-foreground">({data.plan.status})</span>
                </p>
                <BarList
                  ariaLabel="Plan progress"
                  max={100}
                  items={[
                    {
                      key: 'plan',
                      label: 'Progress',
                      value: data.plan.progress.percent,
                      valueText: `${formatDash(data.plan.progress.percent)}% (${data.plan.progress.done} of ${data.plan.progress.total} done)`,
                    },
                  ]}
                />
                <Link to="/plan" className="text-sm text-primary hover:underline">
                  Open my plan
                </Link>
              </>
            ) : (
              <p className="text-sm text-muted-foreground" data-testid="no-plan">
                You do not have a learning plan yet.{' '}
                <Link to="/careers" className="text-primary hover:underline">
                  Choose a career to get started
                </Link>
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Career goals</CardTitle>
          </CardHeader>
          <CardContent>
            {data.goals.length === 0 ? (
              <p className="text-sm text-muted-foreground" data-testid="no-goals">
                No career goals set.{' '}
                <Link to="/careers" className="text-primary hover:underline">
                  Browse careers
                </Link>
              </p>
            ) : (
              <ul className="divide-y text-sm" aria-label="Career goals">
                {data.goals.map((g) => (
                  <li key={g.career_role_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                    <Link to={`/careers/${g.career_role_id}`} className="font-medium text-primary hover:underline">
                      {g.role_name}
                    </Link>
                    <span className="text-muted-foreground">Priority {g.priority}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent assessments</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.recent_assessments.length === 0 ? (
              <p className="text-sm text-muted-foreground" data-testid="no-assessments">
                You have not submitted any assessments yet.{' '}
                <Link to="/assessments" className="text-primary hover:underline">
                  Browse assessments
                </Link>
              </p>
            ) : (
              <ul className="divide-y text-sm" aria-label="Recent assessments">
                {data.recent_assessments.map((a) => (
                  <li key={a.attempt_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                    <Link to={`/attempts/${a.attempt_id}/result`} className="font-medium text-primary hover:underline">
                      {a.assessment_title}
                    </Link>
                    <span className="text-muted-foreground">
                      {formatDash(a.percentage)}% · {formatDate(a.submitted_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <Link to="/assessments/history" className="text-sm text-primary hover:underline">
              View full history
            </Link>
          </CardContent>
        </Card>

        <Card data-testid="resume-card">
          <CardHeader>
            <CardTitle className="text-lg">Resume</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {data.resume ? (
              <>
                <p className="font-medium">{data.resume.filename}</p>
                <p className="text-muted-foreground">
                  {data.resume.analyzed_at ? `Analyzed ${formatDate(data.resume.analyzed_at)}` : 'Not analyzed yet'}
                  {data.resume.role_name && data.resume.role_match_percent !== null
                    ? ` · ${formatDash(data.resume.role_match_percent)}% keyword match for ${data.resume.role_name}`
                    : ''}
                </p>
                <Link to="/resume" className="text-primary hover:underline">
                  Open my resume
                </Link>
              </>
            ) : (
              <p className="text-muted-foreground" data-testid="no-resume">
                You have not uploaded a resume yet.{' '}
                <Link to="/resume" className="text-primary hover:underline">
                  Upload your resume
                </Link>
              </p>
            )}
          </CardContent>
        </Card>

        <Card data-testid="interview-card">
          <CardHeader>
            <CardTitle className="text-lg">Mock interview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {data.interview && data.interview.completed_count > 0 ? (
              <>
                <p>
                  {data.interview.completed_count} completed interview{data.interview.completed_count === 1 ? '' : 's'}
                </p>
                {data.interview.latest && (
                  <p className="text-muted-foreground">
                    Latest ({data.interview.latest.role_name}):{' '}
                    {data.interview.latest.overall === null ? 'no coverage score' : `${formatDash(data.interview.latest.overall)} / 100 coverage`} ·{' '}
                    {formatDate(data.interview.latest.computed_at)}
                  </p>
                )}
                <p className="text-xs text-muted-foreground">{SHORT_DISCLAIMER}</p>
                <Link to="/interview" className="text-primary hover:underline">
                  Open mock interviews
                </Link>
              </>
            ) : (
              <p className="text-muted-foreground" data-testid="no-interview">
                You have not completed a mock interview yet.{' '}
                <Link to="/interview" className="text-primary hover:underline">
                  Start a mock interview
                </Link>
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {data.not_implemented.length > 0 && (
        <Card data-testid="coming-later">
          <CardHeader>
            <CardTitle className="text-lg">Coming in a later phase</CardTitle>
            <CardDescription>These are not available yet, so no score is shown for them.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {data.not_implemented.map((key) => (
                <li key={key}>{notImplementedLabel(key)}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
