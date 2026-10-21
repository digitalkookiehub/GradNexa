import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatScore } from '@/lib/readiness';
import { formatDelta } from '@/lib/roadmap';
import type { ReassessResult } from '@/types';

interface ReassessPanelProps {
  result: ReassessResult;
}

function describe(overall: number | null, level: string | null): string {
  if (overall === null) return 'Not enough evidence';
  return `${formatScore(overall)}${level ? ` (${level})` : ''}`;
}

export function ReassessPanel({ result }: ReassessPanelProps) {
  const { baseline, current } = result;
  return (
    <Card aria-label="Reassessment comparison">
      <CardHeader>
        <CardTitle className="text-lg">Readiness comparison</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {result.rule_version_changed && (
          <div role="note" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-amber-900" data-testid="rule-version-note">
            The readiness rule changed from version {baseline.rule_version} to version {current.rule_version}, so these scores may not be directly comparable.
          </div>
        )}
        <dl className="grid gap-2 sm:grid-cols-3">
          <div>
            <dt className="text-muted-foreground">Baseline</dt>
            <dd data-testid="reassess-baseline">{describe(baseline.overall, baseline.level)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Now</dt>
            <dd data-testid="reassess-current">{describe(current.overall, current.level)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Overall change</dt>
            <dd data-testid="reassess-delta">{formatDelta(result.overall_delta)}</dd>
          </div>
        </dl>
        {result.skill_changes.length === 0 ? (
          <p className="text-muted-foreground">No per-skill changes to show.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="py-2 pr-4 font-medium">Skill</th>
                  <th className="py-2 pr-4 font-medium">Before</th>
                  <th className="py-2 pr-4 font-medium">After</th>
                  <th className="py-2 font-medium">Change</th>
                </tr>
              </thead>
              <tbody>
                {result.skill_changes.map((c) => (
                  <tr key={c.skill_id} className="border-b last:border-0">
                    <td className="py-2 pr-4">{c.skill_name}</td>
                    <td className="py-2 pr-4">{c.before === null ? 'No evidence' : formatScore(c.before)}</td>
                    <td className="py-2 pr-4">{c.after === null ? 'No evidence' : formatScore(c.after)}</td>
                    <td className="py-2">{formatDelta(c.delta)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
