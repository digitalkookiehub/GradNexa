export type UserRole = 'STUDENT' | 'FACULTY' | 'TPO' | 'HOD' | 'ADMIN' | 'SUPER_ADMIN';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  college_id: number | null;
  is_active: boolean;
  is_verified: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  college_code: string;
}

export interface ApiErrorBody {
  detail?: string | { msg: string }[];
}

export * from './student';
export * from './assessment';
export * from './readiness';
export * from './roadmap';
export * from './dashboard';
export * from './interview';
export * from './facultyDashboard';
export * from './hodDashboard';
export * from './placementAnalytics';
export * from './hodAssignment';
