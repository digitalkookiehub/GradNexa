import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { ResumeCard } from '@/components/resume/ResumeCard';
import { ResumeUpload } from '@/components/resume/ResumeUpload';
import { Card, CardContent } from '@/components/ui/card';
import { getErrorMessage } from '@/lib/errors';
import { resumeService } from '@/services/resumeService';
import { roadmapService } from '@/services/roadmapService';
import type { ExplorerRole } from '@/types/roadmap';
import type { Resume } from '@/types/resume';

export function ResumePage() {
  const [searchParams] = useSearchParams();
  const jobParam = Number(searchParams.get('job'));
  const initialJobId = Number.isInteger(jobParam) && jobParam > 0 ? jobParam : null;
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [roles, setRoles] = useState<ExplorerRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rolesError, setRolesError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    resumeService
      .list()
      .then((r) => {
        if (!cancelled) setResumes(r);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load your resumes.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    roadmapService
      .listRoles()
      .then((r) => {
        if (!cancelled) setRoles(r.slice().sort((a, b) => Number(b.is_goal) - Number(a.is_goal)));
      })
      .catch((err: unknown) => {
        if (!cancelled) setRolesError(getErrorMessage(err, 'Could not load career roles; you can still analyze without a target role.'));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold">Resume</h1>
      <div className="space-y-1 text-sm text-muted-foreground">
        <p>
          Upload a PDF or DOCX resume to see which skills and sections can be found in it. Everything shown comes straight from your file; nothing
          is guessed.
        </p>
        <p>
          Resume analysis is not a readiness score and does not feed into your placement readiness. Skill matching is keyword-based against your
          college&apos;s configured skills, so it can miss synonyms. Scanned PDFs are not supported (no OCR).
        </p>
      </div>

      <Card>
        <CardContent className="p-4">
          <ResumeUpload onUploaded={(r) => setResumes((prev) => [r, ...prev])} />
        </CardContent>
      </Card>

      <FormMessage message={error} />
      <FormMessage message={rolesError} />
      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading resumes...
        </p>
      )}
      {!loading && !error && resumes.length === 0 && <p className="text-muted-foreground">You have not uploaded a resume yet.</p>}
      <div className="space-y-3">
        {resumes.map((r) => (
          <ResumeCard key={r.id} resume={r} roles={roles} initialJobId={initialJobId} onDeleted={(id) => setResumes((prev) => prev.filter((x) => x.id !== id))} />
        ))}
      </div>
    </div>
  );
}
