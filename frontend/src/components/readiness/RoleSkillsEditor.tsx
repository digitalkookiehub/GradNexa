import { useState } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { RoleSkill, RoleSkillInput, Skill } from '@/types';

interface RoleSkillsEditorProps {
  skills: Skill[];
  initial: RoleSkill[];
  saving: boolean;
  onSave: (skills: RoleSkillInput[]) => void;
}

interface Row {
  skill_id: number;
  skill_name: string;
  required: string;
  weight: string;
}

export function RoleSkillsEditor({ skills, initial, saving, onSave }: RoleSkillsEditorProps) {
  const [rows, setRows] = useState<Row[]>(() =>
    initial.map((s) => ({ skill_id: s.skill_id, skill_name: s.skill_name, required: String(s.required_level), weight: String(s.weight) })),
  );
  const [pick, setPick] = useState('');
  const [error, setError] = useState<string | null>(null);

  const available = skills.filter((s) => !rows.some((r) => r.skill_id === s.id));

  const addRow = (): void => {
    const skill = skills.find((s) => String(s.id) === pick);
    if (!skill) return;
    setRows((prev) => [...prev, { skill_id: skill.id, skill_name: skill.name, required: '60', weight: '1' }]);
    setPick('');
  };

  const patch = (skillId: number, change: Partial<Row>): void =>
    setRows((prev) => prev.map((r) => (r.skill_id === skillId ? { ...r, ...change } : r)));

  const handleSave = (): void => {
    const payload: RoleSkillInput[] = [];
    for (const r of rows) {
      const required = r.required.trim() === '' ? NaN : Number(r.required);
      const weight = r.weight.trim() === '' ? NaN : Number(r.weight);
      if (!Number.isFinite(required) || required < 0 || required > 100) {
        setError(`Required level for ${r.skill_name} must be between 0 and 100.`);
        return;
      }
      if (!Number.isFinite(weight) || weight <= 0) {
        setError(`Weight for ${r.skill_name} must be greater than 0.`);
        return;
      }
      payload.push({ skill_id: r.skill_id, required_level: required, weight });
    }
    setError(null);
    onSave(payload);
  };

  return (
    <div className="space-y-4" aria-label="Role skills editor" role="group">
      {rows.length === 0 && <p className="text-sm text-muted-foreground">No skills required yet for this role.</p>}
      {rows.map((r) => (
        <div key={r.skill_id} className="flex flex-wrap items-end gap-3" data-testid="role-skill-row">
          <div className="min-w-[10rem] flex-1 text-sm font-medium">{r.skill_name}</div>
          <div className="space-y-1">
            <Label htmlFor={`req-${r.skill_id}`}>Required level for {r.skill_name}</Label>
            <Input id={`req-${r.skill_id}`} type="number" min={0} max={100} step="any" value={r.required} onChange={(e) => patch(r.skill_id, { required: e.target.value })} />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`wt-${r.skill_id}`}>Weight for {r.skill_name}</Label>
            <Input id={`wt-${r.skill_id}`} type="number" min={0} step="any" value={r.weight} onChange={(e) => patch(r.skill_id, { weight: e.target.value })} />
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => setRows((prev) => prev.filter((x) => x.skill_id !== r.skill_id))} aria-label={`Remove ${r.skill_name}`}>
            Remove
          </Button>
        </div>
      ))}

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[12rem] space-y-1">
          <Label htmlFor="skill-picker">Add a skill</Label>
          <select id="skill-picker" className={SELECT_CLASS} value={pick} onChange={(e) => setPick(e.target.value)}>
            <option value="">Select skill</option>
            {available.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.category_name})
              </option>
            ))}
          </select>
        </div>
        <Button type="button" variant="outline" onClick={addRow} disabled={!pick}>
          Add skill
        </Button>
      </div>
      <FormMessage message={error} />
      <Button type="button" onClick={handleSave} disabled={saving}>
        {saving ? 'Saving...' : 'Save skills'}
      </Button>
    </div>
  );
}
