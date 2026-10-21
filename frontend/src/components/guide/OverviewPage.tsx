import { ArrowDown, ArrowRight } from 'lucide-react';
import type { Guide } from '@/types/guide';

interface OverviewPageProps {
  guide: Guide;
  onGo: (id: string) => void;
}

export function OverviewPage({ guide, onGo }: OverviewPageProps) {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">How the application works</h1>
        {guide.tagline && <p className="text-muted-foreground">{guide.tagline}</p>}
        <p className="text-sm">
          Use the list on the left to open a step-by-step procedure. Start at the top of a section and work down: each procedure ends with a
          link to the next one.
        </p>
      </header>

      <section aria-labelledby="overview-flow" className="space-y-3">
        <h2 id="overview-flow" className="text-lg font-semibold">
          The whole flow
        </h2>
        <ol className="flex flex-col gap-2">
          {guide.overview.map((item, i) => (
            <li key={item.id} className="flex flex-col gap-2">
              <button
                type="button"
                onClick={() => onGo(item.goto)}
                className="flex items-start gap-3 rounded-lg border bg-background p-3 text-left shadow-sm transition hover:border-primary hover:bg-accent"
              >
                <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                  {i + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold">{item.title}</span>
                  <span className="block text-sm text-muted-foreground">{item.summary}</span>
                </span>
                <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              </button>
              {i < guide.overview.length - 1 && (
                <span className="flex justify-center text-muted-foreground" aria-hidden="true">
                  <ArrowDown className="h-5 w-5" />
                </span>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="overview-roles" className="space-y-3">
        <h2 id="overview-roles" className="text-lg font-semibold">
          Who does what
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr>
                <th className="border bg-muted px-3 py-2 font-semibold">Role</th>
                <th className="border bg-muted px-3 py-2 font-semibold">What they do</th>
                <th className="border bg-muted px-3 py-2 font-semibold">Lands on</th>
              </tr>
            </thead>
            <tbody>
              {guide.roles.map((r) => (
                <tr key={r.role}>
                  <td className="border px-3 py-2 align-top font-medium">{r.role}</td>
                  <td className="border px-3 py-2 align-top">{r.does}</td>
                  <td className="border px-3 py-2 align-top">{r.lands}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="overview-principles" className="space-y-3">
        <h2 id="overview-principles" className="text-lg font-semibold">
          Rules the application always follows
        </h2>
        <ul className="grid gap-2 text-sm sm:grid-cols-2">
          {guide.principles.map((p) => (
            <li key={p} className="rounded-md border bg-background p-3">
              {p}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
