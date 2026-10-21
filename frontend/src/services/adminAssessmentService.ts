import api from './api';
import { normaliseSummary, num } from './assessmentService';
import type {
  AdminAssessmentDetail,
  AdminQuestion,
  AssessmentFilters,
  AssessmentInput,
  AssessmentSummary,
  QuestionBankFilters,
  QuestionInput,
  Skill,
  SkillCategory,
  SkillCategoryInput,
  SkillInput,
} from '@/types/assessment';

function normaliseQuestion(q: AdminQuestion): AdminQuestion {
  return { ...q, marks: num(q.marks), position: num(q.position), correct_option_ids: q.correct_option_ids ?? [] };
}

export const adminAssessmentService = {
  async list(filters: AssessmentFilters = {}): Promise<AssessmentSummary[]> {
    const { data } = await api.get<AssessmentSummary[]>('/admin/assessments', { params: filters });
    return data.map(normaliseSummary);
  },

  async get(id: number): Promise<AdminAssessmentDetail> {
    const { data } = await api.get<AdminAssessmentDetail>(`/admin/assessments/${id}`);
    return { ...normaliseSummary(data), questions: (data.questions ?? []).map(normaliseQuestion) };
  },

  async create(payload: AssessmentInput): Promise<AssessmentSummary> {
    const { data } = await api.post<AssessmentSummary>('/admin/assessments', payload);
    return normaliseSummary(data);
  },

  async update(id: number, payload: AssessmentInput): Promise<AssessmentSummary> {
    const { data } = await api.put<AssessmentSummary>(`/admin/assessments/${id}`, payload);
    return normaliseSummary(data);
  },

  async remove(id: number): Promise<void> {
    await api.delete(`/admin/assessments/${id}`);
  },

  async publish(id: number): Promise<AssessmentSummary> {
    const { data } = await api.post<AssessmentSummary>(`/admin/assessments/${id}/publish`);
    return normaliseSummary(data);
  },

  async archive(id: number): Promise<AssessmentSummary> {
    const { data } = await api.post<AssessmentSummary>(`/admin/assessments/${id}/archive`);
    return normaliseSummary(data);
  },

  async newVersion(id: number): Promise<AssessmentSummary> {
    const { data } = await api.post<AssessmentSummary>(`/admin/assessments/${id}/new-version`);
    return normaliseSummary(data);
  },

  async listQuestionBank(filters: QuestionBankFilters = {}): Promise<AdminQuestion[]> {
    const { data } = await api.get<AdminQuestion[]>('/admin/question-bank', { params: filters });
    return data.map(normaliseQuestion);
  },

  async addQuestion(assessmentId: number, payload: QuestionInput): Promise<AdminQuestion> {
    const { data } = await api.post<AdminQuestion>(`/admin/assessments/${assessmentId}/questions`, payload);
    return normaliseQuestion(data);
  },

  async updateQuestion(questionId: number, payload: QuestionInput): Promise<AdminQuestion> {
    const { data } = await api.put<AdminQuestion>(`/admin/question-bank/${questionId}`, payload);
    return normaliseQuestion(data);
  },

  async deleteQuestion(questionId: number): Promise<void> {
    await api.delete(`/admin/question-bank/${questionId}`);
  },

  async createCategory(payload: SkillCategoryInput): Promise<SkillCategory> {
    const { data } = await api.post<SkillCategory>('/admin/skill-categories', payload);
    return data;
  },

  async updateCategory(id: number, payload: SkillCategoryInput): Promise<SkillCategory> {
    const { data } = await api.put<SkillCategory>(`/admin/skill-categories/${id}`, payload);
    return data;
  },

  async createSkill(payload: SkillInput): Promise<Skill> {
    const { data } = await api.post<Skill>('/admin/skills', payload);
    return data;
  },

  async updateSkill(id: number, payload: SkillInput): Promise<Skill> {
    const { data } = await api.put<Skill>(`/admin/skills/${id}`, payload);
    return data;
  },
};
