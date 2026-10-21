import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { formatDate } from '@/lib/assessment';
import { formatDash } from '@/lib/dashboard';
import { getErrorMessage } from '@/lib/errors';
import { SHORT_DISCLAIMER } from '@/lib/interview';
import { interviewService } from '@/services/interviewService';
import { roadmapService } from '@/services/roadmapService';
import type { ExplorerRole, InterviewSummary } from '@/types';

interface LoadedData {
  roles: ExplorerRole[];
  history: InterviewSummary[];
}

export function InterviewPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<LoadedData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [roleId, setRoleId] = useState('');
  const [count, setCount] = useState('5');
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([roadmapService.listRoles(), interviewService.list()])
      .then(([roles, history]) => {
        if (cancelled) return;
        const active = roles.filter((r) => r.is_active);
        // Career goals first, then the rest alphabetically.
        active.sort((a, b) => Number(b.is_goal) - Number(a.is_goal) || a.name.localeCompare(b.name));
        setData({ roles: active, history });
        setRoleId((current) => current || (active[0] ? String(active[0].id) : ''));
        setLoadError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(getErrorMessage(err, 'Could not load interview practice.'));
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
    setLoadError(null);
    setAttempt((a) => a + 1);
  }, []);

  const handleStart = async (e: FormEvent): Promise<void> => {
    e.preventDefault();
    const n = Number(count);
    if (!roleId) {
      setStartError('Choose a role first.');
      return;
    }
    if (!Number.isInteger(n) || n < 1 || n > 10) {
      setStartError('Choose between 1 and 10 questions.');
      return;
    }
    setStarting(true);
    setStartError(null);
    try {
      const interview = await interviewService.start(Number(roleId), n);
      navigate(`/interview/${interview.id}`);
    } catch (err) {
      setStartError(getErrorMessage(err, 'Could not start the interview.'));
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <p role="status" className="py-12 text-center text-muted-foreground">
        Loading interview practice...
      </p>
    );
  }
  if (loadError || !data) {
    return (
      <div className="mx-auto max-w-md space-y-4 py-12">
        <FormMessage message={loadError ?? 'Could not load interview practice.'} />
        <Button variant="outline" onClick={retry}>
          Retry
        </Button>
      </div>
    );
  }

  const inProgress = data.history.filter((h) => h.status === 'IN_PROGRESS');

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Mock interview</h1>
        <p className="text-sm text-muted-foreground">
          Answer written questions for a role. {SHORT_DISCLAIMER}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Start an interview</CardTitle>
          <CardDescription>If you already have one in progress for the chosen role, it will be resumed.</CardDescription>
        </CardHeader>
        <CardContent>
          {data.roles.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="no-roles">
              No career roles are available yet.
            </p>
          ) : (
            <form className="space-y-4" onSubmit={(e) => void handleStart(e)} noValidate>
              <div className="space-y-2">
                <Label htmlFor="interview-role">Role</Label>
                <select id="interview-role" className={SELECT_CLASS} value={roleId} onChange={(e) => setRoleId(e.target.value)} disabled={starting}>
                  {data.roles.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                      {r.is_goal ? ' (career goal)' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="interview-count">Number of questions (1-10)</Label>
                <Input id="interview-count" type="number" min={1} max={10} value={count} onChange={(e) => setCount(e.target.value)} disabled={starting} />
              </div>
              <FormMessage message={startError} />
              <Button type="submit" disabled={starting}>
                {starting ? 'Starting...' : 'Start'}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>

      {inProgress.length > 0 && (
        <p className="text-sm" data-testid="in-progress-note">
          You have {inProgress.length} interview{inProgress.length === 1 ? '' : 's'} in progress. Starting the same role resumes it.
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Your interviews</CardTitle>
        </CardHeader>
        <CardContent>
          {data.history.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="no-history">
              You have not taken a mock interview yet.
            </p>
          ) : (
            <ul className="divide-y text-sm" aria-label="Interview history">
              {data.history.map((h) => (
                <li key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span>
                    <span className="font-medium">{h.role_name}</span>{' '}
                    <span className="text-muted-foreground">· {formatDate(h.started_at)}</span>
                  </span>
                  {h.status === 'COMPLETED' ? (
                    <span className="flex items-center gap-3">
                      <span className="text-muted-foreground">Coverage score {formatDash(h.overall)}</span>
                      <Link to={`/interview/${h.id}/result`} className="text-primary hover:underline">
                        View result
                      </Link>
                    </span>
                  ) : (
                    <Link to={`/interview/${h.id}`} className="text-primary hover:underline">
                      Continue
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
