import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { GuideContent } from '@/components/guide/GuideContent';
import { OverviewPage } from '@/components/guide/OverviewPage';
import { ProcedureView } from '@/components/guide/ProcedureView';
import { Button } from '@/components/ui/button';
import { getErrorMessage } from '@/lib/errors';
import { allProcedures, extractSections, neighbours, OVERVIEW_ID, resolvePage, WRITTEN_ID } from '@/lib/guide';
import { guideService } from '@/services/guideService';
import type { Guide } from '@/types/guide';

const ITEM_BASE = 'block w-full rounded-md px-3 py-1.5 text-left text-sm';
const ITEM_ACTIVE = `${ITEM_BASE} bg-primary font-medium text-primary-foreground`;
const ITEM_IDLE = `${ITEM_BASE} hover:bg-accent`;

export function GuidePage() {
  const [params, setParams] = useSearchParams();
  const [guide, setGuide] = useState<Guide | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [doneByPage, setDoneByPage] = useState<Record<string, Set<number>>>({});

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    guideService
      .get()
      .then((g) => {
        if (cancelled) return;
        setGuide(g);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load the user guide.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const procedures = useMemo(() => (guide ? allProcedures(guide) : []), [guide]);
  const sections = useMemo(() => (guide ? extractSections(guide.markdown) : []), [guide]);
  const page = guide ? resolvePage(guide, params.get('p')) : OVERVIEW_ID;

  const go = (id: string): void => {
    setParams({ p: id });
    setMenuOpen(false);
    window.scrollTo({ top: 0 });
  };

  const toggleStep = (index: number): void => {
    setDoneByPage((prev) => {
      const next = new Set(prev[page] ?? []);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return { ...prev, [page]: next };
    });
  };

  if (loading) return <p role="status">Loading the user guide...</p>;
  if (error || !guide) {
    return (
      <div className="space-y-3">
        <FormMessage message={error ?? 'The user guide is empty.'} />
        <Button variant="outline" onClick={() => setAttempt((n) => n + 1)}>
          Try again
        </Button>
      </div>
    );
  }

  const titleOf = (id: string): string => {
    if (id === OVERVIEW_ID) return 'How the application works';
    if (id === WRITTEN_ID) return 'Written guide (full text)';
    return procedures.find((p) => p.id === id)?.title ?? id;
  };
  const { prev, next } = neighbours(guide, page);
  const procedure = procedures.find((p) => p.id === page);
  const group = guide.groups.find((g) => g.procedures.some((p) => p.id === page));

  const sidebar = (
    <nav aria-label="Guide contents" className="space-y-5">
      <button type="button" className={page === OVERVIEW_ID ? ITEM_ACTIVE : ITEM_IDLE} aria-current={page === OVERVIEW_ID ? 'page' : undefined} onClick={() => go(OVERVIEW_ID)}>
        How the application works
      </button>
      {guide.groups.map((group) => (
        <div key={group.id}>
          <h2 className="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{group.title}</h2>
          <ul className="space-y-0.5">
            {group.procedures.map((p) => (
              <li key={p.id}>
                <button type="button" className={page === p.id ? ITEM_ACTIVE : ITEM_IDLE} aria-current={page === p.id ? 'page' : undefined} onClick={() => go(p.id)}>
                  {p.title}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <div>
        <h2 className="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Full text</h2>
        <button type="button" className={page === WRITTEN_ID ? ITEM_ACTIVE : ITEM_IDLE} aria-current={page === WRITTEN_ID ? 'page' : undefined} onClick={() => go(WRITTEN_ID)}>
          Written guide (full text)
        </button>
      </div>
    </nav>
  );

  return (
    <div className="grid gap-6 md:grid-cols-[17rem_minmax(0,1fr)]">
      <aside className="md:sticky md:top-4 md:max-h-[calc(100vh-2rem)] md:self-start md:overflow-y-auto md:pr-2">
        <button
          type="button"
          className="mb-2 w-full rounded-md border bg-background px-3 py-2 text-left text-sm font-medium md:hidden"
          aria-expanded={menuOpen}
          aria-controls="guide-sidebar"
          onClick={() => setMenuOpen((o) => !o)}
        >
          {menuOpen ? 'Hide contents' : `Contents: ${titleOf(page)}`}
        </button>
        <div id="guide-sidebar" className={menuOpen ? 'block' : 'hidden md:block'}>
          {sidebar}
        </div>
      </aside>

      <section className="min-w-0 rounded-lg border bg-background p-5 sm:p-6" aria-live="polite">
        {page === OVERVIEW_ID && <OverviewPage guide={guide} onGo={go} />}
        {page === WRITTEN_ID && (
          <div className="space-y-6">
            {sections.length > 0 && (
              <nav aria-label="Written guide sections" className="rounded-md border p-4">
                <ul className="grid gap-1 text-sm sm:grid-cols-2">
                  {sections.map((s) => (
                    <li key={s.id}>
                      <button type="button" className="text-left text-primary hover:underline" onClick={() => document.getElementById(s.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>
                        {s.title}
                      </button>
                    </li>
                  ))}
                </ul>
              </nav>
            )}
            <GuideContent markdown={guide.markdown} />
          </div>
        )}
        {procedure && group?.intro && (
          <p className="mb-6 rounded-md bg-muted p-3 text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">{group.title}: </span>
            {group.intro}
          </p>
        )}
        {procedure && (
          <ProcedureView
            key={procedure.id}
            procedure={procedure}
            done={doneByPage[procedure.id] ?? new Set<number>()}
            onToggleStep={toggleStep}
            prev={prev ? { id: prev, title: titleOf(prev) } : null}
            next={next ? { id: next, title: titleOf(next) } : null}
            onGo={go}
          />
        )}
      </section>
    </div>
  );
}
