import { useEffect, useState, type FormEvent } from 'react';
import { TagInput } from './TagInput';
import { FieldError } from '@/components/auth/FieldError';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { validateProject, type FieldErrors, type ProjectFormValues } from '@/lib/studentValidation';
import { studentService } from '@/services/studentService';
import type { Project } from '@/types';

export function ProjectsPanel() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [form, setForm] = useState<ProjectFormValues>({ title: '', url: '' });
  const [description, setDescription] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [errors, setErrors] = useState<FieldErrors<keyof ProjectFormValues>>({});
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    studentService
      .listProjects()
      .then((data) => {
        if (!cancelled) setProjects(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setListError(getErrorMessage(err, 'Could not load projects.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setListError(null);
    const found = validateProject(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setSubmitting(true);
    try {
      const created = await studentService.createProject({
        title: form.title.trim(),
        description: description.trim() || null,
        skills,
        url: form.url.trim() || null,
      });
      setProjects((prev) => [...prev, created]);
      setForm({ title: '', url: '' });
      setDescription('');
      setSkills([]);
    } catch (err) {
      setListError(getErrorMessage(err, 'Could not add the project.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number): Promise<void> => {
    setListError(null);
    setDeletingId(id);
    try {
      await studentService.deleteProject(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setListError(getErrorMessage(err, 'Could not delete the project.'));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <FormMessage message={listError} />
      {loading ? (
        <p role="status" className="text-sm text-muted-foreground">
          Loading projects...
        </p>
      ) : projects.length === 0 ? (
        <p className="text-sm text-muted-foreground">No projects yet.</p>
      ) : (
        <ul className="space-y-3" aria-label="Projects">
          {projects.map((p) => (
            <li key={p.id} className="flex items-start justify-between gap-4 rounded-md border p-4 text-sm">
              <div className="space-y-1">
                <div className="font-medium">{p.title}</div>
                {p.description && <p className="text-muted-foreground">{p.description}</p>}
                {p.skills.length > 0 && <p className="text-xs text-muted-foreground">Skills: {p.skills.join(', ')}</p>}
                {p.url && (
                  <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                    {p.url}
                  </a>
                )}
              </div>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={() => handleDelete(p.id)}
                disabled={deletingId === p.id}
                aria-label={`Delete project ${p.title}`}
              >
                {deletingId === p.id ? 'Deleting...' : 'Delete'}
              </Button>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleSubmit} className="space-y-4 rounded-md border p-4" noValidate aria-label="Add project">
        <h3 className="text-sm font-semibold">Add a project</h3>
        <div className="space-y-2">
          <Label htmlFor="project-title">Title</Label>
          <Input
            id="project-title"
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            disabled={submitting}
            aria-invalid={errors.title ? true : undefined}
            aria-describedby={errors.title ? 'project-title-error' : undefined}
          />
          <FieldError id="project-title-error" message={errors.title} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="project-description">Description (optional)</Label>
          <Input id="project-description" value={description} onChange={(e) => setDescription(e.target.value)} disabled={submitting} />
        </div>
        <TagInput
          id="project-skills"
          label="Skills"
          tags={skills}
          onChange={setSkills}
          disabled={submitting}
        />
        <div className="space-y-2">
          <Label htmlFor="project-url">URL (optional)</Label>
          <Input
            id="project-url"
            value={form.url}
            onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
            disabled={submitting}
            aria-invalid={errors.url ? true : undefined}
            aria-describedby={errors.url ? 'project-url-error' : undefined}
          />
          <FieldError id="project-url-error" message={errors.url} />
        </div>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Adding...' : 'Add project'}
        </Button>
      </form>
    </div>
  );
}
