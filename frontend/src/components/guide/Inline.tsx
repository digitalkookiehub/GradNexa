import { inlineRuns } from '@/lib/guide';

/** Renders text with **bold** UI names. Plain text only: no HTML is ever interpreted. */
export function Inline({ text }: { text: string }) {
  return (
    <>
      {inlineRuns(text).map((run, i) =>
        run.bold ? (
          <strong key={i} className="font-semibold text-foreground">
            {run.text}
          </strong>
        ) : (
          <span key={i}>{run.text}</span>
        ),
      )}
    </>
  );
}
