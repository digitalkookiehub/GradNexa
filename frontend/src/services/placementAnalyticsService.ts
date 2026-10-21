import api from './api';
import { num, numOrNull } from './assessmentService';
import type { PlacementAnalytics } from '@/types';

export function normalisePlacementAnalytics(raw: PlacementAnalytics): PlacementAnalytics {
  return {
    generated_at: raw.generated_at,
    scope: { department_id: raw.scope?.department_id ?? null, department_name: raw.scope?.department_name ?? null },
    role_readiness: (raw.role_readiness ?? []).map((r) => ({
      ...r,
      students_with_goal: num(r.students_with_goal),
      students_scored: num(r.students_scored),
      average_overall: numOrNull(r.average_overall),
      average_coverage: numOrNull(r.average_coverage),
    })),
    company_eligibility: (raw.company_eligibility ?? []).map((c) => ({
      ...c,
      eligible: num(c.eligible),
      not_eligible: num(c.not_eligible),
      incomplete_data: num(c.incomplete_data),
      no_rule_students: num(c.no_rule_students),
    })),
    progress_trends: (raw.progress_trends ?? []).map((t) => ({
      ...t,
      students_scored: num(t.students_scored),
      average_overall: numOrNull(t.average_overall),
    })),
  };
}

export const placementAnalyticsService = {
  async get(departmentId?: number | null): Promise<PlacementAnalytics> {
    const params = departmentId === null || departmentId === undefined ? {} : { department_id: departmentId };
    const { data } = await api.get<PlacementAnalytics>('/dashboard/placement/analytics', { params });
    return normalisePlacementAnalytics(data);
  },
};
