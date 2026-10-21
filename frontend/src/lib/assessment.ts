import type { AssessmentStatus, AssessmentType, Option } from '@/types/assessment';

export const TYPE_LABELS: Record<AssessmentType, string> = {
  APTITUDE: 'Aptitude',
  TECHNICAL: 'Technical',
  COMMUNICATION: 'Communication',
  ROLE_SPECIFIC: 'Role specific',
  DEPARTMENT_SPECIFIC: 'Department specific',
  CUSTOM: 'Custom',
};

export const STATUS_LABELS: Record<AssessmentStatus, string> = {
  DRAFT: 'Draft',
  PUBLISHED: 'Published',
  ARCHIVED: 'Archived',
};

export function formatClock(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const mm = String(m).padStart(2, '0');
  const ss = String(sec).padStart(2, '0');
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** Seconds remaining until expiresAt (ISO string); null when there is no limit. */
export function secondsRemaining(expiresAt: string | null, nowMs: number): number | null {
  if (!expiresAt) return null;
  const t = Date.parse(expiresAt);
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.ceil((t - nowMs) / 1000));
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 10) / 10}%`;
}

export interface QuestionFormValues {
  body: string;
  skillId: string;
  marks: string;
  options: Option[];
  correctIds: string[];
}

export type QuestionFormErrors = Partial<Record<'body' | 'skill' | 'marks' | 'options' | 'correct', string>>;

export function validateQuestionForm(values: QuestionFormValues): QuestionFormErrors {
  const errors: QuestionFormErrors = {};
  if (!values.body.trim()) errors.body = 'Question text is required.';
  if (!values.skillId) errors.skill = 'Select a skill.';
  const marks = Number(values.marks);
  if (values.marks.trim() === '' || !Number.isFinite(marks) || marks <= 0) errors.marks = 'Marks must be a positive number.';
  const filled = values.options.filter((o) => o.text.trim() !== '');
  if (filled.length < 2) {
    errors.options = 'Provide at least 2 options with text.';
  }
  const filledIds = new Set(filled.map((o) => o.id));
  const validCorrect = values.correctIds.filter((id) => filledIds.has(id));
  if (validCorrect.length < 1) errors.correct = 'Mark at least 1 correct option.';
  return errors;
}

export interface NegativeMarkingResult {
  value: number | null;
  error?: string;
}

/** Parses the negative-marking field: empty means 0; otherwise a fraction from 0 to 1 (e.g. 0.25). */
export function parseNegativeMarking(raw: string): NegativeMarkingResult {
  const text = raw.trim();
  if (text === '') return { value: 0 };
  const n = Number(text);
  if (!Number.isFinite(n) || n < 0 || n > 1) {
    return { value: null, error: 'Negative marking must be a number from 0 to 1 (for example 0.25).' };
  }
  return { value: n };
}
