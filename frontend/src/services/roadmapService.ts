import api from './api';
import { getErrorStatus } from '@/lib/errors';
import { num, numOrNull } from './assessmentService';
import { normaliseReadiness, normaliseRole, normaliseRoleDetail } from './readinessService';
import type {
  CareerGoal,
  CareerGoalInput,
  ExplorerRole,
  GeneratePlanInput,
  LearningResource,
  MyReadinessSummary,
  Plan,
  PlanHistoryEntry,
  PlanItem,
  PlanItemStatus,
  PlanProgress,
  ReassessResult,
  RoleDetailView,
  SkillChange,
} from '@/types';

function normaliseProgress(raw: PlanProgress | null | undefined): PlanProgress {
  return { done: num(raw?.done), total: num(raw?.total), percent: num(raw?.percent) };
}

export function normaliseItem(raw: PlanItem): PlanItem {
  return {
    ...raw,
    week: num(raw.week, 1),
    position: num(raw.position),
    skill_id: raw.skill_id ?? null,
    skill_name: raw.skill_name ?? null,
    resource: raw.resource ?? null,
    completed_at: raw.completed_at ?? null,
  };
}

export function normalisePlan(raw: Plan): Plan {
  return {
    ...raw,
    duration_days: num(raw.duration_days, 30),
    skills_per_week: num(raw.skills_per_week, 2),
    baseline: raw.baseline
      ? { ...raw.baseline, readiness_score_id: raw.baseline.readiness_score_id ?? null, overall: numOrNull(raw.baseline.overall), level: raw.baseline.level ?? null, rule_version: num(raw.baseline.rule_version, 1) }
      : null,
    weeks: (raw.weeks ?? []).map((w) => ({ week: num(w.week, 1), items: (w.items ?? []).map(normaliseItem) })),
    unscheduled_skills: (raw.unscheduled_skills ?? []).map((s) => ({ ...s, gap: numOrNull(s.gap) })),
    progress: normaliseProgress(raw.progress),
  };
}

function normaliseSummary(raw: MyReadinessSummary): MyReadinessSummary {
  return { ...raw, overall: numOrNull(raw.overall), level: raw.level ?? null, coverage: num(raw.coverage), rule_version: num(raw.rule_version, 1) };
}

function normaliseChange(raw: SkillChange): SkillChange {
  return { ...raw, before: numOrNull(raw.before), after: numOrNull(raw.after), delta: numOrNull(raw.delta) };
}

export const roadmapService = {
  async listRoles(): Promise<ExplorerRole[]> {
    const { data } = await api.get<ExplorerRole[]>('/career-roles');
    return data.map((r) => ({ ...normaliseRole(r), is_goal: r.is_goal === true }));
  },

  async getRole(id: number): Promise<RoleDetailView> {
    const { data } = await api.get<RoleDetailView>(`/career-roles/${id}`);
    return {
      ...normaliseRoleDetail(data),
      is_goal: data.is_goal === true,
      my_readiness: data.my_readiness ? normaliseSummary(data.my_readiness) : null,
    };
  },

  async getGoals(): Promise<CareerGoal[]> {
    const { data } = await api.get<CareerGoal[]>('/students/me/career-goals');
    return data.map((g) => ({ ...g, priority: num(g.priority) })).sort((a, b) => a.priority - b.priority);
  },

  async saveGoals(goals: CareerGoalInput[]): Promise<void> {
    await api.put('/students/me/career-goals', goals);
  },

  async listResources(skillId?: number): Promise<LearningResource[]> {
    const { data } = await api.get<LearningResource[]>('/learning-resources', {
      params: skillId === undefined ? {} : { skill_id: skillId },
    });
    return data;
  },

  async generatePlan(input: GeneratePlanInput): Promise<Plan> {
    const { data } = await api.post<Plan>('/plans/generate', input);
    return normalisePlan(data);
  },

  /** Resolves to null when the student has no active plan (404). */
  async getActivePlan(): Promise<Plan | null> {
    try {
      const { data } = await api.get<Plan>('/plans/me');
      return normalisePlan(data);
    } catch (err) {
      if (getErrorStatus(err) === 404) return null;
      throw err;
    }
  },

  async history(): Promise<PlanHistoryEntry[]> {
    const { data } = await api.get<PlanHistoryEntry[]>('/plans/me/history');
    return data.map((p) => ({ ...p, progress: normaliseProgress(p.progress) }));
  },

  async updateItem(id: number, status: PlanItemStatus): Promise<PlanItem> {
    const { data } = await api.patch<PlanItem>(`/plans/items/${id}`, { status });
    return normaliseItem(data);
  },

  async reassess(): Promise<ReassessResult> {
    const { data } = await api.post<ReassessResult>('/plans/me/reassess');
    return {
      ...data,
      baseline: { ...data.baseline, overall: numOrNull(data.baseline.overall), level: data.baseline.level ?? null, rule_version: num(data.baseline.rule_version, 1) },
      current: normaliseReadiness(data.current),
      overall_delta: numOrNull(data.overall_delta),
      rule_version_changed: data.rule_version_changed === true,
      skill_changes: (data.skill_changes ?? []).map(normaliseChange),
    };
  },
};
