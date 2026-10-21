export type JobStatus = 'DRAFT' | 'OPEN' | 'CLOSED';
export type CgpaBasis = 'LATEST_SEMESTER' | 'AVERAGE_ALL_SEMESTERS';

export interface AdminCompany {
  id: number;
  name: string;
  description: string | null;
  website: string | null;
  is_active: boolean;
  job_count: number;
}

export interface CompanyInput {
  name?: string;
  description?: string | null;
  website?: string | null;
  is_active?: boolean;
}

export interface AdminJobSummary {
  id: number;
  company_id: number;
  company_name: string;
  title: string;
  role_id: number | null;
  role_name: string | null;
  status: JobStatus;
  application_deadline: string | null;
  has_eligibility_rule: boolean;
}

export interface JobSkillOut {
  skill_id: number;
  skill_name: string;
  required_level: number;
  weight: number;
}

export interface JobSkillInput {
  skill_id: number;
  required_level: number;
  weight: number;
}

export interface DepartmentRef {
  id: number;
  name: string;
}

export interface EligibilityRuleOut {
  cgpa_min: number | null;
  cgpa_basis: CgpaBasis | null;
  max_arrears: number | null;
  attendance_min: number | null;
  department_ids: DepartmentRef[] | null;
  graduation_years: number[] | null;
  custom_notes: string[];
}

export interface EligibilityRuleInput {
  cgpa_min?: number;
  cgpa_basis?: CgpaBasis;
  max_arrears?: number;
  attendance_min?: number;
  department_ids?: number[];
  graduation_years?: number[];
  custom_notes?: string[];
}

export interface AdminJob extends AdminJobSummary {
  body: string;
  created_by: number | null;
  skills: JobSkillOut[];
  eligibility: EligibilityRuleOut | null;
}

export interface JobCreateInput {
  company_id: number;
  title: string;
  body: string;
  role_id?: number | null;
  application_deadline?: string | null;
}

export interface JobUpdateInput {
  title?: string;
  body?: string;
  role_id?: number | null;
  application_deadline?: string | null;
}

export interface JobListFilters {
  company_id?: number;
  status?: JobStatus;
}
