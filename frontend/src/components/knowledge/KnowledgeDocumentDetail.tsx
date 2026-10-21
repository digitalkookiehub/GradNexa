import { useEffect, useState } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getErrorMessage } from '@/lib/errors';
import { STATUS_LABELS, sourceTypeLabel } from '@/lib/knowledge';
import { formatBytes } from '@/lib/resume';
import { knowledgeService } from '@/services/knowledgeService';
import type { KnowledgeChunkPage, KnowledgeDocument } from '@/types/knowledge';

export const CHUNK_PAGE_SIZE = 5;

interface KnowledgeDocumentDetailProps {
  document: KnowledgeDocument;
  onClose: () => void;
}

export function KnowledgeDocumentDetail({ document: doc, onClose }: KnowledgeDocumentDetailProps) {
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<KnowledgeChunkPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    knowledgeService
      .chunks(doc.id, CHUNK_PAGE_SIZE, offset)
      .then((p) => {
        if (cancelled) return;
        setPage(p);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load the document chunks.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [doc.id, offset, attempt]);

  const total = page?.total ?? 0;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + CHUNK_PAGE_SIZE, total);

  return (
    <Card aria-label={`Details for ${doc.title}`}>
      <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
        <CardTitle className="text-lg">{doc.title}</CardTitle>
        <Button variant="outline" size="sm" onClick={onClose}>
          Close details
        </Button>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <dl className="grid gap-x-6 gap-y-1 sm:grid-cols-2">
          <div>
            <dt className="inline text-muted-foreground">Status: </dt>
            <dd className="inline">{STATUS_LABELS[doc.status] ?? doc.status}</dd>
          </div>
          <div>
            <dt className="inline text-muted-foreground">Source type: </dt>
            <dd className="inline">{sourceTypeLabel(doc.source_type)}</dd>
          </div>
          <div>
            <dt className="inline text-muted-foreground">Department: </dt>
            <dd className="inline">{doc.department_name ?? 'All departments'}</dd>
          </div>
          <div>
            <dt className="inline text-muted-foreground">File: </dt>
            <dd className="inline">
              {doc.original_filename} ({formatBytes(doc.size_bytes)})
            </dd>
          </div>
          <div>
            <dt className="inline text-muted-foreground">Chunks: </dt>
            <dd className="inline">{doc.chunk_count}</dd>
          </div>
          {doc.approved_at && (
            <div>
              <dt className="inline text-muted-foreground">Approved: </dt>
              <dd className="inline">{new Date(doc.approved_at).toLocaleDateString()}</dd>
            </div>
          )}
        </dl>

        <div className="space-y-2">
          <h3 className="font-semibold">Chunk preview</h3>
          <FormMessage message={error} />
          {loading && (
            <p role="status" className="text-muted-foreground">
              Loading chunks...
            </p>
          )}
          {!loading && error && (
            <Button variant="outline" size="sm" onClick={() => setAttempt((a) => a + 1)}>
              Retry
            </Button>
          )}
          {!loading && !error && page && page.chunks.length === 0 && <p className="text-muted-foreground">This document has no chunks.</p>}
          {!loading && page && page.chunks.length > 0 && (
            <ul className="space-y-2" aria-label="Chunks">
              {page.chunks.map((c) => (
                <li key={c.id} className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">
                    Chunk {c.chunk_index + 1}
                    {c.heading ? ` - ${c.heading}` : ''}
                  </p>
                  <p className="whitespace-pre-wrap break-words">{c.content}</p>
                </li>
              ))}
            </ul>
          )}
          {page && total > 0 && (
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" disabled={offset === 0 || loading} onClick={() => setOffset((o) => Math.max(0, o - CHUNK_PAGE_SIZE))}>
                Previous
              </Button>
              <span data-testid="chunk-range">
                {from}-{to} of {total}
              </span>
              <Button variant="outline" size="sm" disabled={offset + CHUNK_PAGE_SIZE >= total || loading} onClick={() => setOffset((o) => o + CHUNK_PAGE_SIZE)}>
                Next
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
