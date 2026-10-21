import type { RubricConcept } from '@/types/interview';

export const DEFAULT_DISCLAIMER =
  'Scores show keyword-rubric coverage of your written answers only. They do not measure communication, confidence or personality, and do not predict hiring outcomes.';

export const SHORT_DISCLAIMER = 'Keyword-rubric coverage only; not a prediction of hiring outcomes.';

export function countWords(text: string): number {
  const t = text.trim();
  return t === '' ? 0 : t.split(/\s+/).length;
}

export interface RubricDraft {
  concept: string;
  keywords: string[];
  weight: string;
}

export function validateRubric(rubric: RubricDraft[]): string | null {
  if (rubric.length === 0) return 'Add at least one rubric concept.';
  for (let i = 0; i < rubric.length; i += 1) {
    const r = rubric[i];
    const n = i + 1;
    if (!r.concept.trim()) return `Concept ${n} needs a name.`;
    if (r.keywords.length === 0) return `Concept ${n} needs at least one keyword.`;
    const w = Number(r.weight);
    if (r.weight.trim() === '' || !Number.isFinite(w) || w <= 0) return `Concept ${n} needs a weight greater than 0.`;
  }
  return null;
}

export function toRubric(drafts: RubricDraft[]): RubricConcept[] {
  return drafts.map((d) => ({ concept: d.concept.trim(), keywords: d.keywords, weight: Number(d.weight) }));
}

export function fromRubric(rubric: RubricConcept[]): RubricDraft[] {
  return rubric.map((r) => ({ concept: r.concept, keywords: r.keywords, weight: String(r.weight) }));
}
