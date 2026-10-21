import { useState, type FormEvent } from 'react';
import { FieldError } from '@/components/auth/FieldError';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { validateRule, type RuleFormErrors, type RuleFormValues } from '@/lib/readiness';
import type { ReadinessRule, ReadinessRuleInput, SkillCategory } from '@/types';

interface RuleFormProps {
  categories: SkillCategory[];
  /** Existing rule to prefill from (rules are immutable, so this always creates a new version). */
  prefill: ReadinessRule | null;
  saving: boolean;
  onSubmit: (payload: ReadinessRuleInput) => void;
  onCancel: () => void;
}

function valuesFromRule(rule: ReadinessRule | null): RuleFormValues {
  if (!rule) return { weights: {}, levels: [{ level: '', min_score: '0' }], highGap: '', mediumGap: '' };
  const weights: Record<string, string> = {};
  for (const [k, v] of Object.entries(rule.weights)) weights[k] = String(v);
  return {
    weights,
    levels: rule.level_thresholds.map((t) => ({ level: t.level, min_score: String(t.min_score) })),
    highGap: String(rule.gap_thresholds.high_min_gap),
    mediumGap: String(rule.gap_thresholds.medium_min_gap),
  };
}

export function RuleForm({ categories, prefill, saving, onSubmit, onCancel }: RuleFormProps) {
  const [values, setValues] = useState<RuleFormValues>(() => valuesFromRule(prefill));
  const [errors, setErrors] = useState<RuleFormErrors>({});

  const setWeight = (categoryId: number, value: string): void =>
    setValues((v) => ({ ...v, weights: { ...v.weights, [String(categoryId)]: value } }));

  const setLevel = (index: number, patch: Partial<{ level: string; min_score: string }>): void =>
    setValues((v) => ({ ...v, levels: v.levels.map((row, i) => (i === index ? { ...row, ...patch } : row)) }));

  const handleSubmit = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    const result = validateRule(values, categories);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    setErrors({});
    onSubmit(result.payload);
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6" aria-label="New readiness rule version">
      <fieldset className="space-y-3">
        <legend className="font-medium">Category weights</legend>
        <p className="text-sm text-muted-foreground">Leave a category blank to exclude it. Weights are relative to each other.</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {categories.map((c) => (
            <div key={c.id} className="space-y-1">
              <Label htmlFor={`weight-${c.id}`}>{c.name}</Label>
              <Input
                id={`weight-${c.id}`}
                type="number"
                min={0}
                step="any"
                value={values.weights[String(c.id)] ?? ''}
                onChange={(e) => setWeight(c.id, e.target.value)}
              />
            </div>
          ))}
        </div>
        {categories.length === 0 && <p className="text-sm text-muted-foreground">No skill categories exist yet.</p>}
        <FieldError id="weights-error" message={errors.weights} />
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="font-medium">Level thresholds</legend>
        <p className="text-sm text-muted-foreground">Each level applies from its minimum score. One level must start at 0.</p>
        {values.levels.map((row, i) => (
          <div key={i} className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <Label htmlFor={`level-name-${i}`}>Level name {i + 1}</Label>
              <Input id={`level-name-${i}`} value={row.level} onChange={(e) => setLevel(i, { level: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label htmlFor={`level-min-${i}`}>Minimum score {i + 1}</Label>
              <Input
                id={`level-min-${i}`}
                type="number"
                min={0}
                max={100}
                step="any"
                value={row.min_score}
                onChange={(e) => setLevel(i, { min_score: e.target.value })}
              />
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setValues((v) => ({ ...v, levels: v.levels.filter((_, idx) => idx !== i) }))}
              aria-label={`Remove level ${i + 1}`}
            >
              Remove
            </Button>
          </div>
        ))}
        <Button type="button" variant="outline" size="sm" onClick={() => setValues((v) => ({ ...v, levels: [...v.levels, { level: '', min_score: '' }] }))}>
          Add level
        </Button>
        <FieldError id="levels-error" message={errors.levels} />
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="font-medium">Gap thresholds</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1">
            <Label htmlFor="gap-high">High priority at gap of at least</Label>
            <Input id="gap-high" type="number" min={0} step="any" value={values.highGap} onChange={(e) => setValues((v) => ({ ...v, highGap: e.target.value }))} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="gap-medium">Medium priority at gap of at least</Label>
            <Input id="gap-medium" type="number" min={0} step="any" value={values.mediumGap} onChange={(e) => setValues((v) => ({ ...v, mediumGap: e.target.value }))} />
          </div>
        </div>
        <FieldError id="gaps-error" message={errors.gaps} />
      </fieldset>

      <div className="flex gap-2">
        <Button type="submit" disabled={saving}>
          {saving ? 'Saving...' : 'Create version'}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
