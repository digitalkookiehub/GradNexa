import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { GoalToggle } from '@/components/roadmap/GoalToggle';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/lib/assessment';
import { getErrorMessage } from '@/lib/errors';
import { formatScore } from '@/lib/readiness';
import { goalInputs, toggleGoal } from '@/lib/roadmap';
import { roadmapService } from '@/services/roadmapService';
import type { RoleDetailView } from '@/types';

export function CareerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const roleId = Number(id);
  const [role, setRole] = useState<RoleDetailView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [goalBusy, setGoalBusy] = useState(false);
  const [goalError, setGoalError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setRole(null);
    if (!Number.isInteger(roleId)) {
      setError('This career role does not exist.');
      setLoading(false);
      return;
    }
    roadmapService
      .getRole(roleId)
      .then((r) => {
        if (cancelled) return;
        setRole(r);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load this career role.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [roleId]);

  const handleToggleGoal = useCallback(async (): Promise<void> => {
    if (!role) return;
    setGoalBusy(true);
    setGoalError(null);
    try {
      const current = await roadmapService.getGoals();
      const next = toggleGoal(current, role.id, role.name);
      await roadmapService.saveGoals(goalInputs(next));
      setRole({ ...role, is_goal: next.some((g) => g.career_role_id === role.id) });
    } catch (err) {
      setGoalError(getErrorMessage(err, 'Could not update your goals.'));
    } finally {
      setGoalBusy(false);
    }
  }, [role]);

  const readiness = role?.my_readiness ?? null;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to="/careers" className="text-sm text-primary hover:underline">
        Back to careers
      </Link>
      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading role...
        </p>
      )}
      <FormMessage message={error} />
      <FormMessage message={goalError} />

      {role && (
        <>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h1 className="text-2xl font-semibold">{role.name}</h1>
              {role.description && <p className="text-sm text-muted-foreground">{role.description}</p>}
            </div>
            <GoalToggle roleName={role.name} isGoal={role.is_goal} disabled={goalBusy} onToggle={() => void handleToggleGoal()} />
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">My readiness for this role</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm" data-testid="my-readiness">
              {readiness === null ? (
                <p>
                  You have not computed readiness for this role yet.{' '}
                  <Link to="/readiness" className="text-primary hover:underline">
                    Compute it on the readiness page
                  </Link>
                </p>
              ) : readiness.overall === null ? (
                <p>
                  Not enough evidence yet (coverage {formatScore(readiness.coverage)}%).{' '}
                  <Link to="/assessments" className="text-primary hover:underline">
                    Go to assessments
                  </Link>
                </p>
              ) : (
                <p>
                  <span className="text-2xl font-bold">{formatScore(readiness.overall)}</span> / 100
                  {readiness.level ? ` (${readiness.level})` : ''} · coverage {formatScore(readiness.coverage)}% · rule v{readiness.rule_version} · computed{' '}
                  {formatDate(readiness.computed_at)}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Required skills</CardTitle>
              <CardDescription>The level and weight this role expects for each skill.</CardDescription>
            </CardHeader>
            <CardContent>
              {role.skills.length === 0 ? (
                <p className="text-sm text-muted-foreground">No skills have been defined for this role yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b text-muted-foreground">
                        <th className="py-2 pr-4 font-medium">Skill</th>
                        <th className="py-2 pr-4 font-medium">Required level</th>
                        <th className="py-2 font-medium">Weight</th>
                      </tr>
                    </thead>
                    <tbody>
                      {role.skills.map((s) => (
                        <tr key={s.skill_id} className="border-b last:border-0">
                          <td className="py-2 pr-4">{s.skill_name}</td>
                          <td className="py-2 pr-4">{formatScore(s.required_level)}</td>
                          <td className="py-2">{formatScore(s.weight)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex flex-wrap gap-3">
            <Button asChild variant="outline">
              <Link to={`/readiness/gaps?role=${role.id}`}>View skill gaps</Link>
            </Button>
            <Button asChild>
              <Link to={`/plan?role=${role.id}`}>Generate 30-day plan</Link>
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
