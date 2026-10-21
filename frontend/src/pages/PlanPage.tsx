import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { GeneratePlanForm } from '@/components/roadmap/GeneratePlanForm';
import { PlanItemRow } from '@/components/roadmap/PlanItemRow';
import { ReassessPanel } from '@/components/roadmap/ReassessPanel';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/lib/assessment';
import { getErrorMessage } from '@/lib/errors';
import { formatScore } from '@/lib/readiness';
import { replaceItem } from '@/lib/roadmap';
import { roadmapService } from '@/services/roadmapService';
import type { CareerGoal, ExplorerRole, Plan, PlanItem, PlanItemStatus, ReassessResult } from '@/types';

export function PlanPage() {
  const [searchParams] = useSearchParams();
  const requested = Number(searchParams.get('role'));
  const requestedRoleId = Number.isInteger(requested) && requested > 0 ? requested : null;

  const [plan, setPlan] = useState<Plan | null>(null);
  const [roles, setRoles] = useState<ExplorerRole[]>([]);
  const [goals, setGoals] = useState<CareerGoal[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [confirmPending, setConfirmPending] = useState<{ roleId: number; perWeek: number } | null>(null);
  const [pendingItems, setPendingItems] = useState<number[]>([]);
  const [itemError, setItemError] = useState<string | null>(null);
  const [reassessing, setReassessing] = useState(false);
  const [reassessError, setReassessError] = useState<string | null>(null);
  const [reassess, setReassess] = useState<ReassessResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([roadmapService.getActivePlan(), roadmapService.listRoles(), roadmapService.getGoals()])
      .then(([p, r, g]) => {
        if (cancelled) return;
        setPlan(p);
        setRoles(r);
        setGoals(g);
        setLoadError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(getErrorMessage(err, 'Could not load your plan.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const runGenerate = useCallback(async (roleId: number, perWeek: number): Promise<void> => {
    setGenerating(true);
    setGenerateError(null);
    try {
      const created = await roadmapService.generatePlan({ role_id: roleId, skills_per_week: perWeek });
      setPlan(created);
      setReassess(null);
      setShowForm(false);
    } catch (err) {
      setGenerateError(getErrorMessage(err, 'Could not generate your plan.'));
    } finally {
      setGenerating(false);
    }
  }, []);

  const handleGenerate = (roleId: number, perWeek: number): void => {
    if (plan) setConfirmPending({ roleId, perWeek });
    else void runGenerate(roleId, perWeek);
  };

  const handleStatusChange = useCallback(async (item: PlanItem, status: PlanItemStatus): Promise<void> => {
    const previous = item.status;
    const previousCompletedAt = item.completed_at;
    setItemError(null);
    setPendingItems((p) => [...p, item.id]);
    setPlan((cur) => (cur ? replaceItem(cur, item.id, { status }) : cur));
    try {
      const saved = await roadmapService.updateItem(item.id, status);
      setPlan((cur) => (cur ? replaceItem(cur, item.id, saved) : cur));
    } catch (err) {
      setPlan((cur) => (cur ? replaceItem(cur, item.id, { status: previous, completed_at: previousCompletedAt }) : cur));
      setItemError(getErrorMessage(err, 'Could not update that task. Your change was reverted.'));
    } finally {
      setPendingItems((p) => p.filter((id) => id !== item.id));
    }
  }, []);

  const handleReassess = useCallback(async (): Promise<void> => {
    setReassessing(true);
    setReassessError(null);
    try {
      setReassess(await roadmapService.reassess());
    } catch (err) {
      setReassessError(getErrorMessage(err, 'Could not refresh your readiness.'));
    } finally {
      setReassessing(false);
    }
  }, []);

  const formVisible = !loading && !loadError && (plan === null || showForm);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">30-day plan</h1>
        <Link to="/plan/progress" className="text-sm text-primary hover:underline">
          Plan history
        </Link>
      </div>

      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading your plan...
        </p>
      )}
      {loadError && (
        <div className="space-y-3">
          <FormMessage message={loadError} />
          <Button variant="outline" onClick={() => setAttempt((a) => a + 1)}>
            Retry
          </Button>
        </div>
      )}

      {!loading && !loadError && plan === null && (
        <p className="text-muted-foreground" data-testid="no-plan">
          You do not have an active plan. Pick a role to generate one. Readiness for that role must be computed first.
        </p>
      )}

      {plan && !loadError && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{plan.role_name}</CardTitle>
              <CardDescription>
                Starts {plan.starts_on} · {plan.duration_days} days · {plan.skills_per_week} skill(s) per week
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label htmlFor="plan-progress" className="font-medium">
                    Progress
                  </label>
                  <span data-testid="progress-text">
                    {plan.progress.done} of {plan.progress.total} done ({formatScore(plan.progress.percent)}%)
                  </span>
                </div>
                <progress id="plan-progress" className="h-2 w-full" value={plan.progress.percent} max={100} aria-label="Plan progress" />
              </div>
              <div data-testid="baseline">
                <span className="font-medium">Baseline: </span>
                {plan.baseline === null
                  ? 'No baseline was recorded for this plan.'
                  : plan.baseline.overall === null
                    ? `Not enough evidence at the time (rule v${plan.baseline.rule_version}, ${formatDate(plan.baseline.computed_at)}).`
                    : `${formatScore(plan.baseline.overall)}${plan.baseline.level ? ` (${plan.baseline.level})` : ''} · rule v${plan.baseline.rule_version} · ${formatDate(plan.baseline.computed_at)}`}
              </div>
            </CardContent>
          </Card>

          {plan.unscheduled_skills.length > 0 && (
            <div role="note" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900" data-testid="unscheduled">
              <p className="font-medium">These skills did not fit into this plan and are not scheduled:</p>
              <ul className="list-disc pl-5">
                {plan.unscheduled_skills.map((s) => (
                  <li key={s.skill_id}>
                    {s.skill_name}
                    {s.gap !== null ? ` (gap ${formatScore(s.gap)})` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <FormMessage message={itemError} />

          {plan.weeks.map((w) => (
            <section key={w.week} aria-label={`Week ${w.week}`} className="space-y-2">
              <h2 className="text-lg font-semibold">Week {w.week}</h2>
              {w.items.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nothing scheduled this week.</p>
              ) : (
                <ul className="space-y-2">
                  {w.items.map((item) => (
                    <PlanItemRow key={item.id} item={item} pending={pendingItems.includes(item.id)} onStatusChange={(i, s) => void handleStatusChange(i, s)} />
                  ))}
                </ul>
              )}
            </section>
          ))}

          <Card>
            <CardContent className="space-y-3 p-4">
              <div className="flex flex-wrap gap-3">
                <Button onClick={() => void handleReassess()} disabled={reassessing}>
                  {reassessing ? 'Refreshing...' : 'Refresh readiness (reassess)'}
                </Button>
                {!showForm && (
                  <Button variant="outline" onClick={() => setShowForm(true)}>
                    Generate a new plan
                  </Button>
                )}
              </div>
              <FormMessage message={reassessError} />
            </CardContent>
          </Card>

          {reassess && <ReassessPanel result={reassess} />}
        </>
      )}

      {confirmPending && (
        <ConfirmPanel
          title="Generate a new plan?"
          message="You already have an active plan. Generating a new one may replace it. Check Plan history afterwards."
          confirmLabel="Generate new plan"
          busy={generating}
          onConfirm={() => {
            const pending = confirmPending;
            setConfirmPending(null);
            void runGenerate(pending.roleId, pending.perWeek);
          }}
          onCancel={() => setConfirmPending(null)}
        />
      )}

      {formVisible && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Generate a plan</CardTitle>
          </CardHeader>
          <CardContent>
            <GeneratePlanForm roles={roles} goals={goals} initialRoleId={requestedRoleId} busy={generating} error={generateError} onGenerate={handleGenerate} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
