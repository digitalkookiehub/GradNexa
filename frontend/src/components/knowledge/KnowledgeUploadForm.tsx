import { useRef, useState } from 'react';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getErrorMessage, getErrorStatus } from '@/lib/errors';
import { MAX_KNOWLEDGE_BYTES, SOURCE_TYPES, knowledgeUploadError, validateKnowledgeFile } from '@/lib/knowledge';
import { formatBytes } from '@/lib/resume';
import { knowledgeService } from '@/services/knowledgeService';
import type { Department } from '@/types';
import type { KnowledgeDocument, KnowledgeSourceType } from '@/types/knowledge';

interface KnowledgeUploadFormProps {
  departments: Department[];
  onUploaded: (doc: KnowledgeDocument) => void;
}

export function KnowledgeUploadForm({ departments, onUploaded }: KnowledgeUploadFormProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState('');
  const [sourceType, setSourceType] = useState<KnowledgeSourceType>('OTHER');
  const [departmentId, setDepartmentId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [titleError, setTitleError] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const choose = (f: File | null): void => {
    setFile(null);
    setFileError(null);
    if (!f) return;
    const problem = validateKnowledgeFile(f);
    if (problem) {
      setFileError(problem);
      if (inputRef.current) inputRef.current.value = '';
      return;
    }
    setFile(f);
    if (title.trim() === '') setTitle(f.name.replace(/\.[^.]+$/, ''));
  };

  const handleSubmit = async (): Promise<void> => {
    setError(null);
    const trimmed = title.trim();
    setTitleError(trimmed ? null : 'Enter a title.');
    if (!file) setFileError((prev) => prev ?? 'Choose a file to upload.');
    if (!trimmed || !file) return;
    setBusy(true);
    try {
      const doc = await knowledgeService.upload({
        file,
        title: trimmed,
        source_type: sourceType,
        department_id: departmentId === '' ? null : Number(departmentId),
      });
      setTitle('');
      setSourceType('OTHER');
      setDepartmentId('');
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
      onUploaded(doc);
    } catch (err) {
      setError(knowledgeUploadError(getErrorStatus(err), getErrorMessage(err, 'Upload failed. Please try again.')));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form
      className="space-y-4"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        void handleSubmit();
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="kb-title">Title</Label>
          <Input id="kb-title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} aria-invalid={!!titleError} disabled={busy} />
          {titleError && <p className="text-sm text-destructive">{titleError}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="kb-source">Source type</Label>
          <select id="kb-source" className={SELECT_CLASS} value={sourceType} onChange={(e) => setSourceType(e.target.value as KnowledgeSourceType)} disabled={busy}>
            {SOURCE_TYPES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="kb-department">Department (optional)</Label>
        <select id="kb-department" className={SELECT_CLASS} value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} disabled={busy}>
          <option value="">All departments</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="kb-file">Document file</Label>
        <input
          id="kb-file"
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="block text-sm"
          disabled={busy}
          aria-invalid={!!fileError}
          onChange={(e) => choose(e.target.files?.item(0) ?? null)}
        />
        <p className="text-xs text-muted-foreground">
          PDF, DOCX, TXT or MD, up to {formatBytes(MAX_KNOWLEDGE_BYTES)}. Scanned or image-only files are not supported because there is no OCR.
        </p>
        {file && (
          <p className="text-sm" data-testid="kb-selected-file">
            Selected: {file.name} ({formatBytes(file.size)})
          </p>
        )}
        {fileError && (
          <p role="alert" className="text-sm text-destructive">
            {fileError}
          </p>
        )}
      </div>
      <FormMessage message={error} />
      <Button type="submit" disabled={busy}>
        {busy ? 'Uploading...' : 'Upload document'}
      </Button>
    </form>
  );
}
