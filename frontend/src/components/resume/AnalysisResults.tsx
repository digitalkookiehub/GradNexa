import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { blockGroup, formatMatch, skillGroup } from '@/lib/resume';
import type { Block, ResumeAnalysis } from '@/types/resume';

interface AnalysisResultsProps {
  analysis: ResumeAnalysis;
  activeGroup: string | null;
  onSelect: (group: string | null) => void;
}

const BLOCK_SECTIONS = [
  { kind: 'education', title: 'Education' },
  { kind: 'projects', title: 'Projects' },
  { kind: 'experience', title: 'Experience' },
  { kind: 'certifications', title: 'Certifications' },
] as const;

function BlockList({ kind, title, blocks, activeGroup, onSelect }: { kind: string; title: string; blocks: Block[]; activeGroup: string | null; onSelect: (g: string | null) => void }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {blocks.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing was found under {title.toLowerCase()} in this resume.</p>
        ) : (
          <ul className="space-y-2" aria-label={title}>
            {blocks.map((b, i) => {
              const group = blockGroup(kind, i);
              const active = activeGroup === group;
              return (
                <li key={group}>
                  <button
                    type="button"
                    aria-pressed={active}
                    onClick={() => onSelect(active ? null : group)}
                    className={`w-full whitespace-pre-wrap rounded-md border px-3 py-2 text-left text-sm ${active ? 'border-amber-600 bg-amber-50' : 'hover:bg-muted'}`}
                  >
                    {b.text}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function AnalysisResults({ analysis, activeGroup, onSelect }: AnalysisResultsProps) {
  const { extracted, role_match: roleMatch, jd_match: jdMatch } = analysis;

  return (
    <div className="space-y-4">
      {analysis.notes.length > 0 && (
        <div className="space-y-2">
          {analysis.notes.map((n, i) => (
            <div key={i} role="alert" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              {n}
            </div>
          ))}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Sections found</CardTitle>
        </CardHeader>
        <CardContent>
          {extracted.sections_found.length === 0 ? (
            <p className="text-sm text-muted-foreground">No standard section headings were detected.</p>
          ) : (
            <ul className="flex flex-wrap gap-2" aria-label="Sections found">
              {extracted.sections_found.map((s) => (
                <li key={s} className="rounded-full border px-3 py-1 text-sm">
                  {s}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Skills found</CardTitle>
        </CardHeader>
        <CardContent>
          {extracted.skills.length === 0 ? (
            <p className="text-sm text-muted-foreground">None of your college&apos;s configured skills were found as keywords in this resume.</p>
          ) : (
            <ul className="flex flex-wrap gap-2" aria-label="Skills found">
              {extracted.skills.map((s) => {
                const group = skillGroup(s.skill_id);
                const active = activeGroup === group;
                return (
                  <li key={s.skill_id}>
                    <button
                      type="button"
                      aria-pressed={active}
                      onClick={() => onSelect(active ? null : group)}
                      className={`rounded-full border px-3 py-1 text-sm ${active ? 'border-amber-600 bg-amber-100 font-medium' : 'hover:bg-muted'}`}
                    >
                      {s.skill_name} <span className="text-xs text-muted-foreground">x{s.spans.length}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          <p className="mt-3 text-xs text-muted-foreground">Select a skill to highlight where it appears in the source text.</p>
        </CardContent>
      </Card>

      {roleMatch && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Role match{analysis.role_name ? `: ${analysis.role_name}` : ''}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-2xl font-semibold" data-testid="role-match-percent">
              {formatMatch(roleMatch.match_percent)}
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <h4 className="mb-1 text-sm font-semibold">Found in resume</h4>
                {roleMatch.found.length === 0 ? (
                  <p className="text-sm text-muted-foreground">None of this role&apos;s skills were found.</p>
                ) : (
                  <ul className="space-y-1 text-sm" aria-label="Role skills found">
                    {roleMatch.found.map((s) => (
                      <li key={s.skill_id}>{s.skill_name}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <h4 className="mb-1 text-sm font-semibold">Missing from resume</h4>
                {roleMatch.missing.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No role skills are missing.</p>
                ) : (
                  <ul className="space-y-1 text-sm" aria-label="Role skills missing">
                    {roleMatch.missing.map((s) => (
                      <li key={s.skill_id}>{s.skill_name}</li>
                    ))}
                  </ul>
                )}
                {analysis.role_id !== null && roleMatch.missing.length > 0 && (
                  <Link to={`/careers/${analysis.role_id}`} className="mt-2 inline-block text-sm text-primary hover:underline">
                    See this role&apos;s skills and how to build them
                  </Link>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {jdMatch && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Job description match</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-2xl font-semibold" data-testid="jd-match-percent">
              {formatMatch(jdMatch.match_percent)}
            </p>
            {jdMatch.skills_in_jd.length === 0 ? (
              <p className="text-sm text-muted-foreground">No configured skills were detected in the job description.</p>
            ) : (
              <ul className="space-y-1 text-sm" aria-label="Skills in job description">
                {jdMatch.skills_in_jd.map((s) => (
                  <li key={s.skill_id} className="flex items-center justify-between gap-2">
                    <span>{s.skill_name}</span>
                    <span className={s.in_resume ? 'text-green-700' : 'text-destructive'}>{s.in_resume ? 'In resume' : 'Not in resume'}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      {BLOCK_SECTIONS.map((s) => (
        <BlockList key={s.kind} kind={s.kind} title={s.title} blocks={extracted[s.kind]} activeGroup={activeGroup} onSelect={onSelect} />
      ))}
    </div>
  );
}
