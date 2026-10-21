import type { Extracted } from '@/types/resume';

/** Mirrors the server default upload limit (MAX_UPLOAD_MB=10); the server remains authoritative. */
export const MAX_RESUME_BYTES = 10 * 1024 * 1024;
export const MAX_JD_CHARS = 20000;

const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];
const ALLOWED_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

/** Returns an error message, or null when the file looks acceptable. */
export function validateResumeFile(file: File): string | null {
  const name = file.name.toLowerCase();
  const extOk = ALLOWED_EXTENSIONS.some((e) => name.endsWith(e));
  const typeOk = file.type === '' || ALLOWED_TYPES.includes(file.type);
  if (!extOk || !typeOk) return 'Only PDF or DOCX files are supported.';
  if (file.size === 0) return 'This file is empty.';
  if (file.size > MAX_RESUME_BYTES) return `This file is larger than the ${formatBytes(MAX_RESUME_BYTES)} limit.`;
  return null;
}

export function formatBytes(n: number): string {
  if (n >= 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  if (n >= 1024) return `${Math.round(n / 1024)} KB`;
  return `${n} B`;
}

export function uploadErrorMessage(status: number | null, serverMessage: string): string {
  if (status === 413) return `File too large. ${serverMessage}`;
  if (status === 415) return `Unsupported file type. ${serverMessage}`;
  if (status === 422) return `This file could not be read (it may be corrupt or password-protected). ${serverMessage}`;
  return serverMessage;
}

export interface HighlightRange {
  start: number;
  end: number;
  group: string;
}

export interface Segment {
  text: string;
  start: number;
  groups: string[];
}

/**
 * Splits text into contiguous segments. Ranges are CODE POINT indices into the
 * exact text (the backend is Python, which indexes by code point, not by UTF-16
 * unit); invalid (non-integer, negative, empty, out-of-range) ranges are dropped,
 * and overlaps produce segments that carry every covering group.
 */
export function buildSegments(text: string, ranges: HighlightRange[]): Segment[] {
  const chars = Array.from(text);
  const valid = ranges.filter(
    (r) => Number.isInteger(r.start) && Number.isInteger(r.end) && r.start >= 0 && r.end <= chars.length && r.end > r.start,
  );
  const points = new Set<number>([0, chars.length]);
  valid.forEach((r) => {
    points.add(r.start);
    points.add(r.end);
  });
  const sorted = [...points].sort((a, b) => a - b);
  const segments: Segment[] = [];
  for (let i = 0; i < sorted.length - 1; i += 1) {
    const start = sorted[i];
    const end = sorted[i + 1];
    if (end <= start) continue;
    const groups = [...new Set(valid.filter((r) => r.start <= start && r.end >= end).map((r) => r.group))];
    segments.push({ text: chars.slice(start, end).join(''), start, groups });
  }
  return segments;
}

export const skillGroup = (skillId: number): string => `skill:${skillId}`;
export const blockGroup = (kind: string, index: number): string => `${kind}:${index}`;

export function rangesFromExtracted(extracted: Extracted): HighlightRange[] {
  const ranges: HighlightRange[] = [];
  extracted.skills.forEach((s) => s.spans.forEach((sp) => ranges.push({ start: sp.start, end: sp.end, group: skillGroup(s.skill_id) })));
  (['education', 'projects', 'experience', 'certifications'] as const).forEach((kind) =>
    extracted[kind].forEach((b, i) => ranges.push({ start: b.span.start, end: b.span.end, group: blockGroup(kind, i) })),
  );
  return ranges;
}

export function formatMatch(p: number | null): string {
  return p === null ? 'Not enough data' : `${Math.round(p * 10) / 10}%`;
}
