export type KnowledgeSourceType =
  | 'SYLLABUS'
  | 'CURRICULUM'
  | 'LEARNING_MATERIAL'
  | 'PLACEMENT_GUIDE'
  | 'INTERVIEW_GUIDE'
  | 'POLICY'
  | 'OTHER';

export type KnowledgeStatus = 'PENDING' | 'APPROVED' | 'ARCHIVED';

export interface KnowledgeDocument {
  id: number;
  title: string;
  source_type: KnowledgeSourceType;
  department_id: number | null;
  department_name: string | null;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: KnowledgeStatus;
  uploaded_by: number;
  approved_by: number | null;
  approved_at: string | null;
  chunk_count: number;
  created_at: string;
}

export interface KnowledgeChunk {
  id: number;
  chunk_index: number;
  content: string;
  heading: string | null;
}

export interface KnowledgeChunkPage {
  total: number;
  chunks: KnowledgeChunk[];
}

export interface KnowledgeUploadInput {
  file: File;
  title: string;
  source_type: KnowledgeSourceType;
  department_id: number | null;
}

export interface KnowledgeUpdateInput {
  title?: string;
  source_type?: KnowledgeSourceType;
  department_id?: number | null;
}

export interface KnowledgePassage {
  document_id: number;
  document_title: string;
  source_type: string;
  chunk_id: number;
  chunk_index: number;
  snippet: string;
  score: number;
  query_coverage: number;
}

export interface KnowledgeSearchResult {
  query: string;
  insufficient_evidence: boolean;
  message: string | null;
  passages: KnowledgePassage[];
}
