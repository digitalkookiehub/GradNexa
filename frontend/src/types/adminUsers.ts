import type { UserRole } from './index';

export interface StudentSummary {
  student_id: number;
  department_id: number | null;
  department_name: string | null;
  roll_number: string | null;
  graduation_year: number | null;
  profile_complete: boolean;
}

export interface AdminUser {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  student: StudentSummary | null;
}

export interface AdminUserPage {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminUserQuery {
  search?: string;
  role?: UserRole | '';
  department_id?: number | null;
  page?: number;
  page_size?: number;
}

export interface RoleChangeResult {
  id: number;
  role: UserRole;
  previous_role: UserRole;
  removed_faculty_assignments: number;
  removed_hod_assignments: number;
}

export interface FacultyAssignment {
  id: number;
  faculty_user_id: number;
  faculty_name: string;
  faculty_email: string;
  student_id: number;
  student_name: string;
  student_email: string;
}

/** Roles an admin can assign from the Users screen (never SUPER_ADMIN). */
export const ASSIGNABLE_ROLES: UserRole[] = ['STUDENT', 'FACULTY', 'TPO', 'HOD', 'ADMIN'];

export const ROLE_LABELS: Record<string, string> = {
  STUDENT: 'Student',
  FACULTY: 'Faculty',
  TPO: 'TPO',
  HOD: 'HOD',
  ADMIN: 'Admin',
  SUPER_ADMIN: 'Super admin',
};
