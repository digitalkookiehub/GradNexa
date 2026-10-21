import { describe, expect, it } from 'vitest';
import { normaliseAcademicRecord } from './studentService';

describe('normaliseAcademicRecord', () => {
  it('converts string decimals to numbers', () => {
    expect(normaliseAcademicRecord({ id: 1, semester: 2, cgpa: '8.50', active_arrears: 0, attendance_pct: '92.5' })).toEqual({
      id: 1,
      semester: 2,
      cgpa: 8.5,
      active_arrears: 0,
      attendance_pct: 92.5,
    });
  });

  it('keeps null attendance as null', () => {
    expect(normaliseAcademicRecord({ id: 1, semester: 2, cgpa: 7, active_arrears: 1, attendance_pct: null }).attendance_pct).toBeNull();
  });
});
