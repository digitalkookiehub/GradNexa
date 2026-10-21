import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { QuestionForm } from '@/components/assessment/QuestionForm';
import { FieldError } from '@/components/auth/FieldError';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { parseNegativeMarking, STATUS_LABELS, TYPE_LABELS } from '@/lib/assessment';
import { getErrorMessage } from '@/lib/errors';
import { adminAssessmentService } from '@/services/adminAssessmentService';
import { DepartmentSelect, SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { assessmentService } from '@/services/assessmentService';
import { studentService } from '@/services/studentService';
import { ASSESSMENT_TYPES, type AdminAssessmentDetail, type AdminQuestion, type AssessmentType, type Department, type QuestionInput, type Skill } from '@/types';

type QuestionEditor = { mode: 'closed' } | { mode: 'new' } | { mode: 'edit'; question: AdminQuestion };

export function AdminAssessmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const assessmentId = Number(id);
  const [detail, setDetail] = useState<AdminAssessmentDetail | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [type, setType] = useState<AssessmentType>('APTITUDE');
  const [timeLimit, setTimeLimit] = useState('');
  const [maxAttempts, setMaxAttempts] = useState('');
  const [negative, setNegative] = useState('0');
  const [negativeError, setNegativeError] = useState<string | undefined>();
  const [departmentId, setDepartmentId] = useState('');
  const [departments, setDepartments] = useState<Department[]>([]);
  const [titleError, setTitleError] = useState<string | undefined>();
  const [savingMeta, setSavingMeta] = useState(false);

  const [editor, setEditor] = useState<QuestionEditor>({ mode: 'closed' });
  const [savingQuestion, setSavingQuestion] = useState(false);
  const [deleting, setDeleting] = useState<AdminQuestion | null>(null);
  const [busy, setBusy] = useState(false);

  const applyDetail = (d: AdminAssessmentDetail): void => {
    setDetail(d);
    setTitle(d.title);
    setType(d.type);
    setTimeLimit(d.time_limit_min !== null ? String(d.time_limit_min) : '');
    setMaxAttempts(d.max_attempts !== null ? String(d.max_attempts) : '');
    setNegative(String(d.negative_marking));
    setDepartmentId(d.department_id !== null ? String(d.department_id) : '');
  };

  const reload = useCallback(async (): Promise<void> => {
    const d = await adminAssessmentService.get(assessmentId);
    setDetail(d);
  }, [assessmentId]);

  useEffect(() => {
    if (!Number.isInteger(assessmentId)) return;
    let cancelled = false;
    Promise.all([adminAssessmentService.get(assessmentId), assessmentService.listSkills(), studentService.listDepartments()])
      .then(([d, s, deps]) => {
        if (cancelled) return;
        applyDetail(d);
        setSkills(s);
        setDepartments(deps);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load the assessment.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [assessmentId]);

  if (!Number.isInteger(assessmentId)) return <FormMessage message="Invalid assessment." />;

  const isDraft = detail?.status === 'DRAFT';

  const handleSaveMeta = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
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
    setSavingMeta(true);
    setError(null);
    setNotice(null);
    try {
      await adminAssessmentService.update(assessmentId, {
        title: title.trim(),
        type,
        time_limit_min: timeLimit.trim() ? Number(timeLimit) : null,
        max_attempts: maxAttempts.trim() ? Number(maxAttempts) : null,
        negative_marking: parsed.value,
        department_id: departmentId ? Number(departmentId) : null,
      });
      await reload();
      setNotice('Assessment saved.');
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the assessment.'));
    } finally {
      setSavingMeta(false);
    }
  };

  const handleSaveQuestion = async (payload: QuestionInput): Promise<void> => {
    setSavingQuestion(true);
    setError(null);
    try {
      if (editor.mode === 'edit') await adminAssessmentService.updateQuestion(editor.question.id, payload);
      else await adminAssessmentService.addQuestion(assessmentId, payload);
      await reload();
      setEditor({ mode: 'closed' });
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the question.'));
    } finally {
      setSavingQuestion(false);
    }
  };

  const handleDeleteQuestion = async (): Promise<void> => {
    if (!deleting) return;
    setBusy(true);
    setError(null);
    try {
      await adminAssessmentService.deleteQuestion(deleting.id);
      setDeleting(null);
      await reload();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not delete the question.'));
      setDeleting(null);
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <p role="status" className="text-muted-foreground">
        Loading assessment...
      </p>
    );
  }
  if (!detail) {
    return (
      <div className="space-y-4">
        <FormMessage message={error ?? 'Assessment not found.'} />
        <Link to="/admin/assessments" className="text-primary hover:underline">
          Back to assessments
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to="/admin/assessments" className="text-sm text-primary hover:underline">
        Back to assessments
      </Link>
      <h1 className="text-2xl font-semibold">
        {detail.title} <span className="text-base font-normal text-muted-foreground">v{detail.version} · {STATUS_LABELS[detail.status]}</span>
      </h1>
      <FormMessage message={error} />
      <FormMessage message={notice} tone="success" />
      {!isDraft && <p className="text-sm text-muted-foreground">This assessment is not a draft, so it is read-only. Create a new version from the list to edit.</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleSaveMeta(e)} noValidate className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="meta-title">Title</Label>
              <Input id="meta-title" value={title} onChange={(e) => setTitle(e.target.value)} disabled={!isDraft} />
              <FieldError id="meta-title-error" message={titleError} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="meta-type">Type</Label>
              <select id="meta-type" className={SELECT_CLASS} value={type} onChange={(e) => setType(e.target.value as AssessmentType)} disabled={!isDraft}>
                {ASSESSMENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {TYPE_LABELS[t]}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="meta-time">Time limit (minutes)</Label>
              <Input id="meta-time" type="number" min={1} value={timeLimit} onChange={(e) => setTimeLimit(e.target.value)} disabled={!isDraft} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="meta-attempts">Max attempts</Label>
              <Input id="meta-attempts" type="number" min={1} value={maxAttempts} onChange={(e) => setMaxAttempts(e.target.value)} disabled={!isDraft} />
            </div>
            <DepartmentSelect
              id="meta-department"
              label="Department (optional)"
              departments={departments}
              value={departmentId}
              onChange={setDepartmentId}
              placeholder="No department"
              disabled={!isDraft}
            />
            <div className="space-y-2">
              <Label htmlFor="meta-negative">Negative marking (0 to 1)</Label>
              <Input id="meta-negative" type="number" min={0} max={1} step="any" value={negative} onChange={(e) => setNegative(e.target.value)} disabled={!isDraft} aria-invalid={Boolean(negativeError)} />
              <p className="text-xs text-muted-foreground">Fraction of a question's marks lost for each wrong answer, from 0 to 1. Leave 0 for no negative marking.</p>
              <FieldError id="meta-negative-error" message={negativeError} />
            </div>
            {isDraft && (
              <div className="sm:col-span-2">
                <Button type="submit" disabled={savingMeta}>
                  {savingMeta ? 'Saving...' : 'Save details'}
                </Button>
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            Questions ({detail.question_count}, {detail.total_marks} marks)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {deleting && (
            <ConfirmPanel
              title="Delete question?"
              message="This permanently removes the question from this draft."
              confirmLabel="Delete question"
              destructive
              busy={busy}
              onConfirm={() => void handleDeleteQuestion()}
              onCancel={() => setDeleting(null)}
            />
          )}
          {detail.questions.length === 0 && <p className="text-sm text-muted-foreground">No questions yet.</p>}
          <ol className="space-y-3">
            {detail.questions.map((q, i) => (
              <li key={q.id} className="rounded-md border p-3 text-sm">
                <div className="font-medium">
                  {i + 1}. {q.body}
                </div>
                <div className="text-xs text-muted-foreground">
                  {q.skill_name} · {q.difficulty} · {q.marks} marks
                </div>
                <ul className="mt-2 space-y-1">
                  {q.options.map((o) => (
                    <li key={o.id} className={q.correct_option_ids.includes(o.id) ? 'font-medium text-green-700' : ''}>
                      {o.text}
                      {q.correct_option_ids.includes(o.id) && ' (correct)'}
                    </li>
                  ))}
                </ul>
                {isDraft && (
                  <div className="mt-2 flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setEditor({ mode: 'edit', question: q })}>
                      Edit
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => setDeleting(q)}>
                      Delete
                    </Button>
                  </div>
                )}
              </li>
            ))}
          </ol>
          {isDraft && editor.mode === 'closed' && <Button onClick={() => setEditor({ mode: 'new' })}>Add question</Button>}
          {isDraft && editor.mode !== 'closed' && (
            <QuestionForm
              key={editor.mode === 'edit' ? editor.question.id : 'new'}
              skills={skills}
              initial={editor.mode === 'edit' ? editor.question : undefined}
              submitting={savingQuestion}
              onSubmit={(p) => void handleSaveQuestion(p)}
              onCancel={() => setEditor({ mode: 'closed' })}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
