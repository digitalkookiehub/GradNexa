import { useRef, useState, type DragEvent } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { getErrorMessage, getErrorStatus } from '@/lib/errors';
import { MAX_RESUME_BYTES, formatBytes, uploadErrorMessage, validateResumeFile } from '@/lib/resume';
import { resumeService } from '@/services/resumeService';
import type { Resume } from '@/types/resume';

interface ResumeUploadProps {
  onUploaded: (resume: Resume) => void;
}

export function ResumeUpload({ onUploaded }: ResumeUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);

  const choose = (f: File | null): void => {
    setFile(null);
    setError(null);
    if (!f) return;
    const problem = validateResumeFile(f);
    if (problem) {
      setError(problem);
      if (inputRef.current) inputRef.current.value = '';
      return;
    }
    setFile(f);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    setDragging(false);
    choose(e.dataTransfer.files.item(0));
  };

  const handleUpload = async (): Promise<void> => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const resume = await resumeService.upload(file);
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
      onUploaded(resume);
    } catch (err) {
      setError(uploadErrorMessage(getErrorStatus(err), getErrorMessage(err, 'Upload failed. Please try again.')));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`space-y-2 rounded-lg border-2 border-dashed p-6 text-center ${dragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/30'}`}
      >
        <Label htmlFor="resume-file">Resume file</Label>
        <input
          id="resume-file"
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="mx-auto block text-sm"
          disabled={busy}
          onChange={(e) => choose(e.target.files?.item(0) ?? null)}
        />
        <p className="text-xs text-muted-foreground">
          Drop a PDF or DOCX here (up to {formatBytes(MAX_RESUME_BYTES)}). Scanned or image-only PDFs are not supported because there is no OCR.
        </p>
      </div>
      <FormMessage message={error} />
      {file && (
        <p className="text-sm" data-testid="selected-file">
          Selected: {file.name} ({formatBytes(file.size)})
        </p>
      )}
      <Button onClick={() => void handleUpload()} disabled={!file || busy}>
        {busy ? 'Uploading...' : 'Upload resume'}
      </Button>
    </div>
  );
}
