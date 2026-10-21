import { useState, type FormEvent } from 'react';
import { FieldError } from '@/components/auth/FieldError';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { validateAcademic, type AcademicFormValues, type FieldErrors } from '@/lib/studentValidation';
import type { AcademicRecord, AcademicRecordInput } from '@/types';

interface AcademicRecordFormProps {
  initial?: AcademicRecord;
  onSubmit: (input: AcademicRecordInput) => Promise<void>;
  onCancel?: () => void;
}

function toValues(record?: AcademicRecord): AcademicFormValues {
  return {
    semester: record ? String(record.semester) : '',
    cgpa: record ? String(record.cgpa) : '',
    active_arrears: record ? String(record.active_arrears) : '0',
    attendance_pct: record?.attendance_pct != null ? String(record.attendance_pct) : '',
  };
}

export function AcademicRecordForm({ initial, onSubmit, onCancel }: AcademicRecordFormProps) {
  const [values, setValues] = useState<AcademicFormValues>(() => toValues(initial));
  const [errors, setErrors] = useState<FieldErrors<keyof AcademicFormValues>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const setField = (key: keyof AcademicFormValues, value: string): void => {
    setValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setServerError(null);
    const found = validateAcademic(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setSubmitting(true);
    try {
      await onSubmit({
        semester: Number(values.semester),
        cgpa: Number(values.cgpa),
        active_arrears: Number(values.active_arrears),
        attendance_pct: values.attendance_pct.trim() === '' ? null : Number(values.attendance_pct),
      });
      if (!initial) setValues(toValues());
    } catch (err) {
      setServerError(getErrorMessage(err, 'Could not save the academic record.'));
    } finally {
      setSubmitting(false);
    }
  };

  const field = (key: keyof AcademicFormValues, label: string, step?: string) => (
    <div className="space-y-2">
      <Label htmlFor={`ar-${key}`}>{label}</Label>
      <Input
        id={`ar-${key}`}
        type="number"
        inputMode="decimal"
        step={step}
        value={values[key]}
        onChange={(e) => setField(key, e.target.value)}
        disabled={submitting}
        aria-invalid={errors[key] ? true : undefined}
        aria-describedby={errors[key] ? `ar-${key}-error` : undefined}
      />
      <FieldError id={`ar-${key}-error`} message={errors[key]} />
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate aria-label="Academic record">
      <FormMessage message={serverError} />
      <div className="grid gap-4 sm:grid-cols-2">
        {field('semester', 'Semester (1-12)')}
        {field('cgpa', 'CGPA (0-10)', '0.01')}
        {field('active_arrears', 'Active arrears')}
        {field('attendance_pct', 'Attendance % (optional)', '0.1')}
      </div>
      <div className="flex gap-2">
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving...' : initial ? 'Update record' : 'Add record'}
        </Button>
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
