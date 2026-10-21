import { describe, expect, it } from 'vitest';
import { EMPTY_ELIGIBILITY_FORM, buildEligibilityPayload, isValidHttpUrl, parseYears, type EligibilityFormState } from './validation';

function form(change: Partial<EligibilityFormState>): EligibilityFormState {
  return { ...EMPTY_ELIGIBILITY_FORM, ...change };
}

describe('buildEligibilityPayload', () => {
  it('omits criteria that are switched off instead of sending zeros', () => {
    const result = buildEligibilityPayload(form({ cgpaMin: '7', maxArrears: '0', attendanceMin: '0' }));
    expect(result.errors).toEqual({});
    expect(result.payload).toEqual({});
  });

  it('requires a basis whenever a minimum CGPA is set', () => {
    const result = buildEligibilityPayload(form({ cgpaOn: true, cgpaMin: '7.5' }));
    expect(result.payload).toBeNull();
    expect(result.errors.cgpaBasis).toBeDefined();
  });

  it('builds a full payload with only enabled criteria', () => {
    const result = buildEligibilityPayload(
      form({
        cgpaOn: true,
        cgpaMin: '7.5',
        cgpaBasis: 'LATEST_SEMESTER',
        arrearsOn: true,
        maxArrears: '0',
        departmentIds: [2, 3],
        yearsOn: true,
        years: '2027, 2026, 2026',
        notes: ['  Bring ID  '],
      }),
    );
    expect(result.payload).toEqual({
      cgpa_min: 7.5,
      cgpa_basis: 'LATEST_SEMESTER',
      max_arrears: 0,
      department_ids: [2, 3],
      graduation_years: [2026, 2027],
      custom_notes: ['Bring ID'],
    });
  });

  it('validates ranges, empty year list and blank notes', () => {
    const r = buildEligibilityPayload(
      form({ cgpaOn: true, cgpaMin: '11', cgpaBasis: 'AVERAGE_ALL_SEMESTERS', arrearsOn: true, maxArrears: '-1', attendanceOn: true, attendanceMin: '101', yearsOn: true, years: ' , ', notes: ['  '] }),
    );
    expect(r.payload).toBeNull();
    expect(Object.keys(r.errors).sort()).toEqual(['attendanceMin', 'cgpaMin', 'maxArrears', 'notes', 'years']);
  });

  it('rejects too many or too long notes', () => {
    expect(buildEligibilityPayload(form({ notes: Array.from({ length: 21 }, (_, i) => `n${i}`) })).errors.notes).toBeDefined();
    expect(buildEligibilityPayload(form({ notes: ['x'.repeat(501)] })).errors.notes).toBeDefined();
  });
});

describe('parseYears', () => {
  it('rejects out-of-range and non-numeric years', () => {
    expect(parseYears('1989')).toBeNull();
    expect(parseYears('2101')).toBeNull();
    expect(parseYears('20x6')).toBeNull();
    expect(parseYears('')).toBeNull();
    expect(parseYears('2026,2027')).toEqual([2026, 2027]);
  });
});

describe('isValidHttpUrl', () => {
  it('accepts only http and https', () => {
    expect(isValidHttpUrl('https://acme.com')).toBe(true);
    expect(isValidHttpUrl('ftp://acme.com')).toBe(false);
    expect(isValidHttpUrl('acme.com')).toBe(false);
  });
});
