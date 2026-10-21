import { sourceTypeLabel } from '@/lib/knowledge';

export interface CitationItem {
  chunk_id: number;
  document_title: string;
  source_type: string;
  snippet: string;
}

interface CitationListProps {
  citations: CitationItem[];
  label?: string;
}

/** Renders citations as plain text only (snippets may contain markup-like text). */
export function CitationList({ citations, label = 'Citations' }: CitationListProps) {
  if (citations.length === 0) return null;
  return (
    <ul className="space-y-2" aria-label={label}>
      {citations.map((c, i) => (
        <li key={`${c.chunk_id}-${i}`} className="rounded-md border bg-muted/30 p-3 text-sm">
          <p className="font-medium">{c.document_title}</p>
          <p className="text-xs text-muted-foreground">{sourceTypeLabel(c.source_type)}</p>
          <p className="mt-1 whitespace-pre-wrap break-words">{c.snippet}</p>
        </li>
      ))}
    </ul>
  );
}
