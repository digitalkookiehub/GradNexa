export interface HodScope {
  department_ids: number[];
  department_names: string[];
}

export interface HodTotals {
  students: number;
  profile_complete: number;
  with_readiness_score: number;
  with_assessment_submitted: number;
}

export interface HodLevelCount {
  level: string | null;
  count: number;
}

export interface HodHeatmapCell {
  skill_id: number;
  skill_name: string;
  category_name: string;
  students_assessed: number;
  average_score: number | null;
}

export interface HodRoleCount {
  role_id: number;
  role_name: string;
  students: number;
}

export interface HodAssessmentTrend {
  month: string;
  submitted_attempts: number;
  average_percentage: number | null;
}

export interface HodTrainingPriority {
  skill_id: number;
  skill_name: string;
  students_affected: number;
  high_priority_students: number;
}

export interface HodDashboard {
  generated_at: string;
  scope: HodScope;
  rule: { id: number; version: number } | null;
  rule_versions_in_use: number[];
  totals: HodTotals;
  level_distribution: HodLevelCount[];
  skill_heatmap: HodHeatmapCell[];
  career_role_distribution: HodRoleCount[];
  assessment_trends: HodAssessmentTrend[];
  training_priorities: HodTrainingPriority[];
}
