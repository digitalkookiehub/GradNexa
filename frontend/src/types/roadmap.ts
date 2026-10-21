import type { CareerRole, CareerRoleDetail, ReadinessResult } from './readiness';

export interface ExplorerRole extends CareerRole {
  is_goal: boolean;
}

export interface MyReadinessSummary {
  overall: number | null;
  level: string | null;
  coverage: number;
  rule_version: number;
  computed_at: string;
}

export interface RoleDetailView extends CareerRoleDetail {
  is_goal: boolean;
  my_readiness: MyReadinessSummary | null;
}

export interface CareerGoal {
  career_role_id: number;
  role_name: string;
  priority: number;
}

export interface CareerGoalInput {
  career_role_id: number;
  priority: number;
}

export interface LearningResource {
  id: number;
  skill_id: number;
  skill_name: string;
  title: string;
  url: string;
  description: string | null;
}

export interface AdminLearningResource extends LearningResource {
  is_approved: boolean;
  approved_by: number | null;
  approved_at: string | null;
  created_by: number | null;
}

export interface LearningResourceInput {
  skill_id: number;
  title: string;
  url: string;
  description?: string | null;
}

export type PlanStatus = 'ACTIVE' | 'COMPLETED' | 'ARCHIVED';
export type PlanItemKind = 'LEARN' | 'PRACTICE' | 'ASSESS' | 'REASSESS';
export type PlanItemStatus = 'TODO' | 'IN_PROGRESS' | 'DONE';

export interface PlanProgress {
  done: number;
  total: number;
  percent: number;
}

export interface PlanBaseline {
  readiness_score_id: number | null;
  overall: number | null;
  level: string | null;
  rule_version: number;
  computed_at: string;
}

export interface PlanItemResource {
  id: number;
  title: string;
  url: string;
}

export interface PlanItem {
  id: number;
  week: number;
  position: number;
  kind: PlanItemKind;
  skill_id: number | null;
  skill_name: string | null;
  resource: PlanItemResource | null;
  task: string;
  status: PlanItemStatus;
  completed_at: string | null;
}

export interface PlanWeek {
  week: number;
  items: PlanItem[];
}

export interface UnscheduledSkill {
  skill_id: number;
  skill_name: string;
  gap: number | null;
}

export interface Plan {
  id: number;
  role_id: number;
  role_name: string;
  status: PlanStatus;
  starts_on: string;
  duration_days: number;
  skills_per_week: number;
  baseline: PlanBaseline | null;
  weeks: PlanWeek[];
  unscheduled_skills: UnscheduledSkill[];
  progress: PlanProgress;
}

export interface PlanHistoryEntry {
  id: number;
  role_id: number;
  role_name: string;
  status: PlanStatus;
  starts_on: string;
  progress: PlanProgress;
}

export interface GeneratePlanInput {
  role_id: number;
  skills_per_week?: number;
}

export interface ReassessBaseline {
  overall: number | null;
  level: string | null;
  rule_version: number;
}

export interface SkillChange {
  skill_id: number;
  skill_name: string;
  before: number | null;
  after: number | null;
  delta: number | null;
}

export interface ReassessResult {
  plan_id: number;
  baseline: ReassessBaseline;
  current: ReadinessResult;
  overall_delta: number | null;
  rule_version_changed: boolean;
  skill_changes: SkillChange[];
}
