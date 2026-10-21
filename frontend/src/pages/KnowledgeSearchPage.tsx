import { useState } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { CitationList } from '@/components/knowledge/CitationList';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { QUERY_MAX } from '@/lib/knowledge';
import { knowledgeService } from '@/services/knowledgeService';
import type { KnowledgeSearchResult } from '@/types/knowledge';

export function KnowledgeSearchPage() {
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<KnowledgeSearchResult | null>(null);

  const handleSearch = async (): Promise<void> => {
    const q = query.trim();
    if (!q) {
      setError('Enter something to search for.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setResult(await knowledgeService.search(q));
    } catch (err) {
      setResult(null);
      setError(getErrorMessage(err, 'Search failed. Please try again.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Knowledge search</h1>
        <p className="text-sm text-muted-foreground">Searches only documents your college has approved. Results are matched by keywords, not by an AI model.</p>
      </div>

      <form
        className="flex flex-wrap items-end gap-3"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          void handleSearch();
        }}
      >
        <div className="min-w-0 flex-1 space-y-2">
          <Label htmlFor="kb-query">Search</Label>
          <Input id="kb-query" value={query} maxLength={QUERY_MAX} onChange={(e) => setQuery(e.target.value)} disabled={busy} />
        </div>
        <Button type="submit" disabled={busy}>
          {busy ? 'Searching...' : 'Search'}
        </Button>
      </form>

      <FormMessage message={error} />
      {busy && (
        <p role="status" className="text-muted-foreground">
          Searching...
        </p>
      )}

      {!busy && result && result.insufficient_evidence && (
        <p role="status" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {result.message ?? 'There is not enough approved evidence to answer this.'}
        </p>
      )}
      {!busy && result && !result.insufficient_evidence && result.passages.length === 0 && <p className="text-muted-foreground">No matching passages were found.</p>}
      {!busy && result && result.passages.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Results</h2>
          <CitationList citations={result.passages} label="Search results" />
        </section>
      )}
    </div>
  );
}
