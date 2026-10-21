import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { RoleSelect } from '@/components/readiness/RoleSelect';
import { Card, CardContent } from '@/components/ui/card';
import { getErrorMessage, getErrorStatus } from '@/lib/errors';
import { formatScore, GAP_STATUS_LABELS, PRIORITY_CLASSES, PRIORITY_LABELS, sortGaps } from '@/lib/readiness';
import { readinessService } from '@/services/readinessService';
import type { CareerRole, Gap } from '@/types';

export function SkillGapsPage() {
  const [searchParams] = useSearchParams();
  const requestedRole = searchParams.get('role');
  const [roles, setRoles] = useState<CareerRole[]>([]);
  const [rolesLoading, setRolesLoading] = useState(true);
  const [roleValue, setRoleValue] = useState('');
  const [gaps, setGaps] = useState<Gap[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [notComputed, setNotComputed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    readinessService
      .listRoles()
      .then((r) => {
        if (cancelled) return;
        setRoles(r);
        if (r.length > 0) {
          const requested = r.find((x) => String(x.id) === requestedRole);
          setRoleValue(String((requested ?? r[0]).id));
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load career roles.'));
      })
      .finally(() => {
        if (!cancelled) setRolesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [requestedRole]);

  useEffect(() => {
    if (roleValue === '') return;
    let cancelled = false;
    setLoading(true);
    setGaps(null);
    setNotComputed(false);
    readinessService
      .gaps(Number(roleValue))
      .then((g) => {
        if (cancelled) return;
        setGaps(g);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (getErrorStatus(err) === 404) {
          setNotComputed(true);
          setError(null);
        } else {
          setError(getErrorMessage(err, 'Could not load your skill gaps.'));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [roleValue]);

  const sorted = useMemo(() => (gaps ? sortGaps(gaps) : []), [gaps]);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="text-2xl font-semibold">Skill gaps</h1>
      <Card>
        <CardContent className="p-4">
          <div className="max-w-sm">
            <RoleSelect id="gaps-role" roles={roles} value={roleValue} onChange={setRoleValue} allowGeneral={false} disabled={rolesLoading} />
          </div>
        </CardContent>
      </Card>

      <FormMessage message={error} />
      {(rolesLoading || loading) && (
        <p role="status" className="text-muted-foreground">
          Loading skill gaps...
        </p>
      )}
      {!rolesLoading && roles.length === 0 && !error && <p className="text-muted-foreground">No career roles are available yet.</p>}

      {notComputed && (
        <div className="space-y-2 rounded-md border bg-background p-4" data-testid="compute-first">
          <p className="font-medium">Compute your readiness for this role first</p>
          <p className="text-sm text-muted-foreground">Skill gaps are based on a readiness result. None exists for this role yet.</p>
          <Link to="/readiness" className="text-sm text-primary hover:underline">
            Go to readiness
          </Link>
        </div>
      )}

      {gaps && sorted.length === 0 && <p className="text-muted-foreground">This role has no required skills configured.</p>}
      {sorted.length > 0 && (
        <div className="overflow-x-auto rounded-md border bg-background">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-muted-foreground">
                <th className="p-3 font-medium">Skill</th>
                <th className="p-3 font-medium">Current</th>
                <th className="p-3 font-medium">Required</th>
                <th className="p-3 font-medium">Gap</th>
                <th className="p-3 font-medium">Status</th>
                <th className="p-3 font-medium">Priority</th>
                <th className="p-3 font-medium">Recommended action</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((g) => (
                <tr key={g.skill_id} className="border-b last:border-0">
                  <td className="p-3 font-medium">{g.skill_name}</td>
                  <td className="p-3">{g.current === null ? 'Not assessed' : formatScore(g.current)}</td>
                  <td className="p-3">{formatScore(g.required)}</td>
                  <td className="p-3">{formatScore(g.gap)}</td>
                  <td className="p-3">{GAP_STATUS_LABELS[g.status]}</td>
                  <td className="p-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_CLASSES[g.priority]}`} data-testid="priority-badge">
                      {PRIORITY_LABELS[g.priority]}
                    </span>
                  </td>
                  <td className="p-3">{g.recommended_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
