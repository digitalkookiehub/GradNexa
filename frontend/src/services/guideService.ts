import api from './api';
import type { Guide, GuideProcedure } from '@/types/guide';

function normaliseProcedure(p: GuideProcedure): GuideProcedure {
  return {
    ...p,
    path: p.path ?? null,
    before: p.before ?? [],
    steps: p.steps ?? [],
    result: p.result ?? [],
    problems: p.problems ?? [],
    terms: p.terms ?? [],
    tables: p.tables ?? [],
  };
}

export const guideService = {
  async get(): Promise<Guide> {
    const { data } = await api.get<Guide>('/guide');
    return {
      title: data?.title ?? 'User guide',
      tagline: data?.tagline ?? '',
      principles: data?.principles ?? [],
      roles: data?.roles ?? [],
      overview: data?.overview ?? [],
      groups: (data?.groups ?? []).map((g) => ({ ...g, procedures: (g.procedures ?? []).map(normaliseProcedure) })),
      markdown: data?.markdown ?? '',
    };
  },
};
