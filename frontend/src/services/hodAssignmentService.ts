import api from './api';
import { num } from './assessmentService';
import type { HodAssignment, HodAssignmentCreate } from '@/types';

function normalise(raw: HodAssignment): HodAssignment {
  return { ...raw, id: num(raw.id), hod_user_id: num(raw.hod_user_id), department_id: num(raw.department_id) };
}

export const hodAssignmentService = {
  async list(): Promise<HodAssignment[]> {
    const { data } = await api.get<HodAssignment[]>('/admin/hod-assignments');
    return (data ?? []).map(normalise);
  },
  async create(payload: HodAssignmentCreate): Promise<HodAssignment> {
    const { data } = await api.post<HodAssignment>('/admin/hod-assignments', payload);
    return normalise(data);
  },
  async remove(id: number): Promise<void> {
    await api.delete(`/admin/hod-assignments/${id}`);
  },
};
