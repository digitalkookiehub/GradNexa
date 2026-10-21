export interface FacultyTotals {
  assigned_students: number;
  with_readiness_score: number;
  needing_support: number;
}

export interface FacultyStudentRow {
  student_id: number;
  name: string;
  email: string;
  department_name: string | null;
  roll_number: string | null;
  overall: number | null;
  level: string | null;
  coverage: number | null;
  high_priority_gap_count: number;
  last_assessment_percentage: number | null;
  last_assessment_at: string | null;
  needs_support: boolean;
  support_reasons: string[];
}

export interface FacultyTopGap {
  skill_id: number;
  skill_name: string;
  students_affected: number;
  high_priority_students: number;
}

export interface FacultyAssessmentPerformance {
  assessment_id: number;
  title: string;
  attempts_submitted: number;
  average_percentage: number | null;
}

export interface FacultyDashboard {
  generated_at: string;
  totals: FacultyTotals;
  students: FacultyStudentRow[];
  top_gaps: FacultyTopGap[];
  assessment_performance: FacultyAssessmentPerformance[];
}
