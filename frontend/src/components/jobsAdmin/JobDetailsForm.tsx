import { useState, type FormEvent } from 'react';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { FieldError } from '@/components/auth/FieldError';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { isoToLocalInput, localInputToIso } from './validation';
import type { CareerRole } from '@/types';
import type { AdminCompany, AdminJob } from '@/types/jobAdmin';

export interface JobFormValues {
  company_id: number;
  title: string;
  body: string;
  /** undefined when the role picker is unavailable, so the existing role is left untouched. */
  role_id: number | null | undefined;
  application_deadline: string | null;
}

interface JobDetailsFormProps {
  /** Existing job when editing; null when creating. */
  job: AdminJob | null;
  companies: AdminCompany[];
  /** null means the role list is unavailable (for example a 403 for TPO). */
  roles: CareerRole[] | null;
  disabled: boolean;
  saving: boolean;
  submitLabel: string;
  onSubmit: (values: JobFormValues) => void;
  onCancel?: () => void;
}

interface FormErrors {
  company?: string;
  title?: string;
  body?: string;
  deadline?: string;
}

export function JobDetailsForm({ job, companies, roles, disabled, saving, submitLabel, onSubmit, onCancel }: JobDetailsFormProps) {
  const [companyId, setCompanyId] = useState(job ? String(job.company_id) : '');
  const [title, setTitle] = useState(job?.title ?? '');
  const [body, setBody] = useState(job?.body ?? '');
  const [roleId, setRoleId] = useState(job?.role_id != null ? String(job.role_id) : '');
  const [deadline, setDeadline] = useState(isoToLocalInput(job?.application_deadline ?? null));
  const [errors, setErrors] = useState<FormErrors>({});

  const handleSubmit = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    const next: FormErrors = {};
    if (!job && !companyId) next.company = 'Choose a company.';
    if (!title.trim()) next.title = 'Job title is required.';
    if (!body.trim()) next.body = 'Job description is required.';
    const iso = localInputToIso(deadline);
    if (deadline && iso === null) next.deadline = 'Enter a valid deadline.';
    setErrors(next);
    if (Object.keys(next).length > 0) return;
    onSubmit({
      company_id: job ? job.company_id : Number(companyId),
      title: title.trim(),
      body: body.trim(),
      role_id: roles === null ? undefined : roleId ? Number(roleId) : null,
      application_deadline: iso,
    });
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="grid gap-4" aria-label="Job form">
      <fieldset disabled={disabled || saving} className="grid gap-4">
        {!job && (
          <div className="space-y-2">
            <Label htmlFor="job-company">Company</Label>
            <select id="job-company" className={SELECT_CLASS} value={companyId} onChange={(e) => setCompanyId(e.target.value)} aria-invalid={Boolean(errors.company)}>
              <option value="">Select a company</option>
              {companies
                .filter((c) => c.is_active)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
            </select>
            <FieldError id="job-company-error" message={errors.company} />
          </div>
        )}
        <div className="space-y-2">
          <Label htmlFor="job-title">Job title</Label>
          <Input id="job-title" value={title} onChange={(e) => setTitle(e.target.value)} aria-invalid={Boolean(errors.title)} />
          <FieldError id="job-title-error" message={errors.title} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="job-body">Job description</Label>
          <textarea
            id="job-body"
            rows={6}
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            aria-invalid={Boolean(errors.body)}
          />
          <FieldError id="job-body-error" message={errors.body} />
        </div>
        {roles !== null ? (
          <div className="space-y-2">
            <Label htmlFor="job-role">Career role (optional)</Label>
            <select id="job-role" className={SELECT_CLASS} value={roleId} onChange={(e) => setRoleId(e.target.value)}>
              <option value="">No role</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground" data-testid="role-unavailable">
            Career role selection is not available for your account.
            {job?.role_name ? ` Current role: ${job.role_name} (unchanged on save).` : ''}
          </p>
        )}
        <div className="space-y-2">
          <Label htmlFor="job-deadline">Application deadline (optional)</Label>
          <Input id="job-deadline" type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} aria-invalid={Boolean(errors.deadline)} />
          <FieldError id="job-deadline-error" message={errors.deadline} />
        </div>
      </fieldset>
      {!disabled && (
        <div className="flex gap-2">
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving...' : submitLabel}
          </Button>
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>
              Cancel
            </Button>
          )}
        </div>
      )}
    </form>
  );
}
