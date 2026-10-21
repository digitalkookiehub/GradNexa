import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { formatDate } from '@/lib/assessment';
import { getErrorMessage } from '@/lib/errors';
import { formatBytes } from '@/lib/resume';
import { resumeService } from '@/services/resumeService';
import { AnalyzeForm } from './AnalyzeForm';
import type { ExplorerRole } from '@/types/roadmap';
import type { AnalyzePayload, Resume } from '@/types/resume';

interface ResumeCardProps {
  resume: Resume;
  roles: ExplorerRole[];
  initialJobId?: number | null;
  onDeleted: (id: number) => void;
}

type Mode = 'idle' | 'analyze' | 'delete';

export function ResumeCard({ resume, roles, initialJobId = null, onDeleted }: ResumeCardProps) {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('idle');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (payload: AnalyzePayload): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      await resumeService.analyze(resume.id, payload);
      navigate(`/resume/${resume.id}/analysis`);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not analyze this resume.'));
      setBusy(false);
    }
  };

  const handleDelete = async (): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      await resumeService.remove(resume.id);
      onDeleted(resume.id);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not delete this resume.'));
      setBusy(false);
      setMode('idle');
    }
  };

  return (
    <Card>
      <CardContent className="space-y-3 p-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="font-medium">{resume.original_filename}</p>
            <p className="text-xs text-muted-foreground">
              {formatBytes(resume.size_bytes)}
              {resume.page_count !== null ? ` · ${resume.page_count} page(s)` : ''} · uploaded {formatDate(resume.uploaded_at)}
            </p>
          </div>
          {mode === 'idle' && (
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={() => setMode('analyze')} disabled={!resume.has_text}>
                Analyze
              </Button>
              <Button size="sm" variant="outline" asChild>
                <Link to={`/resume/${resume.id}/analysis`}>Latest analysis</Link>
              </Button>
              <Button size="sm" variant="outline" onClick={() => setMode('delete')}>
                Delete
              </Button>
            </div>
          )}
        </div>
        {!resume.has_text && (
          <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            No text could be extracted from this file. It may be a scanned or image-only document; OCR is not supported, so it cannot be
            analyzed. Upload a text-based PDF or a DOCX instead.
          </div>
        )}
        <FormMessage message={error} />
        {mode === 'analyze' && (
          <AnalyzeForm resumeId={resume.id} roles={roles} initialJobId={initialJobId} busy={busy} error={null} onSubmit={(p) => void handleAnalyze(p)} onCancel={() => setMode('idle')} />
        )}
        {mode === 'delete' && (
          <ConfirmPanel
            title={`Delete ${resume.original_filename}?`}
            message="This permanently removes the file, its extracted text and all its analyses."
            confirmLabel="Delete resume"
            destructive
            busy={busy}
            onConfirm={() => void handleDelete()}
            onCancel={() => setMode('idle')}
          />
        )}
      </CardContent>
    </Card>
  );
}
