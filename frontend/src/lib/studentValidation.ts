export type FieldErrors<K extends string> = Partial<Record<K, string>>;

export interface PersonalFormValues {
  roll_number: string;
  graduation_year: string;
  phone: string;
}

const MIN_GRAD_YEAR = 2000;
const MAX_GRAD_YEAR = 2100;

export function validatePersonal(values: PersonalFormValues): FieldErrors<keyof PersonalFormValues> {
  const errors: FieldErrors<keyof PersonalFormValues> = {};
  if (!values.roll_number.trim()) errors.roll_number = 'Roll number is required.';
  const year = values.graduation_year.trim();
  if (!year) {
    errors.graduation_year = 'Graduation year is required.';
  } else if (!/^\d{4}$/.test(year) || Number(year) < MIN_GRAD_YEAR || Number(year) > MAX_GRAD_YEAR) {
    errors.graduation_year = `Enter a 4-digit year between ${MIN_GRAD_YEAR} and ${MAX_GRAD_YEAR}.`;
  }
  const phone = values.phone.trim();
  if (!phone) {
    errors.phone = 'Phone number is required.';
  } else if (!/^\+?[0-9][0-9\s-]{6,18}$/.test(phone)) {
    errors.phone = 'Enter a valid phone number (7-15 digits).';
  }
  return errors;
}

export interface AcademicFormValues {
  semester: string;
  cgpa: string;
  active_arrears: string;
  attendance_pct: string;
}

export function validateAcademic(values: AcademicFormValues): FieldErrors<keyof AcademicFormValues> {
  const errors: FieldErrors<keyof AcademicFormValues> = {};
  const sem = values.semester.trim();
  if (!/^\d+$/.test(sem) || Number(sem) < 1 || Number(sem) > 12) {
    errors.semester = 'Semester must be a whole number from 1 to 12.';
  }
  const cgpa = values.cgpa.trim();
  if (!cgpa || Number.isNaN(Number(cgpa)) || Number(cgpa) < 0 || Number(cgpa) > 10) {
    errors.cgpa = 'CGPA must be a number from 0 to 10.';
  }
  if (!/^\d+$/.test(values.active_arrears.trim())) {
    errors.active_arrears = 'Active arrears must be a whole number, 0 or more.';
  }
  const att = values.attendance_pct.trim();
  if (att && (Number.isNaN(Number(att)) || Number(att) < 0 || Number(att) > 100)) {
    errors.attendance_pct = 'Attendance must be a number from 0 to 100.';
  }
  return errors;
}

export interface ProjectFormValues {
  title: string;
  url: string;
}

export function validateProject(values: ProjectFormValues): FieldErrors<keyof ProjectFormValues> {
  const errors: FieldErrors<keyof ProjectFormValues> = {};
  if (!values.title.trim()) errors.title = 'Title is required.';
  const url = values.url.trim();
  if (url && !/^https?:\/\/\S+$/i.test(url)) errors.url = 'URL must start with http:// or https://.';
  return errors;
}

export function validateCertification(name: string, issuedOn: string): FieldErrors<'name' | 'issued_on'> {
  const errors: FieldErrors<'name' | 'issued_on'> = {};
  if (!name.trim()) errors.name = 'Name is required.';
  if (issuedOn && !/^\d{4}-\d{2}-\d{2}$/.test(issuedOn)) errors.issued_on = 'Use the YYYY-MM-DD format.';
  return errors;
}
