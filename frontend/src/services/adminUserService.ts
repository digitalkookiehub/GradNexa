import api from './api';
import type { AdminUserPage, AdminUserQuery, FacultyAssignment, RoleChangeResult } from '@/types/adminUsers';
import type { UserRole } from '@/types';

export const adminUserService = {
  async list(query: AdminUserQuery = {}): Promise<AdminUserPage> {
    const params: Record<string, string | number> = {};
    if (query.search?.trim()) params.search = query.search.trim();
    if (query.role) params.role = query.role;
    if (query.department_id) params.department_id = query.department_id;
    params.page = query.page ?? 1;
    params.page_size = query.page_size ?? 25;
    const { data } = await api.get<AdminUserPage>('/admin/users', { params });
    return { items: data?.items ?? [], total: data?.total ?? 0, page: data?.page ?? 1, page_size: data?.page_size ?? 25 };
  },

  async changeRole(userId: number, role: UserRole): Promise<RoleChangeResult> {
    const { data } = await api.put<RoleChangeResult>(`/admin/users/${userId}/role`, { role });
    return data;
  },

  async listFacultyAssignments(): Promise<FacultyAssignment[]> {
    const { data } = await api.get<FacultyAssignment[]>('/admin/faculty-assignments');
    return data ?? [];
  },

  async createFacultyAssignment(facultyUserId: number, studentId: number): Promise<void> {
    await api.post('/admin/faculty-assignments', { faculty_user_id: facultyUserId, student_id: studentId });
  },

  async removeFacultyAssignment(id: number): Promise<void> {
    await api.delete(`/admin/faculty-assignments/${id}`);
  },
};
