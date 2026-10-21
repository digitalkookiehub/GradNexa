import { useEffect, useMemo, useRef } from 'react';
import { buildSegments, rangesFromExtracted } from '@/lib/resume';
import type { Extracted } from '@/types/resume';

interface SourceTextProps {
  text: string;
  extracted: Extracted;
  activeGroup: string | null;
}

/** Renders the resume text with every extracted span wrapped in a <mark>. */
export function SourceText({ text, extracted, activeGroup }: SourceTextProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const segments = useMemo(() => buildSegments(text, rangesFromExtracted(extracted)), [text, extracted]);

  useEffect(() => {
    if (!activeGroup) return;
    const first = containerRef.current?.querySelector<HTMLElement>('mark[data-active="true"]');
    if (first && typeof first.scrollIntoView === 'function') first.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [activeGroup]);

  return (
    <div ref={containerRef} className="max-h-[32rem] overflow-y-auto whitespace-pre-wrap rounded-md border bg-background p-3 text-sm" data-testid="source-text">
      {segments.map((seg) => {
        if (seg.groups.length === 0) return <span key={seg.start}>{seg.text}</span>;
        const active = activeGroup !== null && seg.groups.includes(activeGroup);
        return (
          <mark
            key={seg.start}
            data-active={active ? 'true' : 'false'}
            data-groups={seg.groups.join(' ')}
            className={active ? 'rounded bg-amber-400 px-0.5 text-foreground ring-2 ring-amber-600' : 'rounded bg-yellow-100 px-0.5 text-foreground'}
          >
            {seg.text}
          </mark>
        );
      })}
    </div>
  );
}
