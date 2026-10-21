export const NOT_IMPLEMENTED_LABELS: Record<string, string> = {
  resume_score: 'Resume score',
  resume: 'Resume score',
  interview_progress: 'Interview progress',
  interview: 'Interview progress',
  mock_interview: 'Interview progress',
};

export function notImplementedLabel(key: string): string {
  const known = NOT_IMPLEMENTED_LABELS[key];
  if (known) return known;
  const text = key.replace(/[_-]+/g, ' ').trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : key;
}

export function formatDash(value: number | null): string {
  return value === null ? '-' : String(Math.round(value * 10) / 10);
}
