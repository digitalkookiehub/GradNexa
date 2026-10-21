import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { EligibilitySection } from '@/components/jobs/EligibilitySection';
import { SkillFitSection } from '@/components/jobs/SkillFitSection';
import { getErrorMessage, getErrorStatus } from '@/lib/errors';
import { formatDeadline } from '@/lib/jobs';
import { jobService } from '@/services/jobService';
import type { JobDetail } from '@/types/jobs';

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const jobId = Number(id);
  const validId = Number.isInteger(jobId) && jobId > 0;
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(validId);
  const [error, setError] = useState<string | null>(validId ? null : 'Invalid job posting.');

  useEffect(() => {
    if (!validId) return;
    let cancelled = false;
    jobService
      .get(jobId)
      .then((j) => {
        if (!cancelled) setJob(j);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          getErrorStatus(err) === 404 ? 'This job posting was not found or is no longer open.' : getErrorMessage(err, 'Could not load this job posting.'),
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, validId]);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Link to="/jobs" className="text-sm text-primary hover:underline">
        Back to jobs
      </Link>
      <FormMessage message={error} />
      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading job...
        </p>
      )}
      {job && (
        <>
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold">{job.title}</h1>
            <p className="text-muted-foreground">{job.company.name}</p>
            {job.company.description && <p className="text-sm text-muted-foreground">{job.company.description}</p>}
            {job.company.website && <p className="text-sm text-muted-foreground">Website: {job.company.website}</p>}
            <p className="text-sm">
              {job.role_name ? `Role: ${job.role_name} · ` : ''}
              Deadline: {formatDeadline(job.application_deadline)}
              {job.deadline_passed && <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">Deadline passed</span>}
            </p>
          </div>

          <section aria-labelledby="description-heading" className="space-y-2">
            <h2 id="description-heading" className="text-lg font-semibold">
              Description
            </h2>
            <p className="whitespace-pre-wrap text-sm" data-testid="job-body">
              {job.body}
            </p>
          </section>

          <section aria-labelledby="required-skills-heading" className="space-y-2">
            <h2 id="required-skills-heading" className="text-lg font-semibold">
              Required skills
            </h2>
            {job.skills.length === 0 ? (
              <p className="text-sm text-muted-foreground">No required skills are listed.</p>
            ) : (
              <div className="overflow-x-auto rounded-md border bg-background">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b text-muted-foreground">
                      <th className="p-3 font-medium">Skill</th>
                      <th className="p-3 font-medium">Required level</th>
                      <th className="p-3 font-medium">Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    {job.skills.map((s) => (
                      <tr key={s.skill_id} className="border-b last:border-0">
                        <td className="p-3 font-medium">{s.skill_name}</td>
                        <td className="p-3">{s.required_level}</td>
                        <td className="p-3">{s.weight}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <EligibilitySection jobId={job.id} />
          <SkillFitSection jobId={job.id} />

          <Link to={`/resume?job=${job.id}`} className="inline-block text-sm text-primary hover:underline">
            Compare my resume
          </Link>
        </>
      )}
    </div>
  );
}
