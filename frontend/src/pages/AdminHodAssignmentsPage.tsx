import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { DepartmentSelect, SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { adminUserService } from '@/services/adminUserService';
import { hodAssignmentService } from '@/services/hodAssignmentService';
import { studentService } from '@/services/studentService';
import type { AdminUser } from '@/types/adminUsers';
import type { Department, HodAssignment } from '@/types';

export function AdminHodAssignmentsPage() {
  const [items, setItems] = useState<HodAssignment[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [hodUsers, setHodUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [userId, setUserId] = useState('');
  const [deptId, setDeptId] = useState('');
  const [formError, setFormError] = useState<string | undefined>();
  const [saving, setSaving] = useState(false);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    try {
      const [a, d, h] = await Promise.all([
        hodAssignmentService.list(),
        studentService.listDepartments(),
        adminUserService.list({ role: 'HOD', page_size: 100 }),
      ]);
      setItems(a);
      setDepartments(d);
      setHodUsers(h.items);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load HOD assignments.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setNotice(null);
    const parsedUser = Number(userId);
    if (!userId || !Number.isInteger(parsedUser) || parsedUser <= 0) {
      setFormError('Choose a HOD.');
      return;
    }
    if (!deptId) {
      setFormError('Select a department.');
      return;
    }
    setSaving(true);
    setFormError(undefined);
    try {
      await hodAssignmentService.create({ hod_user_id: parsedUser, department_id: Number(deptId) });
      setUserId('');
      setDeptId('');
      setNotice('Assignment created.');
      await load();
    } catch (err) {
      setFormError(getErrorMessage(err, 'Could not create the assignment.'));
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async (id: number): Promise<void> => {
    setDeleting(true);
    setNotice(null);
    try {
      await hodAssignmentService.remove(id);
      setConfirmId(null);
      setNotice('Assignment removed.');
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not remove the assignment.'));
      setConfirmId(null);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">HOD assignments</h1>
        <p className="text-sm text-muted-foreground">Choose which departments each head of department can see.</p>
      </div>

      <FormMessage message={error} />
      <FormMessage message={notice} tone="success" />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Add assignment</CardTitle>
          <CardDescription>Choose a user whose role is HOD. To make someone a HOD, change their role on the Users and students page first.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void submit(e)} className="grid gap-4 sm:grid-cols-3 sm:items-end" noValidate>
            <div className="space-y-2">
              <Label htmlFor="hod-user-id">HOD</Label>
              <select id="hod-user-id" className={SELECT_CLASS} value={userId} onChange={(e) => setUserId(e.target.value)} aria-invalid={Boolean(formError)}>
                <option value="">{hodUsers.length === 0 ? 'No HOD users yet' : 'Select a HOD'}</option>
                {hodUsers.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.full_name} ({h.email})
                  </option>
                ))}
              </select>
            </div>
            <DepartmentSelect
              id="hod-assign-department"
              label="Department"
              departments={departments}
              value={deptId}
              onChange={setDeptId}
              placeholder="Select a department"
            />
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Add assignment'}
            </Button>
          </form>
          <FormMessage message={formError ?? null} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Current assignments</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p role="status" className="text-muted-foreground">
              Loading assignments...
            </p>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">No HOD assignments yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <caption className="sr-only">HOD assignments</caption>
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th scope="col" className="py-2 pr-4 font-medium">HOD</th>
                    <th scope="col" className="py-2 pr-4 font-medium">Department</th>
                    <th scope="col" className="py-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((a) => (
                    <tr key={a.id} className="border-b last:border-0">
                      <th scope="row" className="py-2 pr-4 text-left font-normal">
                        <div className="font-medium">{a.hod_name}</div>
                        <div className="text-xs text-muted-foreground">{a.hod_email}</div>
                      </th>
                      <td className="py-2 pr-4">{a.department_name}</td>
                      <td className="py-2">
                        {confirmId === a.id ? (
                          <div className="flex flex-wrap items-center gap-2" role="group" aria-label={`Confirm removing ${a.hod_name} from ${a.department_name}`}>
                            <span>Remove this assignment?</span>
                            <Button size="sm" variant="destructive" disabled={deleting} onClick={() => void confirmDelete(a.id)}>
                              {deleting ? 'Removing...' : 'Confirm remove'}
                            </Button>
                            <Button size="sm" variant="outline" disabled={deleting} onClick={() => setConfirmId(null)}>
                              Cancel
                            </Button>
                          </div>
                        ) : (
                          <Button size="sm" variant="outline" onClick={() => setConfirmId(a.id)} aria-label={`Remove ${a.hod_name} from ${a.department_name}`}>
                            Remove
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
