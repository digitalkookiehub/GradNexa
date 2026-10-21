import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { AnalysisResults } from '@/components/resume/AnalysisResults';
import { SourceText } from '@/components/resume/SourceText';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/lib/assessment';
import { getErrorMessage, getErrorStatus } from '@/lib/errors';
import { formatMatch } from '@/lib/resume';
import { resumeService } from '@/services/resumeService';
import type { AnalysisSummary, ResumeAnalysis } from '@/types/resume';

export function ResumeAnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const resumeId = Number(id);
  const validId = Number.isInteger(resumeId) && resumeId > 0;

  const [analysis, setAnalysis] = useState<ResumeAnalysis | null>(null);
  const [history, setHistory] = useState<AnalysisSummary[]>([]);
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(validId);
  const [error, setError] = useState<string | null>(validId ? null : 'Invalid resume.');
  const [textError, setTextError] = useState<string | null>(null);
  const [activeGroup, setActiveGroup] = useState<string | null>(null);

  useEffect(() => {
    if (!validId) return;
    let cancelled = false;
    Promise.all([
      resumeService.getAnalysis(resumeId).catch((err: unknown) => {
        if (getErrorStatus(err) === 404) return null;
        throw err;
      }),
      resumeService.listAnalyses(resumeId).catch(() => [] as AnalysisSummary[]),
    ])
      .then(([a, h]) => {
        if (cancelled) return;
        setAnalysis(a);
        setHistory(h);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load this analysis.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    resumeService
      .getText(resumeId)
      .then((t) => {
        if (!cancelled) setText(t);
      })
      .catch((err: unknown) => {
        if (!cancelled) setTextError(getErrorMessage(err, 'Could not load the resume text.'));
      });
    return () => {
      cancelled = true;
    };
  }, [resumeId, validId]);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Resume analysis</h1>
        <Link to="/resume" className="text-sm text-primary hover:underline">
          Back to my resumes
        </Link>
      </div>
      <p className="text-sm text-muted-foreground">
        This is a keyword scan of your resume, not a readiness score, and it does not feed into your placement readiness. Matching is keyword-based
        against your college&apos;s configured skills and can miss synonyms.
      </p>

      <FormMessage message={error} />
      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading analysis...
        </p>
      )}
      {!loading && !error && !analysis && (
        <p className="text-muted-foreground" data-testid="no-analysis">
          This resume has not been analyzed yet. Go back to your resumes and choose Analyze.
        </p>
      )}

      {analysis && (
        <>
          {analysis.job_title && (
            <p className="text-sm font-medium" data-testid="analysis-job">
              Compared with job posting: {analysis.job_title}
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            Analyzed {formatDate(analysis.created_at)} · extractor {analysis.extractor_version}
          </p>
          <div className="grid gap-6 lg:grid-cols-2">
            <AnalysisResults analysis={analysis} activeGroup={activeGroup} onSelect={setActiveGroup} />
            <div className="lg:sticky lg:top-4 lg:self-start">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Source text</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <FormMessage message={textError} />
                  {text === null && !textError && (
                    <p role="status" className="text-sm text-muted-foreground">
                      Loading text...
                    </p>
                  )}
                  {text !== null && text.trim() === '' && (
                    <p className="text-sm text-muted-foreground">No text was extracted from this file, so there is nothing to highlight.</p>
                  )}
                  {text !== null && text.trim() !== '' && <SourceText text={text} extracted={analysis.extracted} activeGroup={activeGroup} />}
                  <p className="text-xs text-muted-foreground">Highlighted passages are the exact places each result was read from.</p>
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}

      {history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Analysis history</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y text-sm" aria-label="Analysis history">
              {history.map((h) => (
                <li key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span>{formatDate(h.created_at)}</span>
                  <span className="text-muted-foreground">
                    {h.role_name ?? 'No target role'}
                    {h.role_name ? ` · role match ${formatMatch(h.role_match_percent)}` : ''}
                    {h.has_jd ? ' · with job description' : ''}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
