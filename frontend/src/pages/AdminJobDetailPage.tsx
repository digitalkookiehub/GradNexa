import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { FormMessage } from '@/components/auth/FormField';
import { EligibilityForm } from '@/components/jobsAdmin/EligibilityForm';
import { EligibilitySummary } from '@/components/jobsAdmin/EligibilitySummary';
import { JobDetailsForm, type JobFormValues } from '@/components/jobsAdmin/JobDetailsForm';
import { StatusBadge } from '@/components/jobsAdmin/StatusBadge';
import { RoleSkillsEditor } from '@/components/readiness/RoleSkillsEditor';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getErrorMessage } from '@/lib/errors';
import { adminJobService } from '@/services/adminJobService';
import { adminReadinessService } from '@/services/adminReadinessService';
import { assessmentService } from '@/services/assessmentService';
import { studentService } from '@/services/studentService';
import type { CareerRole, Department, Skill, RoleSkillInput } from '@/types';
import type { AdminCompany, AdminJob, EligibilityRuleInput, JobUpdateInput } from '@/types/jobAdmin';

type Pending = 'publish' | 'close' | 'delete' | null;

export function AdminJobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const jobId = Number(id);
  const navigate = useNavigate();

  const [job, setJob] = useState<AdminJob | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [roles, setRoles] = useState<CareerRole[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [savingDetails, setSavingDetails] = useState(false);
  const [savingSkills, setSavingSkills] = useState(false);
  const [savingRule, setSavingRule] = useState(false);
  const [pending, setPending] = useState<Pending>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (): Promise<void> => {
    if (!Number.isInteger(jobId) || jobId <= 0) {
      setError('Invalid job id.');
      setLoading(false);
      return;
    }
    try {
      const [j, s, d] = await Promise.all([adminJobService.getJob(jobId), assessmentService.listSkills(), studentService.listDepartments()]);
      setJob(j);
      setSkills(s);
      setDepartments(d);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load the job.'));
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const r = await adminReadinessService.listRoles();
        if (!cancelled) setRoles(r);
      } catch {
        // TPO accounts cannot list roles (403); the picker is simply omitted.
        if (!cancelled) setRoles(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const closed = job?.status === 'CLOSED';

  const handleSaveDetails = async (values: JobFormValues): Promise<void> => {
    setSavingDetails(true);
    setError(null);
    setNotice(null);
    const payload: JobUpdateInput = { title: values.title, body: values.body, application_deadline: values.application_deadline };
    if (values.role_id !== undefined) payload.role_id = values.role_id;
    try {
      setJob(await adminJobService.updateJob(jobId, payload));
      setNotice('Job details saved.');
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the job details.'));
    } finally {
      setSavingDetails(false);
    }
  };

  const handleSaveSkills = async (payload: RoleSkillInput[]): Promise<void> => {
    setSavingSkills(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await adminJobService.setJobSkills(jobId, payload);
      setJob((prev) => (prev ? { ...prev, skills: saved } : prev));
      setNotice('Required skills saved.');
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the required skills.'));
    } finally {
      setSavingSkills(false);
    }
  };

  const handleSaveRule = async (payload: EligibilityRuleInput): Promise<void> => {
    setSavingRule(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await adminJobService.setEligibility(jobId, payload);
      setJob((prev) => (prev ? { ...prev, eligibility: saved, has_eligibility_rule: true } : prev));
      setNotice('Eligibility rule saved.');
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the eligibility rule.'));
    } finally {
      setSavingRule(false);
    }
  };

  const handleRemoveRule = async (): Promise<void> => {
    setSavingRule(true);
    setError(null);
    setNotice(null);
    try {
      await adminJobService.deleteEligibility(jobId);
      setJob((prev) => (prev ? { ...prev, eligibility: null, has_eligibility_rule: false } : prev));
      setNotice('Eligibility rule removed.');
    } catch (err) {
      setError(getErrorMessage(err, 'Could not remove the eligibility rule.'));
    } finally {
      setSavingRule(false);
    }
  };

  const handleConfirm = async (): Promise<void> => {
    if (!pending) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (pending === 'delete') {
        await adminJobService.deleteJob(jobId);
        navigate('/admin/jobs', { replace: true });
        return;
      }
      if (pending === 'publish') await adminJobService.publishJob(jobId);
      else await adminJobService.closeJob(jobId);
      setNotice(pending === 'publish' ? 'Job published.' : 'Job closed.');
      setPending(null);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not complete that action.'));
      setPending(null);
    } finally {
      setBusy(false);
    }
  };

  const companyStub: AdminCompany[] = [];
  const confirmCopy: Record<Exclude<Pending, null>, { title: string; message: string; label: string; destructive: boolean }> = {
    publish: { title: 'Publish job', message: 'Publishing makes this job visible to students.', label: 'Confirm publish', destructive: false },
    close: { title: 'Close job', message: 'Closing is permanent. A closed job can no longer be edited or reopened.', label: 'Confirm close', destructive: true },
    delete: { title: 'Delete job', message: 'This permanently deletes the draft job.', label: 'Confirm delete', destructive: true },
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to="/admin/jobs" className="text-sm text-muted-foreground hover:text-foreground">
        Back to jobs
      </Link>
      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading job...
        </p>
      )}
      <FormMessage message={error} />
      <FormMessage message={notice} tone="success" />

      {job && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <h1 className="flex flex-wrap items-center gap-2 text-2xl font-semibold">
                {job.title}
                <StatusBadge status={job.status} />
              </h1>
              <p className="text-sm text-muted-foreground">{job.company_name}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {job.status === 'DRAFT' && (
                <>
                  <Button onClick={() => setPending('publish')} disabled={busy}>
                    Publish
                  </Button>
                  <Button variant="outline" onClick={() => setPending('delete')} disabled={busy}>
                    Delete draft
                  </Button>
                </>
              )}
              {job.status === 'OPEN' && (
                <Button variant="outline" onClick={() => setPending('close')} disabled={busy}>
                  Close job
                </Button>
              )}
            </div>
          </div>

          {closed && <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm">This job is closed and can no longer be edited.</p>}

          {pending && (
            <ConfirmPanel
              title={confirmCopy[pending].title}
              message={confirmCopy[pending].message}
              confirmLabel={confirmCopy[pending].label}
              destructive={confirmCopy[pending].destructive}
              busy={busy}
              onConfirm={() => void handleConfirm()}
              onCancel={() => setPending(null)}
            />
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Details</CardTitle>
            </CardHeader>
            <CardContent>
              <JobDetailsForm
                key={`${job.id}:${job.status}`}
                job={job}
                companies={companyStub}
                roles={roles}
                disabled={closed}
                saving={savingDetails}
                submitLabel="Save details"
                onSubmit={(v) => void handleSaveDetails(v)}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Required skills</CardTitle>
            </CardHeader>
            <CardContent>
              {closed ? (
                job.skills.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No skills were set for this job.</p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {job.skills.map((s) => (
                      <li key={s.skill_id}>
                        {s.skill_name}: required level {s.required_level}, weight {s.weight}
                      </li>
                    ))}
                  </ul>
                )
              ) : (
                <RoleSkillsEditor
                  key={`${job.id}:${job.skills.map((s) => `${s.skill_id}-${s.required_level}-${s.weight}`).join(',')}`}
                  skills={skills}
                  initial={job.skills}
                  saving={savingSkills}
                  onSave={(p) => void handleSaveSkills(p)}
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Eligibility rule</CardTitle>
            </CardHeader>
            <CardContent>
              <EligibilityForm
                key={`${job.id}:${JSON.stringify(job.eligibility)}`}
                initial={job.eligibility}
                departments={departments}
                saving={savingRule}
                readOnly={closed}
                onSave={(p) => void handleSaveRule(p)}
                onRemove={() => void handleRemoveRule()}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Summary of the saved rule</CardTitle>
            </CardHeader>
            <CardContent>
              <EligibilitySummary rule={job.eligibility} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
