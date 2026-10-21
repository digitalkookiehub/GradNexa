import api from './api';
import { num, numOrNull } from './assessmentService';
import type {
  Interview,
  InterviewAnswerInput,
  InterviewQuestion,
  InterviewResult,
  InterviewSummary,
} from '@/types/interview';

function normaliseQuestion(raw: InterviewQuestion): InterviewQuestion {
  return {
    ...raw,
    position: num(raw.position),
    min_words: num(raw.min_words),
    answer_text: raw.answer_text ?? null,
  };
}

export function normaliseInterview(raw: Interview): Interview {
  return {
    ...raw,
    completed_at: raw.completed_at ?? null,
    questions: (raw.questions ?? []).map(normaliseQuestion).sort((a, b) => a.position - b.position),
  };
}

export function normaliseInterviewSummary(raw: InterviewSummary): InterviewSummary {
  return { ...raw, completed_at: raw.completed_at ?? null, overall: numOrNull(raw.overall) };
}

export function normaliseInterviewResult(raw: InterviewResult): InterviewResult {
  return {
    ...raw,
    overall: numOrNull(raw.overall),
    competency_scores: (raw.competency_scores ?? []).map((c) => ({
      ...c,
      score: num(c.score),
      max: num(c.max, 100),
      questions: num(c.questions),
    })),
    per_question: (raw.per_question ?? []).map((q) => ({
      ...q,
      position: num(q.position),
      score: num(q.score),
      answered: q.answered === true,
      too_short: q.too_short === true,
      covered_concepts: q.covered_concepts ?? [],
      missed_concepts: q.missed_concepts ?? [],
    })),
    disclaimer: raw.disclaimer ?? '',
  };
}

export const interviewService = {
  async start(roleId: number, questionCount?: number): Promise<Interview> {
    const body = questionCount === undefined ? { role_id: roleId } : { role_id: roleId, question_count: questionCount };
    const { data } = await api.post<Interview>('/interviews', body);
    return normaliseInterview(data);
  },

  async get(id: number): Promise<Interview> {
    const { data } = await api.get<Interview>(`/interviews/${id}`);
    return normaliseInterview(data);
  },

  async saveAnswers(id: number, answers: InterviewAnswerInput[]): Promise<void> {
    await api.put(`/interviews/${id}/answers`, { answers });
  },

  async finish(id: number): Promise<InterviewResult> {
    const { data } = await api.post<InterviewResult>(`/interviews/${id}/finish`);
    return normaliseInterviewResult(data);
  },

  async getResult(id: number): Promise<InterviewResult> {
    const { data } = await api.get<InterviewResult>(`/interviews/${id}/result`);
    return normaliseInterviewResult(data);
  },

  async list(): Promise<InterviewSummary[]> {
    const { data } = await api.get<InterviewSummary[]>('/interviews');
    return (data ?? []).map(normaliseInterviewSummary);
  },
};
