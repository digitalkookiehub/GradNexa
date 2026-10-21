import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { AcademicRecordsPanel } from './AcademicRecordsPanel';
import { FieldError } from '@/components/auth/FieldError';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { validatePersonal, type FieldErrors, type PersonalFormValues } from '@/lib/studentValidation';
import { studentService } from '@/services/studentService';
import type { AcademicRecord, Department, StudentProfile } from '@/types';

const STEP_TITLES = ['Personal details', 'Academics', 'Department'] as const;

export function OnboardingWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const [personal, setPersonal] = useState<PersonalFormValues>({ roll_number: '', graduation_year: '', phone: '' });
  const [personalErrors, setPersonalErrors] = useState<FieldErrors<keyof PersonalFormValues>>({});
  const [recordCount, setRecordCount] = useState(0);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [departmentId, setDepartmentId] = useState('');

  const [stepError, setStepError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([studentService.getProfile(), studentService.listDepartments()])
      .then(([p, depts]) => {
        if (cancelled) return;
        setProfile(p);
        setDepartments(depts);
        setPersonal({
          roll_number: p.roll_number ?? '',
          graduation_year: p.graduation_year !== null ? String(p.graduation_year) : '',
          phone: p.phone ?? '',
        });
        setDepartmentId(p.department_id !== null ? String(p.department_id) : '');
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(getErrorMessage(err, 'Could not load your profile.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const submitPersonal = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setStepError(null);
    const found = validatePersonal(personal);
    setPersonalErrors(found);
    if (Object.keys(found).length > 0) return;
    setSaving(true);
    try {
      setProfile(
        await studentService.updateProfile({
          roll_number: personal.roll_number.trim(),
          graduation_year: Number(personal.graduation_year),
          phone: personal.phone.trim(),
        }),
      );
      setStep(1);
    } catch (err) {
      setStepError(getErrorMessage(err, 'Could not save your details.'));
    } finally {
      setSaving(false);
    }
  };

  const goToDepartment = (): void => {
    if (recordCount === 0) {
      setStepError('Add at least one semester record to continue.');
      return;
    }
    setStepError(null);
    setStep(2);
  };

  const finish = async (): Promise<void> => {
    setStepError(null);
    if (!departmentId) {
      setStepError('Select your department.');
      return;
    }
    setSaving(true);
    try {
      const updated = await studentService.updateProfile({ department_id: Number(departmentId) });
      setProfile(updated);
      if (!updated.profile_complete) {
        setStepError('Your profile is still incomplete. Go back and check each step.');
        return;
      }
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setStepError(getErrorMessage(err, 'Could not save your department.'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <p role="status" className="py-12 text-center text-muted-foreground">
        Loading...
      </p>
    );
  }
  if (loadError) {
    return (
      <div className="mx-auto max-w-md space-y-4">
        <FormMessage message={loadError} />
        <Button
          variant="outline"
          onClick={() => {
            setLoadError(null);
            setLoading(true);
            setAttempt((a) => a + 1);
          }}
        >
          Retry
        </Button>
      </div>
    );
  }

  const selectedDepartment = departments.find((d) => String(d.id) === departmentId);

  return (
    <Card className="mx-auto max-w-2xl">
      <CardHeader>
        <CardTitle>Complete your profile</CardTitle>
        <CardDescription>
          Step {step + 1} of {STEP_TITLES.length}: {STEP_TITLES[step]}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormMessage message={stepError} />

        {step === 0 && (
          <form onSubmit={submitPersonal} className="space-y-4" noValidate aria-label="Personal details">
            <div className="space-y-2">
              <Label htmlFor="roll_number">Roll number</Label>
              <Input
                id="roll_number"
                value={personal.roll_number}
                onChange={(e) => setPersonal((p) => ({ ...p, roll_number: e.target.value }))}
                disabled={saving}
                aria-invalid={personalErrors.roll_number ? true : undefined}
                aria-describedby={personalErrors.roll_number ? 'roll_number-error' : undefined}
              />
              <FieldError id="roll_number-error" message={personalErrors.roll_number} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="graduation_year">Graduation year</Label>
              <Input
                id="graduation_year"
                inputMode="numeric"
                value={personal.graduation_year}
                onChange={(e) => setPersonal((p) => ({ ...p, graduation_year: e.target.value }))}
                disabled={saving}
                aria-invalid={personalErrors.graduation_year ? true : undefined}
                aria-describedby={personalErrors.graduation_year ? 'graduation_year-error' : undefined}
              />
              <FieldError id="graduation_year-error" message={personalErrors.graduation_year} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Phone</Label>
              <Input
                id="phone"
                type="tel"
                value={personal.phone}
                onChange={(e) => setPersonal((p) => ({ ...p, phone: e.target.value }))}
                disabled={saving}
                aria-invalid={personalErrors.phone ? true : undefined}
                aria-describedby={personalErrors.phone ? 'phone-error' : undefined}
              />
              <FieldError id="phone-error" message={personalErrors.phone} />
            </div>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Next'}
            </Button>
          </form>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <AcademicRecordsPanel onRecordsChange={(records: AcademicRecord[]) => setRecordCount(records.length)} />
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={() => setStep(0)}>
                Back
              </Button>
              <Button type="button" onClick={goToDepartment}>
                Next
              </Button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="department">Department</Label>
              <select
                id="department"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={departmentId}
                onChange={(e) => setDepartmentId(e.target.value)}
                disabled={saving}
              >
                <option value="">Select a department</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.code})
                  </option>
                ))}
              </select>
            </div>
            <dl className="grid grid-cols-2 gap-2 rounded-md border p-4 text-sm" aria-label="Summary">
              <dt className="text-muted-foreground">Roll number</dt>
              <dd>{profile?.roll_number ?? personal.roll_number}</dd>
              <dt className="text-muted-foreground">Graduation year</dt>
              <dd>{profile?.graduation_year ?? personal.graduation_year}</dd>
              <dt className="text-muted-foreground">Phone</dt>
              <dd>{profile?.phone ?? personal.phone}</dd>
              <dt className="text-muted-foreground">Semester records</dt>
              <dd>{recordCount}</dd>
              <dt className="text-muted-foreground">Department</dt>
              <dd>{selectedDepartment ? selectedDepartment.name : 'Not selected'}</dd>
            </dl>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={() => setStep(1)} disabled={saving}>
                Back
              </Button>
              <Button type="button" onClick={finish} disabled={saving}>
                {saving ? 'Saving...' : 'Confirm and finish'}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
