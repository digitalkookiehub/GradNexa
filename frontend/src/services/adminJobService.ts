import api from './api';
import { num, numOrNull } from './assessmentService';
import type {
  AdminCompany,
  AdminJob,
  AdminJobSummary,
  CompanyInput,
  EligibilityRuleInput,
  EligibilityRuleOut,
  JobCreateInput,
  JobListFilters,
  JobSkillInput,
  JobSkillOut,
  JobUpdateInput,
} from '@/types/jobAdmin';

function normaliseCompany(raw: AdminCompany): AdminCompany {
  return { ...raw, description: raw.description ?? null, website: raw.website ?? null, job_count: num(raw.job_count) };
}

function normaliseSummary<T extends AdminJobSummary>(raw: T): T {
  return {
    ...raw,
    role_id: raw.role_id ?? null,
    role_name: raw.role_name ?? null,
    application_deadline: raw.application_deadline ?? null,
    has_eligibility_rule: Boolean(raw.has_eligibility_rule),
  };
}

function normaliseSkills(raw: JobSkillOut[] | null | undefined): JobSkillOut[] {
  return (raw ?? []).map((s) => ({ ...s, required_level: num(s.required_level), weight: num(s.weight) }));
}

export function normaliseEligibility(raw: EligibilityRuleOut | null | undefined): EligibilityRuleOut | null {
  if (!raw) return null;
  return {
    cgpa_min: numOrNull(raw.cgpa_min),
    cgpa_basis: raw.cgpa_basis ?? null,
    max_arrears: numOrNull(raw.max_arrears),
    attendance_min: numOrNull(raw.attendance_min),
    department_ids: raw.department_ids ?? null,
    graduation_years: raw.graduation_years ? raw.graduation_years.map((y) => num(y)) : null,
    custom_notes: raw.custom_notes ?? [],
  };
}

function normaliseJob(raw: AdminJob): AdminJob {
  return {
    ...normaliseSummary(raw),
    body: raw.body ?? '',
    created_by: raw.created_by ?? null,
    skills: normaliseSkills(raw.skills),
    eligibility: normaliseEligibility(raw.eligibility),
  };
}

export const adminJobService = {
  async listCompanies(): Promise<AdminCompany[]> {
    const { data } = await api.get<AdminCompany[]>('/admin/companies');
    return data.map(normaliseCompany);
  },

  async createCompany(payload: CompanyInput): Promise<AdminCompany> {
    const { data } = await api.post<AdminCompany>('/admin/companies', payload);
    return normaliseCompany(data);
  },

  async updateCompany(id: number, payload: CompanyInput): Promise<AdminCompany> {
    const { data } = await api.put<AdminCompany>(`/admin/companies/${id}`, payload);
    return normaliseCompany(data);
  },

  async deleteCompany(id: number): Promise<void> {
    await api.delete(`/admin/companies/${id}`);
  },

  async listJobs(filters: JobListFilters = {}): Promise<AdminJobSummary[]> {
    const params: Record<string, string | number> = {};
    if (filters.company_id !== undefined) params.company_id = filters.company_id;
    if (filters.status !== undefined) params.status = filters.status;
    const { data } = await api.get<AdminJobSummary[]>('/admin/jobs', { params });
    return data.map(normaliseSummary);
  },

  async getJob(id: number): Promise<AdminJob> {
    const { data } = await api.get<AdminJob>(`/admin/jobs/${id}`);
    return normaliseJob(data);
  },

  async createJob(payload: JobCreateInput): Promise<AdminJob> {
    const { data } = await api.post<AdminJob>('/admin/jobs', payload);
    return normaliseJob(data);
  },

  async updateJob(id: number, payload: JobUpdateInput): Promise<AdminJob> {
    const { data } = await api.put<AdminJob>(`/admin/jobs/${id}`, payload);
    return normaliseJob(data);
  },

  async deleteJob(id: number): Promise<void> {
    await api.delete(`/admin/jobs/${id}`);
  },

  /** The response body is not relied upon; callers refetch the job. */
  async publishJob(id: number): Promise<void> {
    await api.post(`/admin/jobs/${id}/publish`);
  },

  async closeJob(id: number): Promise<void> {
    await api.post(`/admin/jobs/${id}/close`);
  },

  async setJobSkills(id: number, skills: JobSkillInput[]): Promise<JobSkillOut[]> {
    const { data } = await api.put<JobSkillOut[]>(`/admin/jobs/${id}/skills`, skills);
    return normaliseSkills(data);
  },

  async setEligibility(id: number, payload: EligibilityRuleInput): Promise<EligibilityRuleOut> {
    const { data } = await api.put<EligibilityRuleOut>(`/admin/jobs/${id}/eligibility`, payload);
    return normaliseEligibility(data) as EligibilityRuleOut;
  },

  async deleteEligibility(id: number): Promise<void> {
    await api.delete(`/admin/jobs/${id}/eligibility`);
  },
};
