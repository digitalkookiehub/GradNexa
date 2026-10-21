import api from './api';
import type { AssistantAnswer, AssistantQueryInput } from '@/types/assistant';

export function normaliseAnswer(raw: AssistantAnswer): AssistantAnswer {
  return {
    ...raw,
    answer_sections: (raw.answer_sections ?? []).map((s) => ({ heading: s.heading ?? '', text: s.text ?? '', facts: s.facts ?? [] })),
    citations: (raw.citations ?? []).map((c) => ({ ...c, snippet: c.snippet ?? '' })),
    tools_used: raw.tools_used ?? [],
    intent: raw.intent ?? '',
    insufficient_evidence: Boolean(raw.insufficient_evidence),
    llm_used: Boolean(raw.llm_used),
    notes: raw.notes ?? [],
  };
}

export const assistantService = {
  async query(input: AssistantQueryInput): Promise<AssistantAnswer> {
    const { data } = await api.post<AssistantAnswer>('/assistant/query', input);
    return normaliseAnswer(data);
  },
};
