import { useState } from 'react';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { FieldError } from '@/components/auth/FieldError';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  CGPA_BASIS_OPTIONS,
  MAX_NOTES,
  buildEligibilityPayload,
  formFromRule,
  type EligibilityErrors,
  type EligibilityFormState,
} from './validation';
import type { Department } from '@/types';
import type { CgpaBasis, EligibilityRuleInput, EligibilityRuleOut } from '@/types/jobAdmin';

interface EligibilityFormProps {
  initial: EligibilityRuleOut | null;
  departments: Department[];
  saving: boolean;
  readOnly: boolean;
  onSave: (payload: EligibilityRuleInput) => void;
  onRemove: () => void;
}

export function EligibilityForm({ initial, departments, saving, readOnly, onSave, onRemove }: EligibilityFormProps) {
  const [form, setForm] = useState<EligibilityFormState>(() => formFromRule(initial));
  const [errors, setErrors] = useState<EligibilityErrors>({});
  const [confirmRemove, setConfirmRemove] = useState(false);

  const patch = (change: Partial<EligibilityFormState>): void => setForm((prev) => ({ ...prev, ...change }));

  const toggleDepartment = (id: number): void =>
    patch({ departmentIds: form.departmentIds.includes(id) ? form.departmentIds.filter((d) => d !== id) : [...form.departmentIds, id] });

  const handleSave = (): void => {
    const result = buildEligibilityPayload(form);
    setErrors(result.errors);
    if (result.payload) onSave(result.payload);
  };

  const basisHelp = CGPA_BASIS_OPTIONS.find((o) => o.value === form.cgpaBasis)?.help;

  return (
    <form
      className="space-y-5"
      aria-label="Eligibility rule form"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        handleSave();
      }}
    >
      <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm">
        Eligibility criteria are checked automatically against student records. Custom notes are shown to students but are NOT evaluated.
      </p>

      <fieldset disabled={readOnly || saving} className="space-y-5">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input id="el-cgpa-on" type="checkbox" checked={form.cgpaOn} onChange={(e) => patch({ cgpaOn: e.target.checked })} />
            <Label htmlFor="el-cgpa-on">Minimum CGPA</Label>
          </div>
          {form.cgpaOn && (
            <div className="grid gap-3 pl-6 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="el-cgpa-min">Minimum CGPA (0-10)</Label>
                <Input id="el-cgpa-min" type="number" step="any" min={0} max={10} value={form.cgpaMin} onChange={(e) => patch({ cgpaMin: e.target.value })} aria-invalid={Boolean(errors.cgpaMin)} />
                <FieldError id="el-cgpa-min-error" message={errors.cgpaMin} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="el-cgpa-basis">CGPA basis</Label>
                <select
                  id="el-cgpa-basis"
                  className={SELECT_CLASS}
                  value={form.cgpaBasis}
                  onChange={(e) => patch({ cgpaBasis: e.target.value as CgpaBasis | '' })}
                  aria-invalid={Boolean(errors.cgpaBasis)}
                >
                  <option value="">Select a basis</option>
                  {CGPA_BASIS_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <FieldError id="el-cgpa-basis-error" message={errors.cgpaBasis} />
                {basisHelp && <p className="text-xs text-muted-foreground">{basisHelp}</p>}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input id="el-arrears-on" type="checkbox" checked={form.arrearsOn} onChange={(e) => patch({ arrearsOn: e.target.checked })} />
            <Label htmlFor="el-arrears-on">Maximum arrears</Label>
          </div>
          {form.arrearsOn && (
            <div className="space-y-1 pl-6">
              <Label htmlFor="el-arrears">Maximum arrears allowed</Label>
              <Input id="el-arrears" type="number" step="1" min={0} value={form.maxArrears} onChange={(e) => patch({ maxArrears: e.target.value })} aria-invalid={Boolean(errors.maxArrears)} />
              <FieldError id="el-arrears-error" message={errors.maxArrears} />
            </div>
          )}
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input id="el-att-on" type="checkbox" checked={form.attendanceOn} onChange={(e) => patch({ attendanceOn: e.target.checked })} />
            <Label htmlFor="el-att-on">Minimum attendance</Label>
          </div>
          {form.attendanceOn && (
            <div className="space-y-1 pl-6">
              <Label htmlFor="el-att">Minimum attendance % (0-100)</Label>
              <Input id="el-att" type="number" step="any" min={0} max={100} value={form.attendanceMin} onChange={(e) => patch({ attendanceMin: e.target.value })} aria-invalid={Boolean(errors.attendanceMin)} />
              <FieldError id="el-att-error" message={errors.attendanceMin} />
            </div>
          )}
        </div>

        <div className="space-y-2">
          <div className="text-sm font-medium">Departments</div>
          <p className="text-xs text-muted-foreground">
            {form.departmentIds.length === 0 ? 'All departments' : `${form.departmentIds.length} selected`}. Leave none selected to allow all departments.
          </p>
          <div className="grid gap-1 sm:grid-cols-2" role="group" aria-label="Departments">
            {departments.map((d) => (
              <label key={d.id} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.departmentIds.includes(d.id)} onChange={() => toggleDepartment(d.id)} />
                {d.name}
              </label>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input id="el-years-on" type="checkbox" checked={form.yearsOn} onChange={(e) => patch({ yearsOn: e.target.checked })} />
            <Label htmlFor="el-years-on">Graduation years</Label>
          </div>
          {form.yearsOn && (
            <div className="space-y-1 pl-6">
              <Label htmlFor="el-years">Graduation years (comma-separated)</Label>
              <Input id="el-years" value={form.years} placeholder="2026, 2027" onChange={(e) => patch({ years: e.target.value })} aria-invalid={Boolean(errors.years)} />
              <FieldError id="el-years-error" message={errors.years} />
            </div>
          )}
        </div>

        <div className="space-y-2">
          <div className="text-sm font-medium">Custom notes (not evaluated)</div>
          {form.notes.map((note, i) => (
            <div key={i} className="flex items-center gap-2">
              <Input aria-label={`Custom note ${i + 1}`} value={note} onChange={(e) => patch({ notes: form.notes.map((n, j) => (j === i ? e.target.value : n)) })} />
              <Button type="button" variant="outline" size="sm" aria-label={`Remove note ${i + 1}`} onClick={() => patch({ notes: form.notes.filter((_, j) => j !== i) })}>
                Remove
              </Button>
            </div>
          ))}
          <FieldError id="el-notes-error" message={errors.notes} />
          <Button type="button" variant="outline" size="sm" disabled={form.notes.length >= MAX_NOTES} onClick={() => patch({ notes: [...form.notes, ''] })}>
            Add note
          </Button>
        </div>
      </fieldset>

      {!readOnly && (
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save eligibility rule'}
          </Button>
          {initial && (
            <Button type="button" variant="outline" disabled={saving} onClick={() => setConfirmRemove(true)}>
              Remove rule
            </Button>
          )}
        </div>
      )}
      {confirmRemove && (
        <ConfirmPanel
          title="Remove eligibility rule"
          message="Students will no longer see automatic eligibility criteria for this job."
          confirmLabel="Confirm remove"
          destructive
          busy={saving}
          onConfirm={() => {
            setConfirmRemove(false);
            onRemove();
          }}
          onCancel={() => setConfirmRemove(false)}
        />
      )}
    </form>
  );
}
