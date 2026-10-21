import api from './api';
import type { AdminLearningResource, LearningResourceInput } from '@/types';

export interface ResourceFilters {
  skillId?: number;
  approved?: boolean;
}

export const adminResourceService = {
  async list(filters: ResourceFilters = {}): Promise<AdminLearningResource[]> {
    const params: { skill_id?: number; approved?: boolean } = {};
    if (filters.skillId !== undefined) params.skill_id = filters.skillId;
    if (filters.approved !== undefined) params.approved = filters.approved;
    const { data } = await api.get<AdminLearningResource[]>('/admin/learning-resources', { params });
    return data;
  },

  async create(input: LearningResourceInput): Promise<AdminLearningResource> {
    const { data } = await api.post<AdminLearningResource>('/admin/learning-resources', input);
    return data;
  },

  async update(id: number, input: LearningResourceInput): Promise<AdminLearningResource> {
    const { data } = await api.put<AdminLearningResource>(`/admin/learning-resources/${id}`, input);
    return data;
  },

  async remove(id: number): Promise<void> {
    await api.delete(`/admin/learning-resources/${id}`);
  },

  async approve(id: number): Promise<AdminLearningResource> {
    const { data } = await api.post<AdminLearningResource>(`/admin/learning-resources/${id}/approve`);
    return data;
  },

  async unapprove(id: number): Promise<AdminLearningResource> {
    const { data } = await api.post<AdminLearningResource>(`/admin/learning-resources/${id}/unapprove`);
    return data;
  },
};
