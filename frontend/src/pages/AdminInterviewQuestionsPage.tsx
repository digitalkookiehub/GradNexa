import { useCallback, useEffect, useState } from 'react';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { FormMessage } from '@/components/auth/FormField';
import { BankQuestionForm } from '@/components/interview/BankQuestionForm';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { adminInterviewService } from '@/services/adminInterviewService';
import { assessmentService } from '@/services/assessmentService';
import { readinessService } from '@/services/readinessService';
import type { BankQuestion, BankQuestionInput, CareerRole, Skill } from '@/types';

type Editing = { mode: 'none' } | { mode: 'create' } | { mode: 'edit'; question: BankQuestion };

export function AdminInterviewQuestionsPage() {
  const [questions, setQuestions] = useState<BankQuestion[]>([]);
  const [roles, setRoles] = useState<CareerRole[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [roleFilter, setRoleFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [editing, setEditing] = useState<Editing>({ mode: 'none' });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [deactivating, setDeactivating] = useState<BankQuestion | null>(null);
  const [busyDelete, setBusyDelete] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([readinessService.listRoles(), assessmentService.listSkills()])
      .then(([r, s]) => {
        if (cancelled) return;
        setRoles(r);
        setSkills(s);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(getErrorMessage(err, 'Could not load roles and skills.'));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    adminInterviewService
      .list({ role_id: roleFilter ? Number(roleFilter) : null, active: activeFilter === '' ? null : activeFilter === 'true' })
      .then((q) => {
        if (cancelled) return;
        setQuestions(q);
        setLoadError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(getErrorMessage(err, 'Could not load interview questions.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [roleFilter, activeFilter, attempt]);

  const reload = useCallback((): void => {
    setLoading(true);
    setLoadError(null);
    setAttempt((a) => a + 1);
  }, []);

  const handleSubmit = async (payload: BankQuestionInput): Promise<void> => {
    setSaving(true);
    setSaveError(null);
    try {
      if (editing.mode === 'edit') await adminInterviewService.update(editing.question.id, payload);
      else await adminInterviewService.create(payload);
      setEditing({ mode: 'none' });
      reload();
    } catch (err) {
      setSaveError(getErrorMessage(err, 'Could not save the question.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async (): Promise<void> => {
    if (!deactivating) return;
    setBusyDelete(true);
    setActionError(null);
    try {
      await adminInterviewService.deactivate(deactivating.id);
      setDeactivating(null);
      reload();
    } catch (err) {
      setActionError(getErrorMessage(err, 'Could not deactivate the question.'));
      setDeactivating(null);
    } finally {
      setBusyDelete(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">Interview questions</h1>
          <p className="text-sm text-muted-foreground">Answers are scored by keyword-rubric coverage only.</p>
        </div>
        {editing.mode === 'none' && <Button onClick={() => { setSaveError(null); setEditing({ mode: 'create' }); }}>New question</Button>}
      </div>

      {editing.mode !== 'none' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{editing.mode === 'edit' ? 'Edit question' : 'New question'}</CardTitle>
          </CardHeader>
          <CardContent>
            <BankQuestionForm
              key={editing.mode === 'edit' ? editing.question.id : 'new'}
              initial={editing.mode === 'edit' ? editing.question : null}
              roles={roles}
              skills={skills}
              busy={saving}
              error={saveError}
              onSubmit={(p) => void handleSubmit(p)}
              onCancel={() => setEditing({ mode: 'none' })}
            />
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap gap-4">
        <div className="space-y-2">
          <Label htmlFor="filter-role">Filter by role</Label>
          <select id="filter-role" className={SELECT_CLASS} value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
            <option value="">All roles</option>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="filter-active">Status</Label>
          <select id="filter-active" className={SELECT_CLASS} value={activeFilter} onChange={(e) => setActiveFilter(e.target.value)}>
            <option value="">All</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </div>
      </div>

      <FormMessage message={actionError} />
      {deactivating && (
        <ConfirmPanel
          title="Deactivate this question?"
          message="It will no longer be used in new interviews. Past interviews are not affected."
          confirmLabel="Deactivate"
          destructive
          busy={busyDelete}
          onConfirm={() => void handleDeactivate()}
          onCancel={() => setDeactivating(null)}
        />
      )}

      {loading ? (
        <p role="status" className="py-8 text-center text-muted-foreground">
          Loading questions...
        </p>
      ) : loadError ? (
        <div className="space-y-3">
          <FormMessage message={loadError} />
          <Button variant="outline" onClick={reload}>
            Retry
          </Button>
        </div>
      ) : questions.length === 0 ? (
        <p className="text-sm text-muted-foreground" data-testid="no-questions">
          No interview questions match these filters.
        </p>
      ) : (
        <ul className="space-y-3" aria-label="Interview questions">
          {questions.map((q) => (
            <li key={q.id} className="space-y-2 rounded-md border bg-background p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="font-medium">{q.prompt}</p>
                <span className={`rounded-full px-2 py-0.5 text-xs ${q.is_active ? 'bg-green-100 text-green-800' : 'bg-muted text-muted-foreground'}`}>
                  {q.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                {q.competency} · {q.role_name ?? 'Any role'} · min {q.min_words} words · {q.rubric.length} concept{q.rubric.length === 1 ? '' : 's'}
              </p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => { setSaveError(null); setEditing({ mode: 'edit', question: q }); }}>
                  Edit
                </Button>
                {q.is_active && (
                  <Button size="sm" variant="outline" onClick={() => setDeactivating(q)} aria-label={`Deactivate ${q.prompt}`}>
                    Deactivate
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
