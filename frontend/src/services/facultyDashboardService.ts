import api from './api';
import { num, numOrNull } from './assessmentService';
import type { FacultyDashboard } from '@/types';

export function normaliseFacultyDashboard(raw: FacultyDashboard): FacultyDashboard {
  return {
    generated_at: raw.generated_at,
    totals: {
      assigned_students: num(raw.totals?.assigned_students),
      with_readiness_score: num(raw.totals?.with_readiness_score),
      needing_support: num(raw.totals?.needing_support),
    },
    students: (raw.students ?? []).map((s) => ({
      ...s,
      department_name: s.department_name ?? null,
      roll_number: s.roll_number ?? null,
      overall: numOrNull(s.overall),
      level: s.level ?? null,
      coverage: numOrNull(s.coverage),
      high_priority_gap_count: num(s.high_priority_gap_count),
      last_assessment_percentage: numOrNull(s.last_assessment_percentage),
      last_assessment_at: s.last_assessment_at ?? null,
      needs_support: s.needs_support === true,
      support_reasons: s.support_reasons ?? [],
    })),
    top_gaps: (raw.top_gaps ?? []).map((g) => ({
      ...g,
      students_affected: num(g.students_affected),
      high_priority_students: num(g.high_priority_students),
    })),
    assessment_performance: (raw.assessment_performance ?? []).map((a) => ({
      ...a,
      attempts_submitted: num(a.attempts_submitted),
      average_percentage: numOrNull(a.average_percentage),
    })),
  };
}

export const facultyDashboardService = {
  async get(): Promise<FacultyDashboard> {
    const { data } = await api.get<FacultyDashboard>('/dashboard/faculty');
    return normaliseFacultyDashboard(data);
  },
};
