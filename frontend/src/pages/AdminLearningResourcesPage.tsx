import { useCallback, useEffect, useState } from 'react';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/errors';
import { validateResourceUrl } from '@/lib/roadmap';
import { adminResourceService } from '@/services/adminResourceService';
import { assessmentService } from '@/services/assessmentService';
import type { AdminLearningResource, Skill } from '@/types';

type PendingAction = { kind: 'approve' | 'unapprove' | 'delete'; resource: AdminLearningResource };

interface FormErrors {
  skill?: string;
  title?: string;
  url?: string;
}

export function AdminLearningResourcesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const [skills, setSkills] = useState<Skill[]>([]);
  const [resources, setResources] = useState<AdminLearningResource[]>([]);
  const [skillFilter, setSkillFilter] = useState('');
  const [approvedFilter, setApprovedFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [skillId, setSkillId] = useState('');
  const [title, setTitle] = useState('');
  const [url, setUrl] = useState('');
  const [description, setDescription] = useState('');
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [saving, setSaving] = useState(false);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [acting, setActing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    assessmentService
      .listSkills()
      .then((s) => {
        if (!cancelled) setSkills(s);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load skills.'));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    adminResourceService
      .list({
        skillId: skillFilter === '' ? undefined : Number(skillFilter),
        approved: approvedFilter === '' ? undefined : approvedFilter === 'true',
      })
      .then((r) => {
        if (cancelled) return;
        setResources(r);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load learning resources.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [skillFilter, approvedFilter, attempt]);

  const resetForm = (): void => {
    setEditingId(null);
    setSkillId('');
    setTitle('');
    setUrl('');
    setDescription('');
    setFormErrors({});
  };

  const startEdit = (r: AdminLearningResource): void => {
    setEditingId(r.id);
    setSkillId(String(r.skill_id));
    setTitle(r.title);
    setUrl(r.url);
    setDescription(r.description ?? '');
    setFormErrors({});
    setMessage(null);
  };

  const handleSubmit = useCallback(async (): Promise<void> => {
    const errors: FormErrors = {};
    if (skillId === '') errors.skill = 'Select a skill.';
    if (!title.trim()) errors.title = 'Enter a title.';
    const urlError = validateResourceUrl(url);
    if (urlError) errors.url = urlError;
    setFormErrors(errors);
    if (errors.skill || errors.title || errors.url) return;

    setSaving(true);
    setError(null);
    setMessage(null);
    const input = { skill_id: Number(skillId), title: title.trim(), url: url.trim(), description: description.trim() === '' ? null : description.trim() };
    try {
      if (editingId === null) {
        await adminResourceService.create(input);
        setMessage('Resource created. It stays unapproved until an administrator approves it.');
      } else {
        await adminResourceService.update(editingId, input);
        setMessage('Resource updated.');
      }
      resetForm();
      setAttempt((a) => a + 1);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the resource.'));
    } finally {
      setSaving(false);
    }
  }, [skillId, title, url, description, editingId]);

  const handleConfirm = useCallback(async (): Promise<void> => {
    if (!pending) return;
    setActing(true);
    setError(null);
    setMessage(null);
    try {
      if (pending.kind === 'approve') await adminResourceService.approve(pending.resource.id);
      else if (pending.kind === 'unapprove') await adminResourceService.unapprove(pending.resource.id);
      else await adminResourceService.remove(pending.resource.id);
      setMessage(pending.kind === 'approve' ? 'Resource approved.' : pending.kind === 'unapprove' ? 'Approval removed.' : 'Resource deleted.');
      setPending(null);
      setAttempt((a) => a + 1);
    } catch (err) {
      setError(getErrorMessage(err, 'That action failed.'));
      setPending(null);
    } finally {
      setActing(false);
    }
  }, [pending]);

  const confirmCopy = (p: PendingAction): { title: string; message: string; label: string; destructive: boolean } => {
    if (p.kind === 'approve') {
      return { title: 'Approve this resource?', message: `Students will see "${p.resource.title}" in their plans.`, label: 'Approve', destructive: false };
    }
    if (p.kind === 'unapprove') {
      return { title: 'Remove approval?', message: `"${p.resource.title}" will no longer be shown to students.`, label: 'Unapprove', destructive: true };
    }
    return { title: 'Delete this resource?', message: `"${p.resource.title}" will be permanently removed.`, label: 'Delete', destructive: true };
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Learning resources</h1>
        <p className="text-sm text-muted-foreground">
          Only approved resources are shown to students. {isAdmin ? 'You can approve or unapprove resources.' : 'An administrator must approve a resource before students see it.'}
        </p>
      </div>

      <FormMessage message={error} />
      <FormMessage message={message} tone="success" />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{editingId === null ? 'Add a resource' : 'Edit resource'}</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            noValidate
            onSubmit={(e) => {
              e.preventDefault();
              void handleSubmit();
            }}
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="res-skill">Skill</Label>
                <select id="res-skill" className={SELECT_CLASS} value={skillId} onChange={(e) => setSkillId(e.target.value)} aria-invalid={!!formErrors.skill}>
                  <option value="">Select a skill</option>
                  {skills.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
                {formErrors.skill && <p className="text-sm text-destructive">{formErrors.skill}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="res-title">Title</Label>
                <Input id="res-title" value={title} onChange={(e) => setTitle(e.target.value)} aria-invalid={!!formErrors.title} />
                {formErrors.title && <p className="text-sm text-destructive">{formErrors.title}</p>}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="res-url">URL</Label>
              <Input id="res-url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" aria-invalid={!!formErrors.url} />
              {formErrors.url && <p className="text-sm text-destructive">{formErrors.url}</p>}
              {editingId !== null && <p className="text-xs text-muted-foreground">Changing the URL or the skill resets approval; an administrator must approve it again.</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="res-description">Description (optional)</Label>
              <Input id="res-description" value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving...' : editingId === null ? 'Add resource' : 'Save changes'}
              </Button>
              {editingId !== null && (
                <Button type="button" variant="outline" onClick={resetForm} disabled={saving}>
                  Cancel edit
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="filter-skill">Filter by skill</Label>
          <select id="filter-skill" className={SELECT_CLASS} value={skillFilter} onChange={(e) => setSkillFilter(e.target.value)}>
            <option value="">All skills</option>
            {skills.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="filter-approved">Approval</Label>
          <select id="filter-approved" className={SELECT_CLASS} value={approvedFilter} onChange={(e) => setApprovedFilter(e.target.value)}>
            <option value="">All</option>
            <option value="true">Approved</option>
            <option value="false">Not approved</option>
          </select>
        </div>
      </div>

      {pending && (
        <ConfirmPanel
          title={confirmCopy(pending).title}
          message={confirmCopy(pending).message}
          confirmLabel={confirmCopy(pending).label}
          destructive={confirmCopy(pending).destructive}
          busy={acting}
          onConfirm={() => void handleConfirm()}
          onCancel={() => setPending(null)}
        />
      )}

      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading resources...
        </p>
      )}
      {!loading && resources.length === 0 && !error && <p className="text-muted-foreground">No learning resources match these filters.</p>}
      {!loading && error && resources.length === 0 && (
        <Button variant="outline" onClick={() => setAttempt((a) => a + 1)}>
          Retry
        </Button>
      )}
      <ul className="space-y-3" aria-label="Learning resources">
        {resources.map((r) => (
          <li key={r.id}>
            <Card>
              <CardContent className="space-y-2 p-4 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">{r.title}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${r.is_approved ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}
                    data-testid={`approval-${r.id}`}
                  >
                    {r.is_approved ? 'Approved' : 'Not approved'}
                  </span>
                </div>
                <p className="text-muted-foreground">{r.skill_name}</p>
                <a href={r.url} target="_blank" rel="noopener noreferrer" className="break-all text-primary hover:underline">
                  {r.url}
                </a>
                {r.description && <p>{r.description}</p>}
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={() => startEdit(r)} aria-label={`Edit ${r.title}`}>
                    Edit
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setPending({ kind: 'delete', resource: r })} aria-label={`Delete ${r.title}`}>
                    Delete
                  </Button>
                  {isAdmin &&
                    (r.is_approved ? (
                      <Button variant="outline" size="sm" onClick={() => setPending({ kind: 'unapprove', resource: r })} aria-label={`Unapprove ${r.title}`}>
                        Unapprove
                      </Button>
                    ) : (
                      <Button size="sm" onClick={() => setPending({ kind: 'approve', resource: r })} aria-label={`Approve ${r.title}`}>
                        Approve
                      </Button>
                    ))}
                </div>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
