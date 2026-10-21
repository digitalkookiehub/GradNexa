import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { DepartmentSelect } from '@/components/admin/DepartmentSelect';
import { FieldError } from '@/components/auth/FieldError';
import { FormMessage } from '@/components/auth/FormField';
import { RoleSkillsEditor } from '@/components/readiness/RoleSkillsEditor';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { adminReadinessService } from '@/services/adminReadinessService';
import { assessmentService } from '@/services/assessmentService';
import { studentService } from '@/services/studentService';
import type { CareerRole, CareerRoleDetail, Department, RoleSkillInput, Skill } from '@/types';

type Editor = { mode: 'closed' } | { mode: 'new' } | { mode: 'edit'; detail: CareerRoleDetail };

export function AdminCareerRolesPage() {
  const [roles, setRoles] = useState<CareerRole[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editor, setEditor] = useState<Editor>({ mode: 'closed' });
  const [opening, setOpening] = useState(false);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [nameError, setNameError] = useState<string | undefined>();
  const [saving, setSaving] = useState(false);
  const [savingSkills, setSavingSkills] = useState(false);

  const load = useCallback(async (): Promise<void> => {
    try {
      const [r, d, s] = await Promise.all([adminReadinessService.listRoles(), studentService.listDepartments(), assessmentService.listSkills()]);
      setRoles(r);
      setDepartments(d);
      setSkills(s);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load career roles.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const fillForm = (role: CareerRole | null): void => {
    setName(role?.name ?? '');
    setDescription(role?.description ?? '');
    setDepartmentId(role?.department_id != null ? String(role.department_id) : '');
    setIsActive(role?.is_active ?? true);
    setNameError(undefined);
  };

  const openNew = (): void => {
    fillForm(null);
    setNotice(null);
    setEditor({ mode: 'new' });
  };

  const openEdit = async (role: CareerRole): Promise<void> => {
    setOpening(true);
    setError(null);
    setNotice(null);
    try {
      const detail = await adminReadinessService.getRole(role.id);
      fillForm(detail);
      setEditor({ mode: 'edit', detail });
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load the role.'));
    } finally {
      setOpening(false);
    }
  };

  const handleSaveRole = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (!name.trim()) {
      setNameError('Role name is required.');
      return;
    }
    setNameError(undefined);
    setSaving(true);
    setError(null);
    setNotice(null);
    const payload = {
      name: name.trim(),
      description: description.trim() || null,
      department_id: departmentId ? Number(departmentId) : null,
      is_active: isActive,
    };
    try {
      if (editor.mode === 'edit') {
        await adminReadinessService.updateRole(editor.detail.id, payload);
        const detail = await adminReadinessService.getRole(editor.detail.id);
        setEditor({ mode: 'edit', detail });
        setNotice('Role saved.');
      } else {
        const created = await adminReadinessService.createRole(payload);
        const detail = await adminReadinessService.getRole(created.id);
        setEditor({ mode: 'edit', detail });
        setNotice('Role created. Add the skills it requires below.');
      }
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the role.'));
    } finally {
      setSaving(false);
    }
  };

  const handleSaveSkills = async (payload: RoleSkillInput[]): Promise<void> => {
    if (editor.mode !== 'edit') return;
    setSavingSkills(true);
    setError(null);
    setNotice(null);
    try {
      const detail = await adminReadinessService.setRoleSkills(editor.detail.id, payload);
      setEditor({ mode: 'edit', detail });
      setNotice('Required skills saved.');
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the required skills.'));
    } finally {
      setSavingSkills(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Career roles</h1>
        {editor.mode === 'closed' && <Button onClick={openNew}>New role</Button>}
      </div>
      <FormMessage message={error} />
      <FormMessage message={notice} tone="success" />

      {editor.mode !== 'closed' && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{editor.mode === 'edit' ? `Edit role: ${editor.detail.name}` : 'New role'}</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={(e) => void handleSaveRole(e)} noValidate className="grid gap-4 sm:grid-cols-2" aria-label="Role form">
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="role-name">Role name</Label>
                  <Input id="role-name" value={name} onChange={(e) => setName(e.target.value)} aria-invalid={Boolean(nameError)} />
                  <FieldError id="role-name-error" message={nameError} />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="role-description">Description (optional)</Label>
                  <Input id="role-description" value={description} onChange={(e) => setDescription(e.target.value)} />
                </div>
                <DepartmentSelect
                  id="role-department"
                  label="Department (optional)"
                  departments={departments}
                  value={departmentId}
                  onChange={setDepartmentId}
                  placeholder="All departments"
                />
                <div className="flex items-end gap-2">
                  <input id="role-active" type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
                  <Label htmlFor="role-active">Active</Label>
                </div>
                <div className="flex gap-2 sm:col-span-2">
                  <Button type="submit" disabled={saving}>
                    {saving ? 'Saving...' : editor.mode === 'edit' ? 'Save role' : 'Create role'}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => setEditor({ mode: 'closed' })} disabled={saving}>
                    Close
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {editor.mode === 'edit' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Required skills</CardTitle>
              </CardHeader>
              <CardContent>
                <RoleSkillsEditor key={editor.detail.id + ':' + editor.detail.skills.length} skills={skills} initial={editor.detail.skills} saving={savingSkills} onSave={(p) => void handleSaveSkills(p)} />
              </CardContent>
            </Card>
          )}
        </>
      )}

      {(loading || opening) && (
        <p role="status" className="text-muted-foreground">
          {opening ? 'Loading role...' : 'Loading roles...'}
        </p>
      )}
      {!loading && roles.length === 0 && !error && <p className="text-muted-foreground">No career roles yet.</p>}
      <ul className="space-y-3">
        {roles.map((r) => (
          <li key={r.id}>
            <Card>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <div className="font-medium">
                    {r.name}
                    {!r.is_active && <span className="ml-2 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">Inactive</span>}
                  </div>
                  {r.description && <div className="text-sm text-muted-foreground">{r.description}</div>}
                </div>
                <Button size="sm" variant="outline" onClick={() => void openEdit(r)} disabled={opening} aria-label={`Edit role ${r.name}`}>
                  Edit
                </Button>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
