import { CitationList } from '@/components/knowledge/CitationList';
import { Card, CardContent } from '@/components/ui/card';
import type { AssistantAnswer } from '@/types/assistant';

interface AnswerCardProps {
  answer: AssistantAnswer;
}

/** All text is rendered as plain text; answers may contain markup-like characters. */
export function AnswerCard({ answer }: AnswerCardProps) {
  return (
    <Card>
      <CardContent className="space-y-4 p-4 text-sm">
        {answer.insufficient_evidence && (
          <p role="status" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-amber-900">
            There is not enough approved evidence to answer this fully.
          </p>
        )}

        {answer.answer_sections.map((s, i) => (
          <section key={`${s.heading}-${i}`} className="space-y-2">
            {s.heading && <h3 className="font-semibold">{s.heading}</h3>}
            {s.text && <p className="whitespace-pre-wrap break-words">{s.text}</p>}
            {s.facts.length > 0 && (
              <dl className="grid gap-x-6 gap-y-1 sm:grid-cols-2">
                {s.facts.map((f, j) => (
                  <div key={`${f.label}-${j}`} className="flex gap-2">
                    <dt className="text-muted-foreground">{f.label}:</dt>
                    <dd className="break-words">{f.value}</dd>
                  </div>
                ))}
              </dl>
            )}
          </section>
        ))}

        {answer.tools_used.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">Data sources used</p>
            <ul className="flex flex-wrap gap-2" aria-label="Tools used">
              {answer.tools_used.map((t) => (
                <li key={t} className="rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground">
                  {t}
                </li>
              ))}
            </ul>
          </div>
        )}

        {answer.citations.length > 0 && (
          <div className="space-y-1">
            <h4 className="text-xs font-medium text-muted-foreground">Citations</h4>
            <CitationList citations={answer.citations} />
          </div>
        )}

        {answer.notes.length > 0 && (
          <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground" aria-label="Notes">
            {answer.notes.map((n, i) => (
              <li key={`${n}-${i}`}>{n}</li>
            ))}
          </ul>
        )}

        <p className="text-xs text-muted-foreground" data-testid="llm-used">
          Language model used: {answer.llm_used ? 'Yes' : 'No'}
          {answer.intent ? ` | Topic: ${answer.intent}` : ''}
        </p>
      </CardContent>
    </Card>
  );
}
