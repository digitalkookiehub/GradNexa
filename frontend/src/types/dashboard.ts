import type { DashboardInterview, DashboardResume } from './interview';
import type { GapPriority, GapStatus } from './readiness';

export interface DashboardProfile {
  profile_complete: boolean;
  department_name: string | null;
  roll_number: string | null;
}

export interface DashboardReadiness {
  overall: number | null;
  level: string | null;
  coverage: number;
  rule_version: number;
  computed_at: string;
}

export interface DashboardRoleReadiness extends DashboardReadiness {
  role_id: number;
  role_name: string;
}

export interface DashboardSkill {
  skill_id: number;
  skill_name: string;
  category_name: string;
  score: number;
  evidence_count: number;
}

export interface DashboardGap {
  role_id: number;
  role_name: string;
  skill_id: number;
  skill_name: string;
  current: number | null;
  required: number;
  gap: number | null;
  status: GapStatus;
  priority: GapPriority;
  recommended_action: string;
}

export interface DashboardGoal {
  career_role_id: number;
  role_name: string;
  priority: number;
}

export interface DashboardPlan {
  id: number;
  role_id: number;
  role_name: string;
  status: string;
  starts_on: string | null;
  progress: { done: number; total: number; percent: number };
}

export interface DashboardAssessment {
  attempt_id: number;
  assessment_title: string;
  percentage: number;
  submitted_at: string;
}

export interface StudentDashboard {
  profile: DashboardProfile;
  rule_active: boolean;
  readiness: { general: DashboardReadiness | null; roles: DashboardRoleReadiness[] };
  skills: DashboardSkill[];
  top_gaps: DashboardGap[];
  goals: DashboardGoal[];
  plan: DashboardPlan | null;
  recent_assessments: DashboardAssessment[];
  not_implemented: string[];
  resume?: DashboardResume | null;
  interview?: DashboardInterview | null;
}

export interface PlacementTotals {
  students: number;
  profile_complete: number;
  with_readiness_score: number;
  with_assessment_submitted: number;
}

export interface PlacementLevelCount {
  level: string | null;
  count: number;
}

export interface PlacementDepartment {
  department_id: number | null;
  department_name: string;
  students: number;
  scored: number;
  avg_overall: number | null;
  avg_coverage: number | null;
}

export interface PlacementGap {
  skill_id: number;
  skill_name: string;
  students_affected: number;
  high_priority_students: number;
}

export interface PlacementDashboard {
  generated_at: string;
  scope: { department_id: number | null; department_name: string | null };
  rule: { id: number; version: number } | null;
  rule_versions_in_use: number[];
  totals: PlacementTotals;
  level_distribution: PlacementLevelCount[];
  departments: PlacementDepartment[];
  top_gaps: PlacementGap[];
  assessment_participation: { published_assessments: number; students_with_attempts: number; submitted_attempts: number };
}
