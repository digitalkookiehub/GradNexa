import { useState } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import type { CareerGoal, ExplorerRole } from '@/types';

interface GeneratePlanFormProps {
  roles: ExplorerRole[];
  goals: CareerGoal[];
  initialRoleId: number | null;
  busy: boolean;
  error: string | null;
  onGenerate: (roleId: number, skillsPerWeek: number) => void;
}

export function GeneratePlanForm({ roles, goals, initialRoleId, busy, error, onGenerate }: GeneratePlanFormProps) {
  const goalIds = new Set(goals.map((g) => g.career_role_id));
  const goalRoles = goals.map((g) => roles.find((r) => r.id === g.career_role_id)).filter((r): r is ExplorerRole => r !== undefined);
  const otherRoles = roles.filter((r) => !goalIds.has(r.id));
  const firstGoal = goalRoles.length > 0 ? goalRoles[0].id : null;
  const startId = initialRoleId ?? firstGoal;
  const [roleValue, setRoleValue] = useState(startId === null ? '' : String(startId));
  const [perWeek, setPerWeek] = useState('2');
  const [localError, setLocalError] = useState<string | null>(null);

  const submit = (): void => {
    if (roleValue === '') {
      setLocalError('Select a role to build a plan for.');
      return;
    }
    setLocalError(null);
    onGenerate(Number(roleValue), Number(perWeek));
  };

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="plan-role">Role</Label>
          <select id="plan-role" className={SELECT_CLASS} value={roleValue} onChange={(e) => setRoleValue(e.target.value)} disabled={busy}>
            <option value="">Select a role</option>
            {goalRoles.length > 0 && (
              <optgroup label="My goals">
                {goalRoles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </optgroup>
            )}
            <optgroup label="All roles">
              {otherRoles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </optgroup>
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="skills-per-week">Skills per week</Label>
          <select id="skills-per-week" className={SELECT_CLASS} value={perWeek} onChange={(e) => setPerWeek(e.target.value)} disabled={busy}>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
      </div>
      <FormMessage message={localError ?? error} />
      <Button type="submit" disabled={busy}>
        {busy ? 'Generating...' : 'Generate 30-day plan'}
      </Button>
    </form>
  );
}
