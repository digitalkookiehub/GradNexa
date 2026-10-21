import api from './api';
import type {
  KnowledgeChunk,
  KnowledgeChunkPage,
  KnowledgeDocument,
  KnowledgePassage,
  KnowledgeSearchResult,
  KnowledgeUpdateInput,
  KnowledgeUploadInput,
} from '@/types/knowledge';

function toNumber(v: unknown): number {
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
}

export function normaliseDocument(raw: KnowledgeDocument): KnowledgeDocument {
  return {
    ...raw,
    department_id: raw.department_id ?? null,
    department_name: raw.department_name ?? null,
    approved_by: raw.approved_by ?? null,
    approved_at: raw.approved_at ?? null,
    size_bytes: toNumber(raw.size_bytes),
    chunk_count: toNumber(raw.chunk_count),
  };
}

function normaliseChunk(raw: KnowledgeChunk): KnowledgeChunk {
  return { ...raw, content: raw.content ?? '', heading: raw.heading ?? null };
}

export function normalisePassage(raw: KnowledgePassage): KnowledgePassage {
  return { ...raw, snippet: raw.snippet ?? '', score: toNumber(raw.score), query_coverage: toNumber(raw.query_coverage) };
}

export const knowledgeService = {
  async upload(input: KnowledgeUploadInput): Promise<KnowledgeDocument> {
    const form = new FormData();
    form.append('file', input.file);
    form.append('title', input.title);
    form.append('source_type', input.source_type);
    if (input.department_id !== null) form.append('department_id', String(input.department_id));
    const { data } = await api.post<KnowledgeDocument>('/admin/knowledge-documents', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return normaliseDocument(data);
  },

  async list(params: { status?: string; source_type?: string } = {}): Promise<KnowledgeDocument[]> {
    const { data } = await api.get<KnowledgeDocument[]>('/admin/knowledge-documents', {
      params: { status: params.status || undefined, source_type: params.source_type || undefined },
    });
    return (data ?? []).map(normaliseDocument);
  },

  async get(id: number): Promise<KnowledgeDocument> {
    const { data } = await api.get<KnowledgeDocument>(`/admin/knowledge-documents/${id}`);
    return normaliseDocument(data);
  },

  async chunks(id: number, limit: number, offset: number): Promise<KnowledgeChunkPage> {
    const { data } = await api.get<KnowledgeChunkPage>(`/admin/knowledge-documents/${id}/chunks`, { params: { limit, offset } });
    const chunks = (data?.chunks ?? []).map(normaliseChunk);
    return { total: toNumber(data?.total ?? chunks.length), chunks };
  },

  async update(id: number, input: KnowledgeUpdateInput): Promise<KnowledgeDocument> {
    const { data } = await api.put<KnowledgeDocument>(`/admin/knowledge-documents/${id}`, input);
    return normaliseDocument(data);
  },

  async remove(id: number): Promise<void> {
    await api.delete(`/admin/knowledge-documents/${id}`);
  },

  async approve(id: number): Promise<KnowledgeDocument> {
    const { data } = await api.post<KnowledgeDocument>(`/admin/knowledge-documents/${id}/approve`);
    return normaliseDocument(data);
  },

  async archive(id: number): Promise<KnowledgeDocument> {
    const { data } = await api.post<KnowledgeDocument>(`/admin/knowledge-documents/${id}/archive`);
    return normaliseDocument(data);
  },

  async search(query: string, topK?: number): Promise<KnowledgeSearchResult> {
    const { data } = await api.post<KnowledgeSearchResult>('/knowledge/search', { query, top_k: topK });
    return {
      query: data.query ?? query,
      insufficient_evidence: Boolean(data.insufficient_evidence),
      message: data.message ?? null,
      passages: (data.passages ?? []).map(normalisePassage),
    };
  },
};
