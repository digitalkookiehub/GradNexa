import api from './api';
import { num } from './assessmentService';
import type { BankQuestion, BankQuestionFilter, BankQuestionInput } from '@/types/interview';

export function normaliseBankQuestion(raw: BankQuestion): BankQuestion {
  return {
    ...raw,
    role_id: raw.role_id ?? null,
    role_name: raw.role_name ?? null,
    skill_id: raw.skill_id ?? null,
    min_words: num(raw.min_words),
    is_active: raw.is_active !== false,
    created_by: raw.created_by ?? null,
    rubric: (raw.rubric ?? []).map((r) => ({ concept: r.concept, keywords: r.keywords ?? [], weight: num(r.weight, 1) })),
  };
}

export const adminInterviewService = {
  async list(filter: BankQuestionFilter = {}): Promise<BankQuestion[]> {
    const params: { role_id?: number; active?: boolean } = {};
    if (filter.role_id !== null && filter.role_id !== undefined) params.role_id = filter.role_id;
    if (filter.active !== null && filter.active !== undefined) params.active = filter.active;
    const { data } = await api.get<BankQuestion[]>('/admin/interview-questions', { params });
    return (data ?? []).map(normaliseBankQuestion);
  },

  async create(payload: BankQuestionInput): Promise<BankQuestion> {
    const { data } = await api.post<BankQuestion>('/admin/interview-questions', payload);
    return normaliseBankQuestion(data);
  },

  async update(id: number, payload: BankQuestionInput): Promise<BankQuestion> {
    const { data } = await api.put<BankQuestion>(`/admin/interview-questions/${id}`, payload);
    return normaliseBankQuestion(data);
  },

  async deactivate(id: number): Promise<void> {
    await api.delete(`/admin/interview-questions/${id}`);
  },
};
