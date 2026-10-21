import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { FieldError } from '@/components/auth/FieldError';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { parseNegativeMarking, STATUS_LABELS, TYPE_LABELS } from '@/lib/assessment';
import { getErrorMessage } from '@/lib/errors';
import { DepartmentSelect, SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { adminAssessmentService } from '@/services/adminAssessmentService';
import { studentService } from '@/services/studentService';
import { ASSESSMENT_TYPES, type AssessmentSummary, type AssessmentType, type Department } from '@/types';

type ActionKind = 'publish' | 'archive' | 'new-version' | 'delete';

interface PendingAction {
  kind: ActionKind;
  assessment: AssessmentSummary;
}

const ACTION_COPY: Record<ActionKind, { title: string; message: string; label: string }> = {
  publish: { title: 'Publish assessment?', message: 'Students will be able to attempt it and it can no longer be edited.', label: 'Publish' },
  archive: { title: 'Archive assessment?', message: 'Students will no longer be able to start new attempts.', label: 'Archive' },
  'new-version': { title: 'Create a new version?', message: 'A new draft copy will be created for editing.', label: 'Create version' },
  delete: { title: 'Delete assessment?', message: 'This permanently removes the draft and its questions.', label: 'Delete' },
};

export function AdminAssessmentsPage() {
  const [items, setItems] = useState<AssessmentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [busy, setBusy] = useState(false);

  const [title, setTitle] = useState('');
  const [type, setType] = useState<AssessmentType>('APTITUDE');
  const [timeLimit, setTimeLimit] = useState('');
  const [maxAttempts, setMaxAttempts] = useState('');
  const [negative, setNegative] = useState('0');
  const [negativeError, setNegativeError] = useState<string | undefined>();
  const [departmentId, setDepartmentId] = useState('');
  const [departments, setDepartments] = useState<Department[]>([]);
  const [titleError, setTitleError] = useState<string | undefined>();
  const [creating, setCreating] = useState(false);

  const load = useCallback(async (): Promise<void> => {
    try {
      setItems(await adminAssessmentService.list());
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load assessments.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    studentService
      .listDepartments()
      .then(setDepartments)
      .catch((err: unknown) => setError(getErrorMessage(err, 'Could not load departments.')));
  }, [load]);

  const handleCreate = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (!title.trim()) {
      setTitleError('Title is required.');
      return;
    }
    setTitleError(undefined);
    const parsed = parseNegativeMarking(negative);
    if (parsed.value === null) {
      setNegativeError(parsed.error);
      return;
    }
    setNegativeError(undefined);
    setCreating(true);
    setError(null);
    try {
      await adminAssessmentService.create({
        title: title.trim(),
        type,
        time_limit_min: timeLimit.trim() ? Number(timeLimit) : null,
        max_attempts: maxAttempts.trim() ? Number(maxAttempts) : null,
        negative_marking: parsed.value,
        department_id: departmentId ? Number(departmentId) : null,
      });
      setTitle('');
      setTimeLimit('');
      setMaxAttempts('');
      setNegative('0');
      setDepartmentId('');
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not create the assessment.'));
    } finally {
      setCreating(false);
    }
  };

  const runAction = async (): Promise<void> => {
    if (!pending) return;
    setBusy(true);
    setError(null);
    const { kind, assessment } = pending;
    try {
      if (kind === 'publish') await adminAssessmentService.publish(assessment.id);
      else if (kind === 'archive') await adminAssessmentService.archive(assessment.id);
      else if (kind === 'new-version') await adminAssessmentService.newVersion(assessment.id);
      else await adminAssessmentService.remove(assessment.id);
      setPending(null);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'The action could not be completed.'));
      setPending(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Manage assessments</h1>
      <FormMessage message={error} />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Create assessment</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleCreate(e)} noValidate className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="new-title">Title</Label>
              <Input id="new-title" value={title} onChange={(e) => setTitle(e.target.value)} aria-invalid={Boolean(titleError)} />
              <FieldError id="new-title-error" message={titleError} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-type">Type</Label>
              <select id="new-type" className={SELECT_CLASS} value={type} onChange={(e) => setType(e.target.value as AssessmentType)}>
                {ASSESSMENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {TYPE_LABELS[t]}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-time">Time limit (minutes, optional)</Label>
              <Input id="new-time" type="number" min={1} value={timeLimit} onChange={(e) => setTimeLimit(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-attempts">Max attempts (optional)</Label>
              <Input id="new-attempts" type="number" min={1} value={maxAttempts} onChange={(e) => setMaxAttempts(e.target.value)} />
            </div>
            <DepartmentSelect
              id="new-department"
              label="Department (optional)"
              departments={departments}
              value={departmentId}
              onChange={setDepartmentId}
              placeholder="No department"
            />
            <div className="space-y-2">
              <Label htmlFor="new-negative">Negative marking (0 to 1)</Label>
              <Input id="new-negative" type="number" min={0} max={1} step="any" value={negative} onChange={(e) => setNegative(e.target.value)} aria-invalid={Boolean(negativeError)} />
              <p className="text-xs text-muted-foreground">Fraction of a question's marks lost for each wrong answer, from 0 to 1. Leave 0 for no negative marking.</p>
              <FieldError id="new-negative-error" message={negativeError} />
            </div>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={creating}>
                {creating ? 'Creating...' : 'Create assessment'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {pending && (
        <ConfirmPanel
          title={ACTION_COPY[pending.kind].title}
          message={`${pending.assessment.title}: ${ACTION_COPY[pending.kind].message}`}
          confirmLabel={ACTION_COPY[pending.kind].label}
          destructive={pending.kind === 'delete'}
          busy={busy}
          onConfirm={() => void runAction()}
          onCancel={() => setPending(null)}
        />
      )}

      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading assessments...
        </p>
      )}
      {!loading && items.length === 0 && !error && <p className="text-muted-foreground">No assessments yet.</p>}
      <ul className="space-y-3">
        {items.map((a) => (
          <li key={a.id}>
            <Card>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <Link to={`/admin/assessments/${a.id}`} className="font-medium text-primary hover:underline">
                    {a.title}
                  </Link>
                  <div className="text-sm text-muted-foreground">
                    {TYPE_LABELS[a.type]} · v{a.version} · {STATUS_LABELS[a.status]} · {a.question_count} questions · {a.total_marks} marks
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {a.status === 'DRAFT' && (
                    <>
                      <Button size="sm" onClick={() => setPending({ kind: 'publish', assessment: a })}>
                        Publish
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => setPending({ kind: 'delete', assessment: a })}>
                        Delete
                      </Button>
                    </>
                  )}
                  {a.status === 'PUBLISHED' && (
                    <Button size="sm" variant="outline" onClick={() => setPending({ kind: 'archive', assessment: a })}>
                      Archive
                    </Button>
                  )}
                  {a.status !== 'DRAFT' && (
                    <Button size="sm" variant="outline" onClick={() => setPending({ kind: 'new-version', assessment: a })}>
                      New version
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
