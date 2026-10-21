import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { SHORT_DISCLAIMER, countWords } from '@/lib/interview';
import { interviewService } from '@/services/interviewService';
import type { Interview, InterviewAnswerInput } from '@/types';

const SAVE_DEBOUNCE_MS = 800;

type SaveState = 'idle' | 'saving' | 'saved' | 'error';
type TextMap = Record<number, string>;

function isConflict(err: unknown): boolean {
  return axios.isAxiosError(err) && err.response?.status === 409;
}

function toPayload(texts: TextMap): InterviewAnswerInput[] {
  return Object.entries(texts).map(([id, answer_text]) => ({ answer_id: Number(id), answer_text }));
}

export function InterviewSessionPage() {
  const { id } = useParams<{ id: string }>();
  const interviewId = Number(id);
  const navigate = useNavigate();

  const [interview, setInterview] = useState<Interview | null>(null);
  const [texts, setTexts] = useState<TextMap>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [index, setIndex] = useState(0);
  const [confirming, setConfirming] = useState(false);
  const [finishing, setFinishing] = useState(false);

  const textsRef = useRef<TextMap>({});
  const dirtyRef = useRef(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finishingRef = useRef(false);

  useEffect(() => {
    if (!Number.isInteger(interviewId)) return;
    let cancelled = false;
    interviewService
      .get(interviewId)
      .then((iv) => {
        if (cancelled) return;
        const initial: TextMap = {};
        iv.questions.forEach((q) => {
          initial[q.answer_id] = q.answer_text ?? '';
        });
        textsRef.current = initial;
        setTexts(initial);
        setInterview(iv);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(getErrorMessage(err, 'Could not load the interview.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [interviewId]);

  const clearSaveTimer = useCallback((): void => {
    if (saveTimer.current) {
      clearTimeout(saveTimer.current);
      saveTimer.current = null;
    }
  }, []);

  useEffect(() => clearSaveTimer, [clearSaveTimer]);

  const flushSave = useCallback(async (): Promise<boolean> => {
    clearSaveTimer();
    if (!dirtyRef.current) return true;
    dirtyRef.current = false;
    setSaveState('saving');
    try {
      await interviewService.saveAnswers(interviewId, toPayload(textsRef.current));
      setSaveState('saved');
      return true;
    } catch (err) {
      dirtyRef.current = true;
      setSaveState('error');
      if (isConflict(err)) {
        navigate(`/interview/${interviewId}/result`, { replace: true });
      } else {
        setActionError(getErrorMessage(err, 'Could not save your answers. Your latest changes are not saved yet.'));
      }
      return false;
    }
  }, [interviewId, clearSaveTimer, navigate]);

  const finish = async (): Promise<void> => {
    if (finishingRef.current) return;
    finishingRef.current = true;
    setFinishing(true);
    setActionError(null);
    try {
      if (!(await flushSave())) {
        setConfirming(false);
        return;
      }
      await interviewService.finish(interviewId);
      navigate(`/interview/${interviewId}/result`, { replace: true });
    } catch (err) {
      if (isConflict(err)) {
        navigate(`/interview/${interviewId}/result`, { replace: true });
        return;
      }
      setActionError(getErrorMessage(err, 'Could not finish the interview.'));
      setConfirming(false);
    } finally {
      finishingRef.current = false;
      setFinishing(false);
    }
  };

  const handleChange = (answerId: number, value: string): void => {
    const next: TextMap = { ...textsRef.current, [answerId]: value };
    textsRef.current = next;
    dirtyRef.current = true;
    setTexts(next);
    setSaveState('idle');
    clearSaveTimer();
    saveTimer.current = setTimeout(() => {
      void flushSave();
    }, SAVE_DEBOUNCE_MS);
  };

  if (!Number.isInteger(interviewId)) return <FormMessage message="Invalid interview." />;
  if (loading) {
    return (
      <p role="status" className="py-12 text-center text-muted-foreground">
        Loading interview...
      </p>
    );
  }
  if (loadError || !interview) {
    return (
      <div className="mx-auto max-w-md space-y-4 py-12">
        <FormMessage message={loadError ?? 'Could not load the interview.'} />
        <Link to="/interview" className="text-primary hover:underline">
          Back to interviews
        </Link>
      </div>
    );
  }
  if (interview.status === 'COMPLETED') return <Navigate to={`/interview/${interview.id}/result`} replace />;

  const questions = interview.questions;
  if (questions.length === 0) {
    return (
      <div className="mx-auto max-w-md space-y-4 py-12">
        <FormMessage message="This interview has no questions." />
        <Link to="/interview" className="text-primary hover:underline">
          Back to interviews
        </Link>
      </div>
    );
  }

  const current = questions[Math.min(index, questions.length - 1)];
  const text = texts[current.answer_id] ?? '';
  const words = countWords(text);
  const answeredCount = questions.filter((q) => (texts[q.answer_id] ?? '').trim() !== '').length;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-semibold">
          {interview.role_name}: question {index + 1} of {questions.length}
        </h1>
        <span aria-live="polite" className="text-sm text-muted-foreground">
          {saveState === 'saving' && 'Saving...'}
          {saveState === 'saved' && 'Saved'}
          {saveState === 'error' && 'Not saved'}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        {answeredCount} of {questions.length} answered. {SHORT_DISCLAIMER}
      </p>

      <FormMessage message={actionError} />

      <div className="grid gap-4 md:grid-cols-[1fr_12rem]">
        <Card>
          <CardContent className="space-y-3 pt-6">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground" data-testid="competency">
              {current.competency}
            </p>
            <Label htmlFor="answer-text" className="text-base font-medium">
              {current.prompt}
            </Label>
            <textarea
              key={current.answer_id}
              id="answer-text"
              rows={9}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
              value={text}
              onChange={(e) => handleChange(current.answer_id, e.target.value)}
              disabled={finishing}
              aria-describedby="word-count"
            />
            <p id="word-count" className="text-sm text-muted-foreground" data-testid="word-count">
              {words} {words === 1 ? 'word' : 'words'}
              {current.min_words > 0 && ` (aim for at least ${current.min_words}; shorter answers are marked too short)`}
            </p>
            <div className="flex justify-between">
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
                const answered = (texts[q.answer_id] ?? '').trim() !== '';
                return (
                  <Button
                    key={q.answer_id}
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
        <ConfirmPanel
          title="Finish this interview?"
          message={`You have answered ${answeredCount} of ${questions.length} questions. You cannot change your answers after finishing.`}
          confirmLabel="Confirm finish"
          busy={finishing}
          onConfirm={() => void finish()}
          onCancel={() => setConfirming(false)}
        />
      ) : (
        <div className="flex justify-end">
          <Button onClick={() => setConfirming(true)} disabled={finishing}>
            Finish interview
          </Button>
        </div>
      )}
    </div>
  );
}
