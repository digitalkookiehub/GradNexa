import api from './api';
import type { AnalysisSummary, AnalyzePayload, Extracted, Resume, ResumeAnalysis, ResumeText } from '@/types/resume';

export function normaliseExtracted(raw: Partial<Extracted> | undefined): Extracted {
  return {
    sections_found: raw?.sections_found ?? [],
    skills: (raw?.skills ?? []).map((s) => ({ ...s, spans: s.spans ?? [] })),
    education: raw?.education ?? [],
    projects: raw?.projects ?? [],
    experience: raw?.experience ?? [],
    certifications: raw?.certifications ?? [],
  };
}

export function normaliseAnalysis(raw: ResumeAnalysis): ResumeAnalysis {
  return {
    ...raw,
    role_id: raw.role_id ?? null,
    role_name: raw.role_name ?? null,
    job_id: raw.job_id ?? null,
    job_title: raw.job_title ?? null,
    extracted: normaliseExtracted(raw.extracted),
    role_match: raw.role_match
      ? { match_percent: raw.role_match.match_percent ?? null, found: raw.role_match.found ?? [], missing: raw.role_match.missing ?? [] }
      : null,
    jd_match: raw.jd_match ? { match_percent: raw.jd_match.match_percent ?? null, skills_in_jd: raw.jd_match.skills_in_jd ?? [] } : null,
    notes: raw.notes ?? [],
  };
}

export const resumeService = {
  async upload(file: File): Promise<Resume> {
    const form = new FormData();
    form.append('file', file);
    const { data } = await api.post<Resume>('/resumes', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    return data;
  },

  async list(): Promise<Resume[]> {
    const { data } = await api.get<Resume[]>('/resumes');
    return data;
  },

  async remove(id: number): Promise<void> {
    await api.delete(`/resumes/${id}`);
  },

  async getText(id: number): Promise<string> {
    const { data } = await api.get<ResumeText>(`/resumes/${id}/text`);
    return data.text ?? '';
  },

  async analyze(id: number, payload: AnalyzePayload): Promise<ResumeAnalysis> {
    const { data } = await api.post<ResumeAnalysis>(`/resumes/${id}/analyze`, payload);
    return normaliseAnalysis(data);
  },

  async getAnalysis(id: number): Promise<ResumeAnalysis> {
    const { data } = await api.get<ResumeAnalysis>(`/resumes/${id}/analysis`);
    return normaliseAnalysis(data);
  },

  async listAnalyses(id: number): Promise<AnalysisSummary[]> {
    const { data } = await api.get<AnalysisSummary[]>(`/resumes/${id}/analyses`);
    return data;
  },
};
