export interface AnswerFact {
  label: string;
  value: string;
}

export interface AnswerSection {
  heading: string;
  text: string;
  facts: AnswerFact[];
}

export interface AssistantCitation {
  document_id: number;
  document_title: string;
  source_type: string;
  chunk_id: number;
  chunk_index: number;
  snippet: string;
}

export interface AssistantAnswer {
  question: string;
  answer_sections: AnswerSection[];
  citations: AssistantCitation[];
  tools_used: string[];
  intent: string;
  insufficient_evidence: boolean;
  llm_used: boolean;
  notes: string[];
}

export interface AssistantQueryInput {
  question: string;
  role_id?: number;
  job_id?: number;
}

export type ConversationEntry =
  | { id: number; kind: 'pending'; question: string }
  | { id: number; kind: 'answer'; question: string; answer: AssistantAnswer }
  | { id: number; kind: 'error'; question: string; message: string };

export interface McpTool {
  name: string;
  description: string;
  allowed_roles: string[];
  enabled: boolean;
}
