import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { ReadinessSummary } from '@/components/readiness/ReadinessSummary';
import { RoleSelect } from '@/components/readiness/RoleSelect';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/lib/assessment';
import { getErrorMessage, getErrorStatus } from '@/lib/errors';
import { formatScore } from '@/lib/readiness';
import { readinessService } from '@/services/readinessService';
import type { CareerRole, ReadinessResult } from '@/types';

function toRoleId(value: string): number | null {
  return value === '' ? null : Number(value);
}

export function ReadinessPage() {
  const [roles, setRoles] = useState<CareerRole[]>([]);
  const [roleValue, setRoleValue] = useState('');
  const [result, setResult] = useState<ReadinessResult | null>(null);
  const [history, setHistory] = useState<ReadinessResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noRule, setNoRule] = useState(false);

  useEffect(() => {
    let cancelled = false;
    readinessService
      .listRoles()
      .then((r) => {
        if (!cancelled) setRoles(r);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load career roles.'));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const roleId = toRoleId(roleValue);
    setLoading(true);
    setResult(null);
    setHistory([]);
    setNoRule(false);
    Promise.all([
      readinessService.getLatest(roleId).catch((err: unknown) => {
        if (getErrorStatus(err) === 404) return null;
        throw err;
      }),
      readinessService.history(roleId).catch((err: unknown) => {
        if (getErrorStatus(err) === 404) return [] as ReadinessResult[];
        throw err;
      }),
    ])
      .then(([latest, hist]) => {
        if (cancelled) return;
        setResult(latest);
        setHistory(hist);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load your readiness.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [roleValue]);

  const handleCompute = useCallback(async (): Promise<void> => {
    setComputing(true);
    setError(null);
    setNoRule(false);
    const roleId = toRoleId(roleValue);
    try {
      const computed = await readinessService.compute(roleId);
      setResult(computed);
      try {
        setHistory(await readinessService.history(roleId));
      } catch {
        setHistory((prev) => [computed, ...prev]);
      }
    } catch (err) {
      if (getErrorStatus(err) === 409) setNoRule(true);
      else setError(getErrorMessage(err, 'Could not compute your readiness.'));
    } finally {
      setComputing(false);
    }
  }, [roleValue]);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Placement readiness</h1>
        <Link to="/readiness/gaps" className="text-sm text-primary hover:underline">
          View skill gaps
        </Link>
      </div>
      <p className="text-sm text-muted-foreground">
        Your readiness is calculated from the assessment evidence you have so far. Check the coverage figure to see how much of it is backed by results.
      </p>

      <Card>
        <CardContent className="flex flex-wrap items-end gap-4 p-4">
          <div className="min-w-[14rem] flex-1">
            <RoleSelect id="readiness-role" roles={roles} value={roleValue} onChange={setRoleValue} allowGeneral disabled={computing} />
          </div>
          <Button onClick={() => void handleCompute()} disabled={computing || loading}>
            {computing ? 'Computing...' : 'Compute / refresh'}
          </Button>
        </CardContent>
      </Card>

      <FormMessage message={error} />
      {noRule && (
        <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          No readiness rule is configured yet, so readiness cannot be computed. Please ask an administrator to activate a readiness rule.
        </div>
      )}

      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading readiness...
        </p>
      )}

      {!loading && !result && !error && (
        <p className="text-muted-foreground" data-testid="not-computed">
          You have not computed readiness for this selection yet. Choose Compute / refresh to calculate it.
        </p>
      )}

      {result && <ReadinessSummary result={result} />}

      {history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">History</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y text-sm" aria-label="Readiness history">
              {history.map((h) => (
                <li key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span>{formatDate(h.computed_at)}</span>
                  <span className="text-muted-foreground">
                    {h.overall === null ? 'Not enough evidence' : `${formatScore(h.overall)}${h.level ? ` (${h.level})` : ''}`} · coverage{' '}
                    {formatScore(h.coverage)}% · rule v{h.rule_version}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
