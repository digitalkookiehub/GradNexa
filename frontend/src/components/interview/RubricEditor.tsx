import { FormField } from '@/components/auth/FormField';
import { TagInput } from '@/components/student/TagInput';
import { Button } from '@/components/ui/button';
import type { RubricDraft } from '@/lib/interview';

interface RubricEditorProps {
  value: RubricDraft[];
  onChange: (next: RubricDraft[]) => void;
  disabled?: boolean;
}

export function RubricEditor({ value, onChange, disabled = false }: RubricEditorProps) {
  const update = (i: number, patch: Partial<RubricDraft>): void => {
    onChange(value.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  };

  return (
    <fieldset className="space-y-3">
      <legend className="text-sm font-medium">Rubric concepts</legend>
      {value.map((r, i) => (
        <div key={i} className="space-y-3 rounded-md border p-3" role="group" aria-label={`Concept ${i + 1}`}>
          <FormField
            id={`concept-${i}`}
            label={`Concept ${i + 1} name`}
            value={r.concept}
            onChange={(e) => update(i, { concept: e.target.value })}
            disabled={disabled}
          />
          <TagInput id={`keywords-${i}`} label={`Concept ${i + 1} keywords`} tags={r.keywords} onChange={(keywords) => update(i, { keywords })} disabled={disabled} />
          <FormField
            id={`weight-${i}`}
            label={`Concept ${i + 1} weight`}
            type="number"
            min={0}
            step="any"
            value={r.weight}
            onChange={(e) => update(i, { weight: e.target.value })}
            disabled={disabled}
          />
          <Button type="button" variant="outline" size="sm" onClick={() => onChange(value.filter((_, idx) => idx !== i))} disabled={disabled}>
            Remove concept {i + 1}
          </Button>
        </div>
      ))}
      <Button type="button" variant="secondary" size="sm" onClick={() => onChange([...value, { concept: '', keywords: [], weight: '1' }])} disabled={disabled}>
        Add concept
      </Button>
    </fieldset>
  );
}
