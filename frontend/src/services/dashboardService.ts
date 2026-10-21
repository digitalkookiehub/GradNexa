import api from './api';
import { num, numOrNull } from './assessmentService';
import type {
  DashboardGap,
  DashboardReadiness,
  PlacementDashboard,
  StudentDashboard,
} from '@/types/dashboard';

function normaliseReadiness<T extends DashboardReadiness>(raw: T): T {
  return {
    ...raw,
    overall: numOrNull(raw.overall),
    level: raw.level ?? null,
    coverage: num(raw.coverage),
    rule_version: num(raw.rule_version, 1),
  };
}

function normaliseGap(raw: DashboardGap): DashboardGap {
  return { ...raw, current: numOrNull(raw.current), required: num(raw.required), gap: numOrNull(raw.gap), recommended_action: raw.recommended_action ?? '' };
}

export function normaliseStudentDashboard(raw: StudentDashboard): StudentDashboard {
  return {
    ...raw,
    profile: {
      profile_complete: raw.profile?.profile_complete === true,
      department_name: raw.profile?.department_name ?? null,
      roll_number: raw.profile?.roll_number ?? null,
    },
    rule_active: raw.rule_active === true,
    readiness: {
      general: raw.readiness?.general ? normaliseReadiness(raw.readiness.general) : null,
      roles: (raw.readiness?.roles ?? []).map(normaliseReadiness),
    },
    skills: (raw.skills ?? []).map((s) => ({ ...s, score: num(s.score), evidence_count: num(s.evidence_count) })),
    top_gaps: (raw.top_gaps ?? []).map(normaliseGap),
    goals: raw.goals ?? [],
    plan: raw.plan
      ? {
          ...raw.plan,
          starts_on: raw.plan.starts_on ?? null,
          progress: {
            done: num(raw.plan.progress?.done),
            total: num(raw.plan.progress?.total),
            percent: num(raw.plan.progress?.percent),
          },
        }
      : null,
    recent_assessments: (raw.recent_assessments ?? []).map((a) => ({ ...a, percentage: num(a.percentage) })),
    not_implemented: raw.not_implemented ?? [],
    resume: raw.resume
      ? {
          ...raw.resume,
          analyzed_at: raw.resume.analyzed_at ?? null,
          role_name: raw.resume.role_name ?? null,
          role_match_percent: numOrNull(raw.resume.role_match_percent),
        }
      : null,
    interview: raw.interview
      ? {
          completed_count: num(raw.interview.completed_count),
          latest: raw.interview.latest ? { ...raw.interview.latest, overall: numOrNull(raw.interview.latest.overall) } : null,
        }
      : null,
  };
}

export function normalisePlacementDashboard(raw: PlacementDashboard): PlacementDashboard {
  return {
    ...raw,
    scope: { department_id: raw.scope?.department_id ?? null, department_name: raw.scope?.department_name ?? null },
    rule: raw.rule ?? null,
    rule_versions_in_use: (raw.rule_versions_in_use ?? []).map((v) => num(v)),
    totals: {
      students: num(raw.totals?.students),
      profile_complete: num(raw.totals?.profile_complete),
      with_readiness_score: num(raw.totals?.with_readiness_score),
      with_assessment_submitted: num(raw.totals?.with_assessment_submitted),
    },
    level_distribution: (raw.level_distribution ?? []).map((l) => ({ level: l.level ?? null, count: num(l.count) })),
    departments: (raw.departments ?? []).map((d) => ({
      ...d,
      department_id: d.department_id ?? null,
      students: num(d.students),
      scored: num(d.scored),
      avg_overall: numOrNull(d.avg_overall),
      avg_coverage: numOrNull(d.avg_coverage),
    })),
    top_gaps: (raw.top_gaps ?? []).map((g) => ({ ...g, students_affected: num(g.students_affected), high_priority_students: num(g.high_priority_students) })),
    assessment_participation: {
      published_assessments: num(raw.assessment_participation?.published_assessments),
      students_with_attempts: num(raw.assessment_participation?.students_with_attempts),
      submitted_attempts: num(raw.assessment_participation?.submitted_attempts),
    },
  };
}

export const dashboardService = {
  async getStudent(): Promise<StudentDashboard> {
    const { data } = await api.get<StudentDashboard>('/dashboard/student');
    return normaliseStudentDashboard(data);
  },

  async getPlacement(departmentId?: number | null): Promise<PlacementDashboard> {
    const params = departmentId === null || departmentId === undefined ? {} : { department_id: departmentId };
    const { data } = await api.get<PlacementDashboard>('/dashboard/placement', { params });
    return normalisePlacementDashboard(data);
  },
};
