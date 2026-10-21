import type { CgpaBasis, EligibilityRuleInput, EligibilityRuleOut } from '@/types/jobAdmin';

export const CGPA_BASIS_OPTIONS: { value: CgpaBasis; label: string; help: string }[] = [
  {
    value: 'LATEST_SEMESTER',
    label: 'Latest semester',
    help: "Uses the CGPA from the student's most recent semester record.",
  },
  {
    value: 'AVERAGE_ALL_SEMESTERS',
    label: 'Average of all semesters',
    help: "Uses the average CGPA across all of the student's recorded semesters.",
  },
];

export const MAX_NOTES = 20;
export const MAX_NOTE_LENGTH = 500;
export const MIN_YEAR = 1990;
export const MAX_YEAR = 2100;

export interface EligibilityFormState {
  cgpaOn: boolean;
  cgpaMin: string;
  cgpaBasis: CgpaBasis | '';
  arrearsOn: boolean;
  maxArrears: string;
  attendanceOn: boolean;
  attendanceMin: string;
  departmentIds: number[];
  yearsOn: boolean;
  years: string;
  notes: string[];
}

export type EligibilityErrors = Partial<Record<'cgpaMin' | 'cgpaBasis' | 'maxArrears' | 'attendanceMin' | 'years' | 'notes', string>>;

export const EMPTY_ELIGIBILITY_FORM: EligibilityFormState = {
  cgpaOn: false,
  cgpaMin: '',
  cgpaBasis: '',
  arrearsOn: false,
  maxArrears: '',
  attendanceOn: false,
  attendanceMin: '',
  departmentIds: [],
  yearsOn: false,
  years: '',
  notes: [],
};

export function formFromRule(rule: EligibilityRuleOut | null): EligibilityFormState {
  if (!rule) return { ...EMPTY_ELIGIBILITY_FORM };
  return {
    cgpaOn: rule.cgpa_min !== null,
    cgpaMin: rule.cgpa_min !== null ? String(rule.cgpa_min) : '',
    cgpaBasis: rule.cgpa_basis ?? '',
    arrearsOn: rule.max_arrears !== null,
    maxArrears: rule.max_arrears !== null ? String(rule.max_arrears) : '',
    attendanceOn: rule.attendance_min !== null,
    attendanceMin: rule.attendance_min !== null ? String(rule.attendance_min) : '',
    departmentIds: rule.department_ids ? rule.department_ids.map((d) => d.id) : [],
    yearsOn: rule.graduation_years !== null,
    years: rule.graduation_years ? rule.graduation_years.join(', ') : '',
    notes: [...rule.custom_notes],
  };
}

function parseNumber(text: string): number {
  return text.trim() === '' ? NaN : Number(text);
}

/** Parses "2026, 2027" into integers. Returns null when empty or any entry is not a valid year. */
export function parseYears(text: string): number[] | null {
  const parts = text
    .split(',')
    .map((p) => p.trim())
    .filter((p) => p !== '');
  if (parts.length === 0) return null;
  const years: number[] = [];
  for (const p of parts) {
    if (!/^\d{4}$/.test(p)) return null;
    const y = Number(p);
    if (y < MIN_YEAR || y > MAX_YEAR) return null;
    if (!years.includes(y)) years.push(y);
  }
  return years.sort((a, b) => a - b);
}

export interface BuildResult {
  errors: EligibilityErrors;
  payload: EligibilityRuleInput | null;
}

