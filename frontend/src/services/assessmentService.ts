import api from './api';
import type {
  AnswerMap,
  AssessmentResult,
  AssessmentSummary,
  Attempt,
  AttemptQuestion,
  HistoryEntry,
  Skill,
  SkillCategory,
  SkillScore,
  StudentAssessment,
  StudentSkill,
} from '@/types/assessment';

type NumericLike = number | string | null | undefined;

export function num(value: NumericLike, fallback = 0): number {
  if (value === null || value === undefined || value === '') return fallback;
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function numOrNull(value: NumericLike): number | null {
  if (value === null || value === undefined || value === '') return null;
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export function normaliseSummary<T extends AssessmentSummary>(raw: T): T {
  return {
    ...raw,
    version: num(raw.version, 1),
    time_limit_min: numOrNull(raw.time_limit_min),
    max_attempts: numOrNull(raw.max_attempts),
    question_count: num(raw.question_count),
    total_marks: num(raw.total_marks),
  };
}

function normaliseSkillScore(raw: SkillScore): SkillScore {
  return { ...raw, score: num(raw.score), max: num(raw.max), percentage: num(raw.percentage) };
}

export function normaliseResult<T extends AssessmentResult>(raw: T): T {
  return {
    ...raw,
    assessment_version: num(raw.assessment_version, 1),
    total_score: num(raw.total_score),
    max_score: num(raw.max_score),
    percentage: num(raw.percentage),
    per_skill_scores: (raw.per_skill_scores ?? []).map(normaliseSkillScore),
  };
}

function normaliseAttempt(raw: Attempt): Attempt {
  const questions: AttemptQuestion[] = (raw.questions ?? [])
    .map((q) => ({ ...q, marks: num(q.marks), position: num(q.position), multi_select: Boolean(q.multi_select) }))
    .sort((a, b) => a.position - b.position);
  return { ...raw, questions, answers: raw.answers ?? {} };
}

export const assessmentService = {
  async list(): Promise<StudentAssessment[]> {
    const { data } = await api.get<StudentAssessment[]>('/assessments');
    return data.map((a) => ({
      ...normaliseSummary(a),
      attempts_used: num(a.attempts_used),
      in_progress_attempt_id: a.in_progress_attempt_id ?? null,
    }));
  },

  async get(id: number): Promise<AssessmentSummary> {
    const { data } = await api.get<AssessmentSummary>(`/assessments/${id}`);
    return normaliseSummary(data);
  },

  async startAttempt(assessmentId: number): Promise<Attempt> {
    const { data } = await api.post<Attempt>(`/assessments/${assessmentId}/attempts`);
    return normaliseAttempt(data);
  },

  async saveAnswers(attemptId: number, answers: AnswerMap): Promise<number> {
    const { data } = await api.put<{ saved: number }>(`/attempts/${attemptId}/answers`, { answers });
    return num(data.saved);
  },

  async submit(attemptId: number): Promise<AssessmentResult> {
    const { data } = await api.post<AssessmentResult>(`/attempts/${attemptId}/submit`);
    return normaliseResult(data);
  },

  async getResult(attemptId: number): Promise<AssessmentResult> {
    const { data } = await api.get<AssessmentResult>(`/attempts/${attemptId}/result`);
    return normaliseResult(data);
  },

  async history(): Promise<HistoryEntry[]> {
    const { data } = await api.get<HistoryEntry[]>('/assessments/history');
    return data.map((h) => ({ ...normaliseResult(h), attempt_no: num(h.attempt_no, 1) }));
  },

  async mySkills(): Promise<StudentSkill[]> {
    const { data } = await api.get<StudentSkill[]>('/students/me/skills');
    return data.map((s) => ({
      ...s,
      score: num(s.score),
      evidence_count: num(s.evidence_count),
      confidence: numOrNull(s.confidence),
    }));
  },

  async listSkills(): Promise<Skill[]> {
    const { data } = await api.get<Skill[]>('/skills');
    return data;
  },

  async listSkillCategories(): Promise<SkillCategory[]> {
    const { data } = await api.get<SkillCategory[]>('/skill-categories');
    return data;
  },
};
