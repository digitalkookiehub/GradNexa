import api from './api';
import type {
  AcademicRecord,
  AcademicRecordInput,
  Certification,
  CertificationInput,
  Department,
  Project,
  ProjectInput,
  StudentProfile,
  StudentProfileUpdate,
} from '@/types/student';

type NumericLike = number | string | null | undefined;

interface RawAcademicRecord {
  id: number;
  semester: NumericLike;
  cgpa: NumericLike;
  active_arrears: NumericLike;
  attendance_pct?: NumericLike;
}

interface RawProject {
  id: number;
  title: string;
  description?: string | null;
  skills?: string[] | null;
  url?: string | null;
}

function toNumber(value: NumericLike): number | null {
  if (value === null || value === undefined || value === '') return null;
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export function normaliseAcademicRecord(raw: RawAcademicRecord): AcademicRecord {
  return {
    id: raw.id,
    semester: toNumber(raw.semester) ?? 0,
    cgpa: toNumber(raw.cgpa) ?? 0,
    active_arrears: toNumber(raw.active_arrears) ?? 0,
    attendance_pct: toNumber(raw.attendance_pct),
  };
}

function normaliseProject(raw: RawProject): Project {
  return {
    id: raw.id,
    title: raw.title,
    description: raw.description ?? null,
    skills: raw.skills ?? [],
    url: raw.url ?? null,
  };
}

export const studentService = {
  async listDepartments(): Promise<Department[]> {
    const { data } = await api.get<Department[]>('/departments');
    return data;
  },

  async getProfile(): Promise<StudentProfile> {
    const { data } = await api.get<StudentProfile>('/students/me');
    return data;
  },

  async updateProfile(payload: StudentProfileUpdate): Promise<StudentProfile> {
    const { data } = await api.put<StudentProfile>('/students/me', payload);
    return data;
  },

  async listAcademicRecords(): Promise<AcademicRecord[]> {
    const { data } = await api.get<RawAcademicRecord[]>('/students/me/academic-records');
    return data.map(normaliseAcademicRecord);
  },

  async createAcademicRecord(payload: AcademicRecordInput): Promise<AcademicRecord> {
    const { data } = await api.post<RawAcademicRecord>('/students/me/academic-records', payload);
    return normaliseAcademicRecord(data);
  },

  async updateAcademicRecord(id: number, payload: AcademicRecordInput): Promise<AcademicRecord> {
    const { data } = await api.put<RawAcademicRecord>(`/students/me/academic-records/${id}`, payload);
    return normaliseAcademicRecord(data);
  },

  async listProjects(): Promise<Project[]> {
    const { data } = await api.get<RawProject[]>('/students/me/projects');
    return data.map(normaliseProject);
  },

  async createProject(payload: ProjectInput): Promise<Project> {
    const { data } = await api.post<RawProject>('/students/me/projects', payload);
    return normaliseProject(data);
  },

  async deleteProject(id: number): Promise<void> {
    await api.delete(`/students/me/projects/${id}`);
  },

  async listCertifications(): Promise<Certification[]> {
    const { data } = await api.get<Certification[]>('/students/me/certifications');
    return data;
  },

  async createCertification(payload: CertificationInput): Promise<Certification> {
    const { data } = await api.post<Certification>('/students/me/certifications', payload);
    return data;
  },

  async deleteCertification(id: number): Promise<void> {
    await api.delete(`/students/me/certifications/${id}`);
  },
};