/** Mirrors the server rules. Criteria that are switched off are omitted from the payload (never sent as zeros). */
export function buildEligibilityPayload(form: EligibilityFormState): BuildResult {
  const errors: EligibilityErrors = {};
  const payload: EligibilityRuleInput = {};

  if (form.cgpaOn) {
    const v = parseNumber(form.cgpaMin);
    if (!Number.isFinite(v) || v < 0 || v > 10) errors.cgpaMin = 'Minimum CGPA must be a number between 0 and 10.';
    else payload.cgpa_min = v;
    if (form.cgpaBasis === '') errors.cgpaBasis = 'Choose which CGPA the minimum is checked against.';
    else payload.cgpa_basis = form.cgpaBasis;
  }
  if (form.arrearsOn) {
    const v = parseNumber(form.maxArrears);
    if (!Number.isInteger(v) || v < 0) errors.maxArrears = 'Maximum arrears must be a whole number, 0 or more.';
    else payload.max_arrears = v;
  }
  if (form.attendanceOn) {
    const v = parseNumber(form.attendanceMin);
    if (!Number.isFinite(v) || v < 0 || v > 100) errors.attendanceMin = 'Minimum attendance must be a number between 0 and 100.';
    else payload.attendance_min = v;
  }
  if (form.departmentIds.length > 0) payload.department_ids = [...form.departmentIds];
  if (form.yearsOn) {
    const years = parseYears(form.years);
    if (years === null) errors.years = `Enter one or more graduation years (${MIN_YEAR}-${MAX_YEAR}) separated by commas.`;
    else payload.graduation_years = years;
  }
  if (form.notes.length > 0) {
    const trimmed = form.notes.map((n) => n.trim());
    if (trimmed.some((n) => n === '')) errors.notes = 'Custom notes cannot be blank. Remove empty notes.';
    else if (trimmed.some((n) => n.length > MAX_NOTE_LENGTH)) errors.notes = `Each note must be ${MAX_NOTE_LENGTH} characters or fewer.`;
    else if (trimmed.length > MAX_NOTES) errors.notes = `At most ${MAX_NOTES} custom notes are allowed.`;
    else payload.custom_notes = trimmed;
  }

  if (Object.keys(errors).length > 0) return { errors, payload: null };
  return { errors, payload };
}

export function basisLabel(basis: CgpaBasis): string {
  return CGPA_BASIS_OPTIONS.find((o) => o.value === basis)?.label ?? basis;
}

/** Plain-language lines describing a rule the way students will see it. */
export function describeRule(rule: EligibilityRuleOut): { checked: string[]; notes: string[] } {
  const checked: string[] = [];
  if (rule.cgpa_min !== null) {
    checked.push(`Minimum CGPA ${rule.cgpa_min}${rule.cgpa_basis ? ` (${basisLabel(rule.cgpa_basis).toLowerCase()})` : ''}`);
  }
  if (rule.max_arrears !== null) checked.push(`At most ${rule.max_arrears} arrears`);
  if (rule.attendance_min !== null) checked.push(`Minimum attendance ${rule.attendance_min}%`);
  checked.push(rule.department_ids ? `Departments: ${rule.department_ids.map((d) => d.name).join(', ')}` : 'Departments: all departments');
  if (rule.graduation_years) checked.push(`Graduation years: ${rule.graduation_years.join(', ')}`);
  return { checked, notes: rule.custom_notes };
}

export function isValidHttpUrl(value: string): boolean {
  try {
    const u = new URL(value);
    return (u.protocol === 'http:' || u.protocol === 'https:') && u.hostname.length > 0;
  } catch {
    return false;
  }
}

const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

/**
 * The backend stores the application deadline as a calendar DATE (no time), so the
 * form works with plain YYYY-MM-DD strings end to end (no timezone conversion).
 * Accepts a date or date-time string and returns the date part for an <input type="date">.
 */
export function isoToLocalInput(iso: string | null): string {
  if (!iso) return '';
  const datePart = iso.slice(0, 10);
  return DATE_ONLY.test(datePart) ? datePart : '';
}

/** <input type="date"> value -> API value (YYYY-MM-DD), or null when empty/invalid. */
export function localInputToIso(value: string): string | null {
  if (!value || !DATE_ONLY.test(value)) return null;
  const d = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== value ? null : value;
}

export function formatDeadline(iso: string | null): string {
  const date = isoToLocalInput(iso);
  if (!date) return 'No deadline';
  return new Date(`${date}T00:00:00Z`).toLocaleDateString(undefined, { timeZone: 'UTC' });
}
