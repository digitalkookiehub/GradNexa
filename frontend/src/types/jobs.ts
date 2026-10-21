import type { Gap } from './readiness';

export type EligibilityStatus = 'ELIGIBLE' | 'NOT_ELIGIBLE' | 'INCOMPLETE_DATA' | 'NO_RULE';
export type CriterionResult = 'MET' | 'NOT_MET' | 'UNKNOWN';
export type CriterionKey = 'cgpa' | 'arrears' | 'attendance' | 'department' | 'graduation_year';
export type CgpaBasis = 'LATEST_SEMESTER' | 'AVERAGE_ALL_SEMESTERS';

export interface JobListItem {
  id: number;
  company_id: number;
  company_name: string;
  title: string;
  role_id: number | null;
  role_name: string | null;
  status: string;
  application_deadline: string | null;
  deadline_passed: boolean;
  has_eligibility_rule: boolean;
  eligibility_status: EligibilityStatus;
}

export interface JobCompany {
  id: number;
  name: string;
  description: string | null;
  website: string | null;
}

export interface JobSkill {
  skill_id: number;
  skill_name: string;
  required_level: number;
  weight: number;
}

export interface DepartmentRef {
  id: number;
  name: string;
}

export interface EligibilityRule {
  cgpa_min: number | null;
  cgpa_basis: CgpaBasis | null;
  max_arrears: number | null;
  attendance_min: number | null;
  department_ids: DepartmentRef[] | null;
  graduation_years: number[] | null;
  custom_notes: string[];
}

export interface JobDetail {
  id: number;
  company: JobCompany;
  title: string;
  body: string;
  role_id: number | null;
  role_name: string | null;
  status: string;
  application_deadline: string | null;
  deadline_passed: boolean;
  skills: JobSkill[];
  eligibility_criteria: EligibilityRule | null;
}

export interface EligibilityCriterion {
  key: CriterionKey;
  label: string;
  required: string;
  actual: string | null;
  result: CriterionResult;
}

export interface EligibilityCheck {
  job_id: number;
  status: EligibilityStatus;
  criteria: EligibilityCriterion[];
  custom_notes: string[];
  note: string;
  evaluated_at: string;
}

export interface JobSkillFit {
  job_id: number;
  rule_id: number | null;
  rule_version: number;
  overall: number | null;
  coverage: number;
  gaps: Gap[];
}
