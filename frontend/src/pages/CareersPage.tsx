import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { GoalToggle } from '@/components/roadmap/GoalToggle';
import { GoalsPanel } from '@/components/roadmap/GoalsPanel';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { goalInputs, goalsKey, moveGoal, renumber, toggleGoal } from '@/lib/roadmap';
import { roadmapService } from '@/services/roadmapService';
import { studentService } from '@/services/studentService';
import type { CareerGoal, Department, ExplorerRole } from '@/types';

export function CareersPage() {
  const [roles, setRoles] = useState<ExplorerRole[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [goals, setGoals] = useState<CareerGoal[]>([]);
  const [savedKey, setSavedKey] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([roadmapService.listRoles(), roadmapService.getGoals(), studentService.listDepartments().catch(() => [] as Department[])])
      .then(([r, g, d]) => {
        if (cancelled) return;
        setRoles(r);
        const ordered = renumber(g);
        setGoals(ordered);
        setSavedKey(goalsKey(ordered));
        setDepartments(d);
        setError(null);
        setLoadFailed(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(getErrorMessage(err, 'Could not load career roles.'));
        setLoadFailed(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const departmentName = useMemo(() => new Map(departments.map((d) => [d.id, d.name])), [departments]);
  const goalIds = useMemo(() => new Set(goals.map((g) => g.career_role_id)), [goals]);
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return roles;
    return roles.filter((r) => r.name.toLowerCase().includes(q) || (r.description ?? '').toLowerCase().includes(q));
  }, [roles, search]);
  const dirty = goalsKey(goals) !== savedKey;

  const handleSave = useCallback(async (): Promise<void> => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await roadmapService.saveGoals(goalInputs(goals));
      setSavedKey(goalsKey(goals));
      setSaved(true);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save your goals.'));
    } finally {
      setSaving(false);
    }
  }, [goals]);

  const changeGoals = (next: CareerGoal[]): void => {
    setGoals(next);
    setSaved(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Career explorer</h1>
        <p className="text-sm text-muted-foreground">Browse roles, see what they require, and star the ones you are working towards.</p>
      </div>

      <FormMessage message={error} />
      <FormMessage message={saved ? 'Goals saved.' : null} tone="success" />

      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading careers...
        </p>
      )}
      {!loading && loadFailed && (
        <Button variant="outline" onClick={() => setAttempt((a) => a + 1)}>
          Retry
        </Button>
      )}

      {!loading && !loadFailed && (
        <div className="grid gap-6 md:grid-cols-[2fr_1fr]">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="role-search">Search roles</Label>
              <Input id="role-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="e.g. Backend" />
            </div>
            {roles.length === 0 && <p className="text-muted-foreground">No career roles are available yet.</p>}
            {roles.length > 0 && filtered.length === 0 && <p className="text-muted-foreground">No roles match your search.</p>}
            <ul className="grid gap-3 sm:grid-cols-2" aria-label="Career roles">
              {filtered.map((r) => (
                <li key={r.id}>
                  <Card className="h-full">
                    <CardContent className="space-y-2 p-4">
                      <div className="flex items-start justify-between gap-2">
                        <Link to={`/careers/${r.id}`} className="font-semibold text-primary hover:underline">
                          {r.name}
                        </Link>
                        <GoalToggle roleName={r.name} isGoal={goalIds.has(r.id)} disabled={saving} onToggle={() => changeGoals(toggleGoal(goals, r.id, r.name))} />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {r.department_id !== null ? (departmentName.get(r.department_id) ?? 'Department') : 'All departments'}
                      </p>
                      {r.description && <p className="text-sm">{r.description}</p>}
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          </div>
          <GoalsPanel
            goals={goals}
            dirty={dirty}
            saving={saving}
            onMove={(i, d) => changeGoals(moveGoal(goals, i, d))}
            onRemove={(id) => changeGoals(renumber(goals.filter((g) => g.career_role_id !== id)))}
            onSave={() => void handleSave()}
          />
        </div>
      )}
    </div>
  );
}
