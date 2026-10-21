import api from './api';
import { num, numOrNull } from './assessmentService';
import type { CareerRole, CareerRoleDetail, Gap, ReadinessResult } from '@/types/readiness';

export function normaliseGap(raw: Gap): Gap {
  return { ...raw, current: numOrNull(raw.current), required: num(raw.required), gap: numOrNull(raw.gap), recommended_action: raw.recommended_action ?? '' };
}

export function normaliseReadiness(raw: ReadinessResult): ReadinessResult {
  return {
    ...raw,
    role_id: raw.role_id ?? null,
    role_name: raw.role_name ?? null,
    rule_version: num(raw.rule_version, 1),
    overall: numOrNull(raw.overall),
    level: raw.level ?? null,
    coverage: num(raw.coverage),
    category_scores: (raw.category_scores ?? []).map((c) => ({
      ...c,
      weight: num(c.weight),
      score: numOrNull(c.score),
      evidence_count: num(c.evidence_count),
    })),
    evidence: (raw.evidence ?? []).map((e) => ({
      ...e,
      score: num(e.score),
      evidence_count: num(e.evidence_count),
      last_result_id: e.last_result_id ?? null,
    })),
    gaps: (raw.gaps ?? []).map(normaliseGap),
  };
}

export function normaliseRole<T extends CareerRole>(raw: T): T {
  return { ...raw, description: raw.description ?? null, department_id: raw.department_id ?? null, is_active: raw.is_active !== false };
}

export function normaliseRoleDetail(raw: CareerRoleDetail): CareerRoleDetail {
  return {
    ...normaliseRole(raw),
    skills: (raw.skills ?? []).map((s) => ({ ...s, required_level: num(s.required_level), weight: num(s.weight) })),
  };
}

function roleParams(roleId: number | null | undefined): { role_id?: number } {
  return roleId === null || roleId === undefined ? {} : { role_id: roleId };
}

export const readinessService = {
  async compute(roleId?: number | null): Promise<ReadinessResult> {
    const { data } = await api.post<ReadinessResult>('/readiness/compute', roleParams(roleId));
    return normaliseReadiness(data);
  },

  async getLatest(roleId?: number | null): Promise<ReadinessResult> {
    const { data } = await api.get<ReadinessResult>('/readiness/me', { params: roleParams(roleId) });
    return normaliseReadiness(data);
  },

  async history(roleId?: number | null): Promise<ReadinessResult[]> {
    const { data } = await api.get<ReadinessResult[]>('/readiness/me/history', { params: roleParams(roleId) });
    return data.map(normaliseReadiness);
  },

  async gaps(roleId: number): Promise<Gap[]> {
    const { data } = await api.get<Gap[]>('/readiness/gaps', { params: { role_id: roleId } });
    return data.map(normaliseGap);
  },

  async listRoles(): Promise<CareerRole[]> {
    const { data } = await api.get<CareerRole[]>('/career-roles');
    return data.map(normaliseRole);
  },

  async getRole(id: number): Promise<CareerRoleDetail> {
    const { data } = await api.get<CareerRoleDetail>(`/career-roles/${id}`);
    return normaliseRoleDetail(data);
  },
};
