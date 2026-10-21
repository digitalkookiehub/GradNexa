export interface Department {
  id: number;
  name: string;
  code: string;
}

export interface StudentProfile {
  id: number;
  user_id: number;
  college_id: number;
  department_id: number | null;
  department_name: string | null;
  roll_number: string | null;
  graduation_year: number | null;
  phone: string | null;
  profile_complete: boolean;
}

export interface StudentProfileUpdate {
  department_id?: number;
  roll_number?: string;
  graduation_year?: number;
  phone?: string;
}

export interface AcademicRecord {
  id: number;
  semester: number;
  cgpa: number;
  active_arrears: number;
  attendance_pct: number | null;
}

export interface AcademicRecordInput {
  semester: number;
  cgpa: number;
  active_arrears: number;
  attendance_pct: number | null;
}

export interface Project {
  id: number;
  title: string;
  description: string | null;
  skills: string[];
  url: string | null;
}

export interface ProjectInput {
  title: string;
  description: string | null;
  skills: string[];
  url: string | null;
}

export interface Certification {
  id: number;
  name: string;
  issuer: string | null;
  issued_on: string | null;
}

export interface CertificationInput {
  name: string;
  issuer: string | null;
  issued_on: string | null;
}
