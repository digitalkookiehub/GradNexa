import { formatBytes } from '@/lib/resume';
import type { KnowledgeSourceType, KnowledgeStatus } from '@/types/knowledge';

/** Mirrors the server default upload limit (MAX_UPLOAD_MB=10); the server remains authoritative. */
export const MAX_KNOWLEDGE_BYTES = 10 * 1024 * 1024;
export const QUERY_MAX = 1000;

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md'];
const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
  'text/x-markdown',
];

export const SOURCE_TYPES: { value: KnowledgeSourceType; label: string }[] = [
  { value: 'SYLLABUS', label: 'Syllabus' },
  { value: 'CURRICULUM', label: 'Curriculum' },
  { value: 'LEARNING_MATERIAL', label: 'Learning material' },
  { value: 'PLACEMENT_GUIDE', label: 'Placement guide' },
  { value: 'INTERVIEW_GUIDE', label: 'Interview guide' },
  { value: 'POLICY', label: 'Policy' },
  { value: 'OTHER', label: 'Other' },
];

export function sourceTypeLabel(value: string): string {
  return SOURCE_TYPES.find((s) => s.value === value)?.label ?? value;
}

export const STATUS_LABELS: Record<KnowledgeStatus, string> = {
  PENDING: 'Pending approval',
  APPROVED: 'Approved',
  ARCHIVED: 'Archived',
};

export const STATUS_CLASSES: Record<KnowledgeStatus, string> = {
  PENDING: 'bg-amber-100 text-amber-800',
  APPROVED: 'bg-green-100 text-green-800',
  ARCHIVED: 'bg-muted text-muted-foreground',
};

/** Returns an error message, or null when the file looks acceptable. */
export function validateKnowledgeFile(file: File): string | null {
  const name = file.name.toLowerCase();
  const extOk = ALLOWED_EXTENSIONS.some((e) => name.endsWith(e));
  const typeOk = file.type === '' || ALLOWED_TYPES.includes(file.type);
  if (!extOk || !typeOk) return 'Only PDF, DOCX, TXT or MD files are supported.';
  if (file.size === 0) return 'This file is empty.';
  if (file.size > MAX_KNOWLEDGE_BYTES) return `This file is larger than the ${formatBytes(MAX_KNOWLEDGE_BYTES)} limit.`;
  return null;
}

export function knowledgeUploadError(status: number | null, serverMessage: string): string {
  if (status === 413) return `File too large. ${serverMessage}`;
  if (status === 415) return `Unsupported file type. ${serverMessage}`;
  if (status === 422) return `This file could not be used. ${serverMessage}`;
  return serverMessage;
}

export const ASSISTANT_EXAMPLES: string[] = [
  'What is my readiness for my goal role?',
  'Which skills am I missing for this role?',
  'Am I eligible for this job?',
  'What should I study next?',
];

export const NO_LLM_NOTE =
  'Answers are assembled from your own records and from documents your college has approved, using fixed rules. No AI language model is used yet.';
