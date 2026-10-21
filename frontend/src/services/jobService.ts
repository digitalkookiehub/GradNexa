import api from './api';
import { normaliseGap } from './readinessService';
import { num, numOrNull } from './assessmentService';
import type { EligibilityCheck, JobDetail, JobListItem, JobSkillFit } from '@/types/jobs';

export function normaliseJobDetail(raw: JobDetail): JobDetail {
  return {
    ...raw,
    body: raw.body ?? '',
    role_id: raw.role_id ?? null,
    role_name: raw.role_name ?? null,
    application_deadline: raw.application_deadline ?? null,
    deadline_passed: Boolean(raw.deadline_passed),
    skills: (raw.skills ?? []).map((s) => ({ ...s, required_level: num(s.required_level), weight: num(s.weight) })),
    eligibility_criteria: raw.eligibility_criteria
      ? {
          cgpa_min: numOrNull(raw.eligibility_criteria.cgpa_min),
          cgpa_basis: raw.eligibility_criteria.cgpa_basis ?? null,
          max_arrears: numOrNull(raw.eligibility_criteria.max_arrears),
          attendance_min: numOrNull(raw.eligibility_criteria.attendance_min),
          department_ids: raw.eligibility_criteria.department_ids ?? null,
          graduation_years: raw.eligibility_criteria.graduation_years ?? null,
          custom_notes: raw.eligibility_criteria.custom_notes ?? [],
        }
      : null,
  };
}

export function normaliseEligibility(raw: EligibilityCheck): EligibilityCheck {
  return { ...raw, criteria: raw.criteria ?? [], custom_notes: raw.custom_notes ?? [], note: raw.note ?? '' };
}

export function normaliseSkillFit(raw: JobSkillFit): JobSkillFit {
  return {
    ...raw,
    rule_id: raw.rule_id ?? null,
    rule_version: num(raw.rule_version, 1),
    overall: numOrNull(raw.overall),
    coverage: num(raw.coverage),
    gaps: (raw.gaps ?? []).map(normaliseGap),
  };
}

export const jobService = {
  async list(): Promise<JobListItem[]> {
    const { data } = await api.get<JobListItem[]>('/jobs');
    return (data ?? []).map((j) => ({ ...j, deadline_passed: Boolean(j.deadline_passed) }));
  },

  async get(id: number): Promise<JobDetail> {
    const { data } = await api.get<JobDetail>(`/jobs/${id}`);
    return normaliseJobDetail(data);
  },

  async eligibility(id: number): Promise<EligibilityCheck> {
    const { data } = await api.get<EligibilityCheck>(`/jobs/${id}/eligibility`);
    return normaliseEligibility(data);
  },

  async skillFit(id: number): Promise<JobSkillFit> {
    const { data } = await api.get<JobSkillFit>(`/jobs/${id}/skill-fit`);
    return normaliseSkillFit(data);
  },
};
