import api from './api';
import { num } from './assessmentService';
import { normaliseRole, normaliseRoleDetail } from './readinessService';
import type {
  CareerRole,
  CareerRoleDetail,
  CareerRoleInput,
  ReadinessRule,
  ReadinessRuleInput,
  RoleSkillInput,
} from '@/types/readiness';

function normaliseRule(raw: ReadinessRule): ReadinessRule {
  const weights: Record<string, number> = {};
  for (const [k, v] of Object.entries(raw.weights ?? {})) weights[k] = num(v);
  return {
    ...raw,
    version: num(raw.version, 1),
    weights,
    level_thresholds: (raw.level_thresholds ?? []).map((t) => ({ level: t.level, min_score: num(t.min_score) })),
    gap_thresholds: {
      high_min_gap: num(raw.gap_thresholds?.high_min_gap),
      medium_min_gap: num(raw.gap_thresholds?.medium_min_gap),
    },
  };
}

export const adminReadinessService = {
  async listRules(): Promise<ReadinessRule[]> {
    const { data } = await api.get<ReadinessRule[]>('/admin/readiness-rules');
    return data.map(normaliseRule);
  },

  async createRule(payload: ReadinessRuleInput): Promise<ReadinessRule> {
    const { data } = await api.post<ReadinessRule>('/admin/readiness-rules', payload);
    return normaliseRule(data);
  },

  async activateRule(id: number): Promise<ReadinessRule> {
    const { data } = await api.post<ReadinessRule>(`/admin/readiness-rules/${id}/activate`);
    return normaliseRule(data);
  },

  async listRoles(): Promise<CareerRole[]> {
    const { data } = await api.get<CareerRole[]>('/admin/career-roles');
    return data.map(normaliseRole);
  },

  async getRole(id: number): Promise<CareerRoleDetail> {
    const { data } = await api.get<CareerRoleDetail>(`/admin/career-roles/${id}`);
    return normaliseRoleDetail(data);
  },

  async createRole(payload: CareerRoleInput): Promise<CareerRole> {
    const { data } = await api.post<CareerRole>('/admin/career-roles', payload);
    return normaliseRole(data);
  },

  async updateRole(id: number, payload: CareerRoleInput): Promise<CareerRole> {
    const { data } = await api.put<CareerRole>(`/admin/career-roles/${id}`, payload);
    return normaliseRole(data);
  },

  async setRoleSkills(id: number, skills: RoleSkillInput[]): Promise<CareerRoleDetail> {
    const { data } = await api.put<CareerRoleDetail>(`/admin/career-roles/${id}/skills`, skills);
    return normaliseRoleDetail(data);
  },
};
