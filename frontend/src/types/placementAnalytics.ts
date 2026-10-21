export interface RoleReadinessRow {
  role_id: number;
  role_name: string;
  students_with_goal: number;
  students_scored: number;
  average_overall: number | null;
  average_coverage: number | null;
}

export interface CompanyEligibilityRow {
  job_id: number;
  job_title: string;
  company_name: string;
  eligible: number;
  not_eligible: number;
  incomplete_data: number;
  no_rule_students: number;
}

export interface ProgressTrendRow {
  month: string;
  students_scored: number;
  average_overall: number | null;
}

export interface PlacementAnalytics {
  generated_at: string;
  scope: { department_id: number | null; department_name: string | null };
  role_readiness: RoleReadinessRow[];
  company_eligibility: CompanyEligibilityRow[];
  progress_trends: ProgressTrendRow[];
}
