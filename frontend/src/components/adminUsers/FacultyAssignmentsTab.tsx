import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { adminUserService } from '@/services/adminUserService';
import type { AdminUser, FacultyAssignment } from '@/types/adminUsers';

export function FacultyAssignmentsTab() {
  const [assignments, setAssignments] = useState<FacultyAssignment[]>([]);
  const [faculty, setFaculty] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [facultyId, setFacultyId] = useState('');
  const [studentQuery, setStudentQuery] = useState('');
  const [studentResults, setStudentResults] = useState<AdminUser[]>([]);
  const [searched, setSearched] = useState(false);
  const [studentId, setStudentId] = useState('');
  const [formError, setFormError] = useState<string | undefined>();
  const [saving, setSaving] = useState(false);
  const [confirmId, setConfirmId] = useState<number | null>(null);

  const load = useCallback(async (): Promise<void> => {
    try {
      const [a, f] = await Promise.all([
        adminUserService.listFacultyAssignments(),
        adminUserService.list({ role: 'FACULTY', page_size: 100 }),
      ]);
      setAssignments(a);
      setFaculty(f.items);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load faculty assignments.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const searchStudents = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setFormError(undefined);
    try {
      const result = await adminUserService.list({ role: 'STUDENT', search: studentQuery, page_size: 10 });
      setStudentResults(result.items.filter((u) => u.student !== null));
      setSearched(true);
      setStudentId('');
    } catch (err) {
      setFormError(getErrorMessage(err, 'Could not search students.'));
    }
  };

  const add = async (): Promise<void> => {
    if (!facultyId) {
      setFormError('Choose a faculty member.');
      return;
    }
    if (!studentId) {
      setFormError('Search for a student and choose one.');
      return;
    }
    setSaving(true);
    setFormError(undefined);
    setNotice(null);
    try {
      await adminUserService.createFacultyAssignment(Number(facultyId), Number(studentId));
      setNotice('Assignment created.');
      setStudentId('');
      await load();
    } catch (err) {
      setFormError(getErrorMessage(err, 'Could not create the assignment.'));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number): Promise<void> => {
    setNotice(null);
    try {
      await adminUserService.removeFacultyAssignment(id);
      setConfirmId(null);
      setNotice('Assignment removed.');
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not remove the assignment.'));
      setConfirmId(null);
    }
  };

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        A faculty member only sees students assigned to them. Only users whose role is Faculty can be assigned: change a user's role on the Users tab first.
      </p>
      <FormMessage message={error} />
      <FormMessage message={notice} tone="success" />

      <section aria-labelledby="add-assignment" className="space-y-3 rounded-lg border bg-background p-4">
        <h2 id="add-assignment" className="font-semibold">
          Add assignment
        </h2>
        <div className="space-y-2">
          <Label htmlFor="assign-faculty">Faculty member</Label>
          <select id="assign-faculty" className={SELECT_CLASS} value={facultyId} onChange={(e) => setFacultyId(e.target.value)}>
            <option value="">{faculty.length === 0 ? 'No faculty users yet' : 'Select a faculty member'}</option>
            {faculty.map((f) => (
              <option key={f.id} value={f.id}>
                {f.full_name} ({f.email})
              </option>
            ))}
          </select>
        </div>
        <form onSubmit={(e) => void searchStudents(e)} className="flex flex-wrap items-end gap-2" aria-label="Find a student">
          <div className="min-w-0 flex-1 space-y-2">
            <Label htmlFor="assign-student-search">Find a student (name, email or roll number)</Label>
            <Input id="assign-student-search" value={studentQuery} onChange={(e) => setStudentQuery(e.target.value)} />
          </div>
          <Button type="submit" variant="outline">
            Find student
          </Button>
        </form>
        {searched && (
          <div className="space-y-2">
            <Label htmlFor="assign-student">Student</Label>
            <select id="assign-student" className={SELECT_CLASS} value={studentId} onChange={(e) => setStudentId(e.target.value)}>
              <option value="">{studentResults.length === 0 ? 'No students found' : 'Select a student'}</option>
              {studentResults.map((s) => (
                <option key={s.id} value={s.student?.student_id}>
                  {s.full_name} ({s.email}){s.student?.roll_number ? `, ${s.student.roll_number}` : ''}
                </option>
              ))}
            </select>
          </div>
        )}
        <FormMessage message={formError ?? null} />
        <Button onClick={() => void add()} disabled={saving}>
          {saving ? 'Saving...' : 'Add assignment'}
        </Button>
      </section>

      <section aria-labelledby="current-assignments" className="space-y-3">
        <h2 id="current-assignments" className="font-semibold">
          Current assignments
        </h2>
        {loading ? (
          <p role="status" className="text-muted-foreground">
            Loading assignments...
          </p>
        ) : assignments.length === 0 ? (
          <p className="rounded-md border bg-background p-4 text-sm text-muted-foreground">No faculty assignments yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border bg-background">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Faculty assignments</caption>
              <thead>
                <tr className="border-b bg-muted text-muted-foreground">
                  <th scope="col" className="px-3 py-2 font-medium">Faculty</th>
                  <th scope="col" className="px-3 py-2 font-medium">Student</th>
                  <th scope="col" className="px-3 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {assignments.map((a) => (
                  <tr key={a.id} className="border-b last:border-0 align-top">
                    <th scope="row" className="px-3 py-2 text-left font-normal">
                      <div className="font-medium">{a.faculty_name}</div>
                      <div className="text-xs text-muted-foreground">{a.faculty_email}</div>
                    </th>
                    <td className="px-3 py-2">
                      <div className="font-medium">{a.student_name}</div>
                      <div className="text-xs text-muted-foreground">{a.student_email}</div>
                    </td>
                    <td className="px-3 py-2">
                      {confirmId === a.id ? (
                        <div className="flex flex-wrap items-center gap-2" role="group" aria-label={`Confirm removing ${a.student_name} from ${a.faculty_name}`}>
                          <span>Remove this assignment?</span>
                          <Button size="sm" variant="destructive" onClick={() => void remove(a.id)}>
                            Confirm remove
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => setConfirmId(null)}>
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <Button size="sm" variant="outline" aria-label={`Remove ${a.student_name} from ${a.faculty_name}`} onClick={() => setConfirmId(a.id)}>
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
      </section>
    </div>
  );
}
