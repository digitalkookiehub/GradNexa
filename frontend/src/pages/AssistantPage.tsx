import { useEffect, useRef, useState } from 'react';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { AnswerCard } from '@/components/assistant/AnswerCard';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { getErrorMessage, getErrorStatus } from '@/lib/errors';
import { ASSISTANT_EXAMPLES, NO_LLM_NOTE } from '@/lib/knowledge';
import { assistantService } from '@/services/assistantService';
import { jobService } from '@/services/jobService';
import { roadmapService } from '@/services/roadmapService';
import type { ConversationEntry } from '@/types/assistant';
import type { JobListItem } from '@/types/jobs';
import type { ExplorerRole } from '@/types/roadmap';

const QUESTION_MAX = 1000;

export function AssistantPage() {
  const [question, setQuestion] = useState('');
  const [roles, setRoles] = useState<ExplorerRole[]>([]);
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [roleId, setRoleId] = useState('');
  const [jobId, setJobId] = useState('');
  const [pickerError, setPickerError] = useState<string | null>(null);
  const [entries, setEntries] = useState<ConversationEntry[]>([]);
  const [inputError, setInputError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const nextId = useRef(1);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([roadmapService.listRoles(), jobService.list()])
      .then(([r, j]) => {
        if (cancelled) return;
        // Goal roles first.
        setRoles([...r].sort((a, b) => Number(b.is_goal) - Number(a.is_goal) || a.name.localeCompare(b.name)));
        setJobs(j);
      })
      .catch((err: unknown) => {
        if (!cancelled) setPickerError(getErrorMessage(err, 'Could not load the role and job pickers. You can still ask a question.'));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const ask = async (): Promise<void> => {
    const q = question.trim();
    if (!q) {
      setInputError('Enter a question.');
      return;
    }
    if (q.length > QUESTION_MAX) {
      setInputError(`Questions can be at most ${QUESTION_MAX} characters.`);
      return;
    }
    setInputError(null);
    const id = nextId.current;
    nextId.current += 1;
    setEntries((prev) => [...prev, { id, kind: 'pending', question: q }]);
    setQuestion('');
    setBusy(true);
    try {
      const answer = await assistantService.query({
        question: q,
        ...(roleId !== '' ? { role_id: Number(roleId) } : {}),
        ...(jobId !== '' ? { job_id: Number(jobId) } : {}),
      });
      setEntries((prev) => prev.map((e) => (e.id === id ? { id, kind: 'answer', question: q, answer } : e)));
    } catch (err) {
      const status = getErrorStatus(err);
      const base = getErrorMessage(err, 'The assistant could not answer. Please try again.');
      const message = status === 409 ? `${base} Complete the missing step and ask again.` : base;
      setEntries((prev) => prev.map((e) => (e.id === id ? { id, kind: 'error', question: q, message } : e)));
    } finally {
      setBusy(false);
    }
  };

  const fillExample = (text: string): void => {
    setQuestion(text);
    setInputError(null);
    inputRef.current?.focus();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Assistant</h1>
        <p className="mt-1 rounded-md border bg-muted/40 px-3 py-2 text-sm" data-testid="no-llm-note">
          {NO_LLM_NOTE}
        </p>
      </div>

      <section aria-label="Conversation" className="space-y-4">
        {entries.length === 0 && <p className="text-muted-foreground">Ask a question to get started. Try one of the examples below.</p>}
        {entries.map((e) => (
          <div key={e.id} className="space-y-2">
            <p className="ml-auto max-w-[85%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">{e.question}</p>
            {e.kind === 'pending' && (
              <p role="status" className="text-sm text-muted-foreground">
                Looking through your records and approved documents...
              </p>
            )}
            {e.kind === 'error' && <FormMessage message={e.message} />}
            {e.kind === 'answer' && <AnswerCard answer={e.answer} />}
          </div>
        ))}
      </section>

      <form
        className="space-y-4 rounded-md border bg-background p-4"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          void ask();
        }}
      >
        <div className="space-y-2">
          <Label htmlFor="assistant-question">Your question</Label>
          <textarea
            id="assistant-question"
            ref={inputRef}
            rows={3}
            maxLength={QUESTION_MAX}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={busy}
            aria-invalid={!!inputError}
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{inputError ? <span className="text-destructive">{inputError}</span> : ''}</span>
            <span data-testid="char-count">
              {question.length}/{QUESTION_MAX}
            </span>
          </div>
        </div>

        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Ask about</p>
          <ul className="flex flex-wrap gap-2" aria-label="Example questions">
            {ASSISTANT_EXAMPLES.map((ex) => (
              <li key={ex}>
                <button type="button" onClick={() => fillExample(ex)} className="rounded-full border px-3 py-1 text-xs hover:bg-accent" disabled={busy}>
                  {ex}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <FormMessage message={pickerError} />
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="assistant-role">Career role (optional)</Label>
            <select id="assistant-role" className={SELECT_CLASS} value={roleId} onChange={(e) => setRoleId(e.target.value)} disabled={busy}>
              <option value="">No specific role</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                  {r.is_goal ? ' (your goal)' : ''}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="assistant-job">Job (optional)</Label>
            <select id="assistant-job" className={SELECT_CLASS} value={jobId} onChange={(e) => setJobId(e.target.value)} disabled={busy}>
              <option value="">No specific job</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title} - {j.company_name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex gap-2">
          <Button type="submit" disabled={busy}>
            {busy ? 'Asking...' : 'Ask'}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={busy || entries.length === 0}
            onClick={() => {
              setEntries([]);
              setInputError(null);
            }}
          >
            Clear conversation
          </Button>
        </div>
      </form>
    </div>
  );
}
