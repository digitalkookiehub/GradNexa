import { useState, type FormEvent } from 'react';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { FormField, FormMessage } from '@/components/auth/FormField';
import { RubricEditor } from '@/components/interview/RubricEditor';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { fromRubric, toRubric, validateRubric, type RubricDraft } from '@/lib/interview';
import type { BankQuestion, BankQuestionInput, CareerRole, Skill } from '@/types';

interface BankQuestionFormProps {
  initial: BankQuestion | null;
  roles: CareerRole[];
  skills: Skill[];
  busy: boolean;
  error: string | null;
  onSubmit: (payload: BankQuestionInput) => void;
  onCancel: () => void;
}

export function BankQuestionForm({ initial, roles, skills, busy, error, onSubmit, onCancel }: BankQuestionFormProps) {
  const [competency, setCompetency] = useState(initial?.competency ?? '');
  const [prompt, setPrompt] = useState(initial?.prompt ?? '');
  const [minWords, setMinWords] = useState(String(initial?.min_words ?? 30));
  const [roleId, setRoleId] = useState(initial?.role_id ? String(initial.role_id) : '');
  const [skillId, setSkillId] = useState(initial?.skill_id ? String(initial.skill_id) : '');
  const [rubric, setRubric] = useState<RubricDraft[]>(initial ? fromRubric(initial.rubric) : [{ concept: '', keywords: [], weight: '1' }]);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = (e: FormEvent): void => {
    e.preventDefault();
    if (!competency.trim()) return setFormError('Competency is required.');
    if (!prompt.trim()) return setFormError('Prompt is required.');
    const mw = Number(minWords);
    if (!Number.isInteger(mw) || mw < 0) return setFormError('Minimum words must be a whole number, 0 or more.');
    const rubricError = validateRubric(rubric);
    if (rubricError) return setFormError(rubricError);
    setFormError(null);
    onSubmit({
      role_id: roleId ? Number(roleId) : null,
      skill_id: skillId ? Number(skillId) : null,
      competency: competency.trim(),
      prompt: prompt.trim(),
      rubric: toRubric(rubric),
      min_words: mw,
    });
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit} noValidate aria-label={initial ? 'Edit interview question' : 'New interview question'}>
      <FormField id="iq-competency" label="Competency" value={competency} onChange={(e) => setCompetency(e.target.value)} disabled={busy} />
      <div className="space-y-2">
        <Label htmlFor="iq-prompt">Prompt</Label>
        <textarea
          id="iq-prompt"
          rows={3}
          className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={busy}
        />
      </div>
      <FormField id="iq-min-words" label="Minimum words" type="number" min={0} value={minWords} onChange={(e) => setMinWords(e.target.value)} disabled={busy} />
      <div className="space-y-2">
        <Label htmlFor="iq-role">Role (optional)</Label>
        <select id="iq-role" className={SELECT_CLASS} value={roleId} onChange={(e) => setRoleId(e.target.value)} disabled={busy}>
          <option value="">Any role</option>
          {roles.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="iq-skill">Skill (optional)</Label>
        <select id="iq-skill" className={SELECT_CLASS} value={skillId} onChange={(e) => setSkillId(e.target.value)} disabled={busy}>
          <option value="">No skill</option>
          {skills.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>
      <RubricEditor value={rubric} onChange={setRubric} disabled={busy} />
      <FormMessage message={formError ?? error} />
      <div className="flex gap-2">
        <Button type="submit" disabled={busy}>
          {busy ? 'Saving...' : initial ? 'Save changes' : 'Create question'}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
