import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatClock, secondsRemaining } from '@/lib/assessment';
import { getErrorMessage } from '@/lib/errors';
import { assessmentService } from '@/services/assessmentService';
import type { AnswerMap, Attempt, AttemptQuestion } from '@/types';

const SAVE_DEBOUNCE_MS = 800;

type SaveState = 'idle' | 'saving' | 'saved' | 'error';

function isConflict(err: unknown): boolean {
  return axios.isAxiosError(err) && err.response?.status === 409;
}

interface QuestionViewProps {
  question: AttemptQuestion;
  selected: string[];
  onChange: (optionIds: string[]) => void;
  disabled: boolean;
}

function QuestionView({ question, selected, onChange, disabled }: QuestionViewProps) {
  const toggle = (optionId: string): void => {
    if (question.multi_select) {
      onChange(selected.includes(optionId) ? selected.filter((id) => id !== optionId) : [...selected, optionId]);
    } else {
      onChange([optionId]);
    }
  };
  const inputType = question.multi_select ? 'checkbox' : 'radio';
  return (
    <fieldset className="space-y-3">
      <legend className="text-base font-medium">{question.body}</legend>
      <p className="text-xs text-muted-foreground">
        {question.skill_name} · {question.marks} {question.marks === 1 ? 'mark' : 'marks'} ·{' '}
        {question.multi_select ? 'Select all that apply' : 'Select one'}
      </p>
      <div className="space-y-2">
        {question.options.map((o) => (
          <label key={o.id} className="flex cursor-pointer items-center gap-3 rounded-md border p-3 text-sm hover:bg-accent">
            <input
              type={inputType}
              name={`q-${question.id}`}
              checked={selected.includes(o.id)}
              onChange={() => toggle(o.id)}
              disabled={disabled}
            />
            <span>{o.text}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function AttemptPage() {
  const { id } = useParams<{ id: string }>();
  const assessmentId = Number(id);
  const navigate = useNavigate();

  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [index, setIndex] = useState(0);
  const [now, setNow] = useState<number>(() => Date.now());
  const [confirming, setConfirming] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [finished, setFinished] = useState(false);

  const answersRef = useRef<AnswerMap>({});
  const dirtyRef = useRef(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const submittingRef = useRef(false);

  useEffect(() => {
    if (!Number.isInteger(assessmentId)) return;
    let cancelled = false;
    assessmentService
      .startAttempt(assessmentId)
      .then((a) => {
        if (cancelled) return;
        answersRef.current = a.answers;
        setAttempt(a);
        setAnswers(a.answers);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(getErrorMessage(err, 'Could not start the assessment.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [assessmentId]);

  const attemptId = attempt?.id ?? null;

  const clearSaveTimer = useCallback((): void => {
    if (saveTimer.current) {
      clearTimeout(saveTimer.current);
      saveTimer.current = null;
    }
  }, []);

  const flushSave = useCallback(async (): Promise<boolean> => {
    if (attemptId === null) return true;
    clearSaveTimer();
    if (!dirtyRef.current) return true;
    dirtyRef.current = false;
    setSaveState('saving');
    try {
      await assessmentService.saveAnswers(attemptId, answersRef.current);
      setSaveState('saved');
      return true;
    } catch (err) {
      dirtyRef.current = true;
      setSaveState('error');
      if (isConflict(err)) {
        setFinished(true);
        setActionError(getErrorMessage(err, 'This attempt has already been finished.'));
      } else {
        setActionError(getErrorMessage(err, 'Could not save your answers. Your latest changes are not saved yet.'));
      }
      return false;
    }
  }, [attemptId, clearSaveTimer]);

  const submit = useCallback(
    async (auto: boolean): Promise<void> => {
      if (attemptId === null || submittingRef.current) return;
      submittingRef.current = true;
      setSubmitting(true);
      setActionError(null);
      clearSaveTimer();
      try {
        // Best-effort final save; a 409 here means the attempt is already closed.
        if (dirtyRef.current) {
          try {
            await assessmentService.saveAnswers(attemptId, answersRef.current);
            dirtyRef.current = false;
          } catch (err) {
            if (!isConflict(err) && !auto) {
              setActionError(getErrorMessage(err, 'Could not save your answers. Please try again.'));
              return;
            }
          }
        }
        await assessmentService.submit(attemptId);
        setFinished(true);
        navigate(`/attempts/${attemptId}/result`, { replace: true });
      } catch (err) {
        if (isConflict(err)) {
          // Already submitted or expired elsewhere: the result is the source of truth.
          setFinished(true);
          navigate(`/attempts/${attemptId}/result`, { replace: true });
          return;
        }
        setActionError(getErrorMessage(err, 'Could not submit the attempt.'));
        setConfirming(false);
      } finally {
        submittingRef.current = false;
        setSubmitting(false);
      }
    },
    [attemptId, clearSaveTimer, navigate],
  );

  const submitRef = useRef(submit);
  useEffect(() => {
    submitRef.current = submit;
  }, [submit]);

  // Countdown tick; triggers auto-submit once on expiry.
  const expiresAt = attempt?.expires_at ?? null;
  useEffect(() => {
    if (!expiresAt || finished) return;
    const timer = setInterval(() => {
      const t = Date.now();
      setNow(t);
      if (secondsRemaining(expiresAt, t) === 0) {
        clearInterval(timer);
        void submitRef.current(true);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [expiresAt, finished]);

  useEffect(() => clearSaveTimer, [clearSaveTimer]);

  const handleChange = (questionId: number, optionIds: string[]): void => {
    const next: AnswerMap = { ...answersRef.current, [String(questionId)]: optionIds };
    answersRef.current = next;
    dirtyRef.current = true;
    setAnswers(next);
    setSaveState('idle');
    clearSaveTimer();
    saveTimer.current = setTimeout(() => {
      void flushSave();
    }, SAVE_DEBOUNCE_MS);
  };

  if (!Number.isInteger(assessmentId)) {
    return <FormMessage message="Invalid assessment." />;
  }
  if (loading) {
    return (
      <p role="status" className="py-12 text-center text-muted-foreground">
        Loading assessment...
      </p>
    );
  }
  if (loadError || !attempt) {
    return (
      <div className="mx-auto max-w-md space-y-4 py-12">
        <FormMessage message={loadError ?? 'Could not start the assessment.'} />
        <Link to="/assessments" className="text-primary hover:underline">
          Back to assessments
        </Link>
      </div>
    );
  }

  const questions = attempt.questions;
  if (questions.length === 0) {
    return (
      <div className="mx-auto max-w-md space-y-4 py-12">
        <FormMessage message="This assessment has no questions." />
        <Link to="/assessments" className="text-primary hover:underline">
          Back to assessments
        </Link>
      </div>
    );
  }

  const current = questions[Math.min(index, questions.length - 1)];
  const answeredCount = questions.filter((q) => (answers[String(q.id)] ?? []).length > 0).length;
  const remaining = secondsRemaining(attempt.expires_at, now);
  const locked = finished || submitting;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-semibold">
          Question {index + 1} of {questions.length}
        </h1>
        <div className="flex items-center gap-4 text-sm">
          <span aria-live="polite" className="text-muted-foreground">
            {saveState === 'saving' && 'Saving...'}
            {saveState === 'saved' && 'Saved'}
            {saveState === 'error' && 'Not saved'}
          </span>
          {remaining !== null && (
            <span role="timer" aria-label="Time remaining" className={remaining <= 60 ? 'font-semibold text-destructive' : 'font-semibold'}>
              {formatClock(remaining)}
            </span>
          )}
        </div>
      </div>
      <progress
        className="h-2 w-full overflow-hidden rounded bg-muted [&::-moz-progress-bar]:bg-primary [&::-webkit-progress-bar]:bg-muted [&::-webkit-progress-value]:bg-primary"
        max={questions.length}
        value={answeredCount}
        aria-label="Answered questions"
      />
      <p className="text-xs text-muted-foreground">
        {answeredCount} of {questions.length} answered
      </p>

      <FormMessage message={actionError} />
      {finished && (
        <p className="text-sm">
          <Link to={`/attempts/${attempt.id}/result`} className="text-primary hover:underline">
            View result
          </Link>
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-[1fr_12rem]">
        <Card>
          <CardContent className="pt-6">
            <QuestionView
              key={current.id}
              question={current}
              selected={answers[String(current.id)] ?? []}
              onChange={(ids) => handleChange(current.id, ids)}
              disabled={locked}
            />
            <div className="mt-6 flex justify-between">
              <Button variant="outline" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}>
                Previous
              </Button>
              <Button variant="outline" onClick={() => setIndex((i) => Math.min(questions.length - 1, i + 1))} disabled={index >= questions.length - 1}>
                Next
              </Button>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Navigator</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-5 gap-2" role="group" aria-label="Question navigator">
              {questions.map((q, i) => {
                const answered = (answers[String(q.id)] ?? []).length > 0;
                return (
                  <Button
                    key={q.id}
                    size="sm"
                    variant={i === index ? 'default' : answered ? 'secondary' : 'outline'}
                    className="px-0"
                    onClick={() => setIndex(i)}
                    aria-label={`Go to question ${i + 1}${answered ? ' (answered)' : ''}`}
                    aria-current={i === index ? 'step' : undefined}
                  >
                    {i + 1}
                  </Button>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {confirming ? (
        <div role="alertdialog" aria-labelledby="confirm-title" className="space-y-3 rounded-md border bg-background p-4">
          <h2 id="confirm-title" className="font-semibold">
            Submit your attempt?
          </h2>
          <p className="text-sm text-muted-foreground">
            You have answered {answeredCount} of {questions.length} questions. You cannot change your answers after submitting.
          </p>
          <div className="flex gap-2">
            <Button onClick={() => void submit(false)} disabled={submitting}>
              {submitting ? 'Submitting...' : 'Confirm submit'}
            </Button>
            <Button variant="outline" onClick={() => setConfirming(false)} disabled={submitting}>
              Keep working
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex justify-end">
          <Button onClick={() => setConfirming(true)} disabled={locked}>
            Submit attempt
          </Button>
        </div>
      )}
    </div>
  );
}
