import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { DepartmentSelect, SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/errors';
import { adminUserService } from '@/services/adminUserService';
import { studentService } from '@/services/studentService';
import { ASSIGNABLE_ROLES, ROLE_LABELS, type AdminUser, type AdminUserPage } from '@/types/adminUsers';
import type { Department, UserRole } from '@/types';

const PAGE_SIZE = 25;

function describeChange(user: AdminUser, to: UserRole): string {
  const parts = [`${user.full_name} will become ${ROLE_LABELS[to] ?? to}. This takes effect immediately, including for anyone already signed in.`];
  if (user.role === 'FACULTY') parts.push('Their faculty-to-student assignments will be removed.');
  if (user.role === 'HOD') parts.push('Their department assignments will be removed.');
  if (to === 'ADMIN') parts.push('Admins can change every college setting and other users’ roles.');
  return parts.join(' ');
}

export function UsersTab() {
  const { user: me } = useAuth();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [role, setRole] = useState<UserRole | ''>('');
  const [departmentId, setDepartmentId] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AdminUserPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [newRole, setNewRole] = useState<UserRole>('FACULTY');
  const [confirming, setConfirming] = useState<{ user: AdminUser; to: UserRole } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    studentService
      .listDepartments()
      .then(setDepartments)
      .catch(() => setDepartments([]));
  }, []);

  const load = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const result = await adminUserService.list({
        search,
        role,
        department_id: departmentId ? Number(departmentId) : null,
        page,
        page_size: PAGE_SIZE,
      });
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load users.'));
    } finally {
      setLoading(false);
    }
  }, [search, role, departmentId, page]);

  useEffect(() => {
    void load();
  }, [load]);

  const applyFilters = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    setPage(1);
    setSearch(searchDraft);
  };

  const confirmChange = async (): Promise<void> => {
    if (!confirming) return;
    setBusy(true);
    setNotice(null);
    try {
      const result = await adminUserService.changeRole(confirming.user.id, confirming.to);
      const extra: string[] = [];
      if (result.removed_faculty_assignments > 0) extra.push(`${result.removed_faculty_assignments} faculty assignment(s) removed`);
      if (result.removed_hod_assignments > 0) extra.push(`${result.removed_hod_assignments} HOD assignment(s) removed`);
      setNotice(`${confirming.user.full_name} is now ${ROLE_LABELS[result.role] ?? result.role}.${extra.length ? ` ${extra.join('; ')}.` : ''}`);
      setConfirming(null);
      setEditingId(null);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not change the role.'));
      setConfirming(null);
    } finally {
      setBusy(false);
    }
  };

  const total = data?.total ?? 0;
  const first = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const last = Math.min(page * PAGE_SIZE, total);

  return (
    <div className="space-y-4">
      <form onSubmit={applyFilters} className="grid gap-3 rounded-lg border bg-background p-4 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_auto] lg:items-end" aria-label="Filter users">
        <div className="space-y-2">
          <Label htmlFor="user-search">Search name, email or roll number</Label>
          <Input id="user-search" value={searchDraft} onChange={(e) => setSearchDraft(e.target.value)} placeholder="e.g. Asha or CSE-101" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="user-role">Role</Label>
          <select
            id="user-role"
            className={SELECT_CLASS}
            value={role}
            onChange={(e) => {
              setPage(1);
              setRole(e.target.value as UserRole | '');
            }}
          >
            <option value="">All roles</option>
            {ASSIGNABLE_ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
        </div>
        <DepartmentSelect
          id="user-department"
          label="Student department"
          departments={departments}
          value={departmentId}
          onChange={(v) => {
            setPage(1);
            setDepartmentId(v);
          }}
          placeholder="All departments"
        />
        <Button type="submit">Search</Button>
      </form>

      <FormMessage message={error} />
      <FormMessage message={notice} tone="success" />

      {confirming && (
        <ConfirmPanel
          title={`Change role to ${ROLE_LABELS[confirming.to] ?? confirming.to}?`}
          message={describeChange(confirming.user, confirming.to)}
          confirmLabel="Change role"
          busy={busy}
          destructive={confirming.to === 'ADMIN' || confirming.user.role === 'FACULTY' || confirming.user.role === 'HOD'}
          onConfirm={() => void confirmChange()}
          onCancel={() => setConfirming(null)}
        />
      )}

      {loading && !data ? (
        <p role="status" className="text-muted-foreground">
          Loading users...
        </p>
      ) : total === 0 ? (
        <p className="rounded-md border bg-background p-4 text-sm text-muted-foreground">No users match these filters.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border bg-background">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Users in your college</caption>
            <thead>
              <tr className="border-b bg-muted text-muted-foreground">
                <th scope="col" className="px-3 py-2 font-medium">Name</th>
                <th scope="col" className="px-3 py-2 font-medium">Role</th>
                <th scope="col" className="px-3 py-2 font-medium">Department</th>
                <th scope="col" className="px-3 py-2 font-medium">Roll no.</th>
                <th scope="col" className="px-3 py-2 font-medium">Grad. year</th>
                <th scope="col" className="px-3 py-2 font-medium">Profile</th>
                <th scope="col" className="px-3 py-2 font-medium">Joined</th>
                <th scope="col" className="px-3 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((u) => (
                <tr key={u.id} className="border-b last:border-0 align-top">
                  <th scope="row" className="px-3 py-2 text-left font-normal">
                    <div className="font-medium">
                      {u.full_name}
                      {u.id === me?.id && <span className="ml-1 text-xs text-muted-foreground">(you)</span>}
                    </div>
                    <div className="text-xs text-muted-foreground">{u.email}</div>
                  </th>
                  <td className="px-3 py-2">{ROLE_LABELS[u.role] ?? u.role}</td>
                  <td className="px-3 py-2">{u.student?.department_name ?? '-'}</td>
                  <td className="px-3 py-2">{u.student?.roll_number ?? '-'}</td>
                  <td className="px-3 py-2">{u.student?.graduation_year ?? '-'}</td>
                  <td className="px-3 py-2">{u.student ? (u.student.profile_complete ? 'Complete' : 'Incomplete') : '-'}</td>
                  <td className="px-3 py-2">{u.created_at.slice(0, 10)}</td>
                  <td className="px-3 py-2">
                    {u.id === me?.id || u.role === 'SUPER_ADMIN' ? (
                      <span className="text-xs text-muted-foreground">-</span>
                    ) : editingId === u.id ? (
                      <div className="flex flex-wrap items-center gap-2" role="group" aria-label={`Change role for ${u.full_name}`}>
                        <select
                          className={`${SELECT_CLASS} h-9 w-auto`}
                          aria-label={`New role for ${u.full_name}`}
                          value={newRole}
                          onChange={(e) => setNewRole(e.target.value as UserRole)}
                        >
                          {ASSIGNABLE_ROLES.map((r) => (
                            <option key={r} value={r}>
                              {ROLE_LABELS[r]}
                            </option>
                          ))}
                        </select>
                        <Button size="sm" disabled={newRole === u.role} onClick={() => setConfirming({ user: u, to: newRole })}>
                          Apply
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setEditingId(null)}>
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        aria-label={`Change role of ${u.full_name}`}
                        onClick={() => {
                          setEditingId(u.id);
                          setNewRole(u.role === 'STUDENT' ? 'FACULTY' : u.role);
                          setConfirming(null);
                        }}
                      >
                        Change role
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {total > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <p aria-live="polite">
            Showing {first}-{last} of {total}
          </p>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={page <= 1 || loading} onClick={() => setPage((p) => p - 1)}>
              Previous
            </Button>
            <Button size="sm" variant="outline" disabled={last >= total || loading} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
