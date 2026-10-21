import { CheckCircle2, ChevronLeft, ChevronRight, CircleHelp, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Inline } from './Inline';
import { isOpenableByAdmin } from '@/lib/guide';
import type { GuideProcedure } from '@/types/guide';

interface ProcedureViewProps {
  procedure: GuideProcedure;
  done: Set<number>;
  onToggleStep: (index: number) => void;
  prev: { id: string; title: string } | null;
  next: { id: string; title: string } | null;
  onGo: (id: string) => void;
}

export function ProcedureView({ procedure, done, onToggleStep, prev, next, onGo }: ProcedureViewProps) {
  const total = procedure.steps.length;
  const doneCount = [...done].filter((i) => i < total).length;
  return (
    <article className="space-y-8" aria-labelledby={`proc-${procedure.id}`}>
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">For: {procedure.audience}</p>
        <h1 id={`proc-${procedure.id}`} className="text-2xl font-semibold">
          {procedure.title}
        </h1>
        <p className="text-muted-foreground">{procedure.summary}</p>
        {procedure.path && (
          <p className="flex flex-wrap items-center gap-2 text-sm">
            <span>Page:</span>
            <code className="rounded bg-muted px-1.5 py-0.5">{procedure.path}</code>
            {isOpenableByAdmin(procedure.path) && (
              <Link to={procedure.path} className="inline-flex items-center gap-1 text-primary underline">
                Open this page <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            )}
          </p>
        )}
      </header>

      {procedure.before.length > 0 && (
        <section aria-labelledby={`before-${procedure.id}`} className="rounded-lg border bg-background p-4">
          <h2 id={`before-${procedure.id}`} className="mb-2 font-semibold">
            Before you start
          </h2>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {procedure.before.map((b) => (
              <li key={b}>
                <Inline text={b} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {total > 0 && (
        <section aria-labelledby={`steps-${procedure.id}`} className="space-y-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id={`steps-${procedure.id}`} className="text-lg font-semibold">
              Steps
            </h2>
            <p className="text-xs text-muted-foreground" aria-live="polite">
              {doneCount} of {total} ticked off (just for you; not saved)
            </p>
          </div>
          <ol className="space-y-3">
            {procedure.steps.map((step, i) => {
              const isDone = done.has(i);
              return (
                <li key={`${i}-${step.do}`} className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => onToggleStep(i)}
                    aria-pressed={isDone}
                    aria-label={`Mark step ${i + 1} ${isDone ? 'not done' : 'done'}`}
                    className={
                      isDone
                        ? 'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-green-600 text-white'
                        : 'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground'
                    }
                  >
                    {isDone ? <CheckCircle2 className="h-5 w-5" aria-hidden="true" /> : i + 1}
                  </button>
                  <div className={isDone ? 'min-w-0 flex-1 space-y-1 opacity-60' : 'min-w-0 flex-1 space-y-1'}>
                    <p className="leading-7">
                      <span className="sr-only">Step {i + 1}: </span>
                      <Inline text={step.do} />
                    </p>
                    {step.detail && (
                      <p className="text-sm text-muted-foreground">
                        <Inline text={step.detail} />
                      </p>
                    )}
                    {step.expect && (
                      <p className="rounded-md border border-green-300 bg-green-50 px-3 py-2 text-sm text-green-950 dark:border-green-800 dark:bg-green-950/40 dark:text-green-100">
                        <span className="font-semibold">You should see: </span>
                        <Inline text={step.expect} />
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {procedure.tables.length > 0 && (
        <section aria-label="Samples and reference tables" className="space-y-6">
          {procedure.tables.map((table) => (
            <figure key={table.title} className="space-y-2">
              <figcaption className="font-semibold">{table.title}</figcaption>
              <div className="overflow-x-auto rounded-md border">
                <table className="w-full border-collapse text-left text-sm">
                  <thead>
                    <tr>
                      {table.columns.map((c) => (
                        <th key={c} scope="col" className="border-b bg-muted px-3 py-2 font-semibold">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.map((row, r) => (
                      <tr key={`${r}-${row[0]}`} className="odd:bg-background even:bg-muted/30">
                        {row.map((cell, c) => (
                          <td key={`${r}-${c}`} className="border-t px-3 py-2 align-top">
                            <Inline text={cell} />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {table.caption && <p className="text-xs text-muted-foreground">{table.caption}</p>}
            </figure>
          ))}
        </section>
      )}

      {procedure.terms.length > 0 && (
        <dl className="space-y-3">
          {procedure.terms.map((t) => (
            <div key={t.term} className="rounded-lg border bg-background p-3">
              <dt className="font-semibold">{t.term}</dt>
              <dd className="text-sm text-muted-foreground">
                <Inline text={t.meaning} />
              </dd>
            </div>
          ))}
        </dl>
      )}

      {procedure.note && <p className="rounded-md bg-muted p-3 text-sm text-muted-foreground">{procedure.note}</p>}

      {procedure.result.length > 0 && (
        <section aria-labelledby={`result-${procedure.id}`}>
          <h2 id={`result-${procedure.id}`} className="mb-2 text-lg font-semibold">
            When you are done
          </h2>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {procedure.result.map((r) => (
              <li key={r}>
                <Inline text={r} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {procedure.problems.length > 0 && (
        <section aria-labelledby={`problems-${procedure.id}`} className="space-y-2">
          <h2 id={`problems-${procedure.id}`} className="flex items-center gap-2 text-lg font-semibold">
            <CircleHelp className="h-5 w-5" aria-hidden="true" /> If something goes wrong
          </h2>
          <ul className="space-y-2">
            {procedure.problems.map((p) => (
              <li
                key={p.problem}
                className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-100"
              >
                <p className="font-semibold">
                  <Inline text={p.problem} />
                </p>
                <p>
                  <Inline text={p.fix} />
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <nav aria-label="Previous and next" className="flex flex-wrap justify-between gap-3 border-t pt-4">
        {prev ? (
          <button type="button" className="inline-flex items-center gap-1 rounded-md border px-3 py-2 text-sm hover:bg-accent" onClick={() => onGo(prev.id)}>
            <ChevronLeft className="h-4 w-4" aria-hidden="true" /> Previous: {prev.title}
          </button>
        ) : (
          <span />
        )}
        {next && (
          <button type="button" className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground hover:opacity-90" onClick={() => onGo(next.id)}>
            Next: {next.title} <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </nav>
    </article>
  );
}
