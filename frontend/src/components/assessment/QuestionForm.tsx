import { useState, type FormEvent } from 'react';
import { FieldError } from '@/components/auth/FieldError';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { validateQuestionForm, type QuestionFormErrors } from '@/lib/assessment';
import { DIFFICULTIES, type AdminQuestion, type Difficulty, type Option, type QuestionInput, type Skill } from '@/types';

interface QuestionFormProps {
  skills: Skill[];
  initial?: AdminQuestion;
  submitting: boolean;
  onSubmit: (payload: QuestionInput) => void;
  onCancel: () => void;
}

const SELECT_CLASS =
  'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

function nextOptionId(options: Option[]): string {
  const used = new Set(options.map((o) => o.id));
  for (let i = 0; i < 26; i += 1) {
    const id = String.fromCharCode(97 + i);
    if (!used.has(id)) return id;
  }
  return `o${options.length + 1}`;
}

export function QuestionForm({ skills, initial, submitting, onSubmit, onCancel }: QuestionFormProps) {
  const [body, setBody] = useState(initial?.body ?? '');
  const [skillId, setSkillId] = useState(initial ? String(initial.skill_id) : '');
  const [difficulty, setDifficulty] = useState<Difficulty>(initial?.difficulty ?? 'MEDIUM');
  const [marks, setMarks] = useState(initial ? String(initial.marks) : '1');
  const [options, setOptions] = useState<Option[]>(
    initial && initial.options.length > 0
      ? initial.options
      : [
          { id: 'a', text: '' },
          { id: 'b', text: '' },
        ],
  );
  const [correctIds, setCorrectIds] = useState<string[]>(initial?.correct_option_ids ?? []);
  const [errors, setErrors] = useState<QuestionFormErrors>({});

  const setOptionText = (id: string, text: string): void => {
    setOptions((prev) => prev.map((o) => (o.id === id ? { ...o, text } : o)));
  };

  const addOption = (): void => {
    setOptions((prev) => [...prev, { id: nextOptionId(prev), text: '' }]);
  };

  const removeOption = (id: string): void => {
    setOptions((prev) => prev.filter((o) => o.id !== id));
    setCorrectIds((prev) => prev.filter((c) => c !== id));
  };

  const toggleCorrect = (id: string): void => {
    setCorrectIds((prev) => (prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]));
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    const found = validateQuestionForm({ body, skillId, marks, options, correctIds });
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    const filled = options.filter((o) => o.text.trim() !== '').map((o) => ({ id: o.id, text: o.text.trim() }));
    const ids = new Set(filled.map((o) => o.id));
    onSubmit({
      skill_id: Number(skillId),
      difficulty,
      body: body.trim(),
      options: filled,
      correct_option_ids: correctIds.filter((c) => ids.has(c)),
      marks: Number(marks),
    });
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4 rounded-md border p-4" aria-label="Question form">
      <div className="space-y-2">
        <Label htmlFor="q-body">Question</Label>
        <textarea
          id="q-body"
          className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          aria-invalid={Boolean(errors.body)}
          aria-describedby={errors.body ? 'q-body-error' : undefined}
        />
        <FieldError id="q-body-error" message={errors.body} />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="q-skill">Skill</Label>
          <select id="q-skill" className={SELECT_CLASS} value={skillId} onChange={(e) => setSkillId(e.target.value)}>
            <option value="">Select skill</option>
            {skills.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <FieldError id="q-skill-error" message={errors.skill} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="q-difficulty">Difficulty</Label>
          <select id="q-difficulty" className={SELECT_CLASS} value={difficulty} onChange={(e) => setDifficulty(e.target.value as Difficulty)}>
            {DIFFICULTIES.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="q-marks">Marks</Label>
          <Input id="q-marks" inputMode="decimal" value={marks} onChange={(e) => setMarks(e.target.value)} />
          <FieldError id="q-marks-error" message={errors.marks} />
        </div>
      </div>
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Options (tick the correct answer or answers)</legend>
        {options.map((o, i) => (
          <div key={o.id} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={correctIds.includes(o.id)}
              onChange={() => toggleCorrect(o.id)}
              aria-label={`Option ${i + 1} is correct`}
            />
            <Input value={o.text} onChange={(e) => setOptionText(o.id, e.target.value)} aria-label={`Option ${i + 1} text`} />
            <Button type="button" variant="ghost" size="sm" onClick={() => removeOption(o.id)} disabled={options.length <= 2} aria-label={`Remove option ${i + 1}`}>
              Remove
            </Button>
          </div>
        ))}
        <Button type="button" variant="outline" size="sm" onClick={addOption} disabled={options.length >= 10}>
          Add option
        </Button>
        <FieldError id="q-options-error" message={errors.options} />
        <FieldError id="q-correct-error" message={errors.correct} />
      </fieldset>
      <div className="flex gap-2">
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving...' : initial ? 'Save question' : 'Add question'}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
