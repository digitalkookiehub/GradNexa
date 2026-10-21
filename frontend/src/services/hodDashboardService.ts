import api from './api';
import { num, numOrNull } from './assessmentService';
import type { HodDashboard } from '@/types';

export function normaliseHodDashboard(raw: HodDashboard): HodDashboard {
  return {
    generated_at: raw.generated_at,
    scope: {
      department_ids: (raw.scope?.department_ids ?? []).map((v) => num(v)),
      department_names: raw.scope?.department_names ?? [],
    },
    rule: raw.rule ?? null,
    rule_versions_in_use: (raw.rule_versions_in_use ?? []).map((v) => num(v)),
    totals: {
      students: num(raw.totals?.students),
      profile_complete: num(raw.totals?.profile_complete),
      with_readiness_score: num(raw.totals?.with_readiness_score),
      with_assessment_submitted: num(raw.totals?.with_assessment_submitted),
    },
    level_distribution: (raw.level_distribution ?? []).map((l) => ({ level: l.level ?? null, count: num(l.count) })),
    skill_heatmap: (raw.skill_heatmap ?? []).map((c) => ({
      ...c,
      category_name: c.category_name ?? '',
      students_assessed: num(c.students_assessed),
      average_score: numOrNull(c.average_score),
    })),
    career_role_distribution: (raw.career_role_distribution ?? []).map((r) => ({ ...r, students: num(r.students) })),
    assessment_trends: (raw.assessment_trends ?? []).map((t) => ({
      ...t,
      submitted_attempts: num(t.submitted_attempts),
      average_percentage: numOrNull(t.average_percentage),
    })),
    training_priorities: (raw.training_priorities ?? []).map((g) => ({
      ...g,
      students_affected: num(g.students_affected),
      high_priority_students: num(g.high_priority_students),
    })),
  };
}

export const hodDashboardService = {
  async get(departmentId?: number | null): Promise<HodDashboard> {
    const params = departmentId === null || departmentId === undefined ? {} : { department_id: departmentId };
    const { data } = await api.get<HodDashboard>('/dashboard/hod', { params });
    return normaliseHodDashboard(data);
  },
};
