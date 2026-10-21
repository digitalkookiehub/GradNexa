import { describe, expect, it } from 'vitest';
import { formatDeadline, isoToLocalInput, localInputToIso } from './validation';

describe('application deadline (date-only, matches the backend DATE column)', () => {
  it('sends plain YYYY-MM-DD with no time component', () => {
    expect(localInputToIso('2026-10-30')).toBe('2026-10-30');
  });

  it('rejects empty, malformed and impossible dates', () => {
    expect(localInputToIso('')).toBeNull();
    expect(localInputToIso('2026-10-30T10:00')).toBeNull();
    expect(localInputToIso('30/10/2026')).toBeNull();
    expect(localInputToIso('2026-02-30')).toBeNull();
  });

  it('reads back a date or date-time string as the date part without timezone shifts', () => {
    expect(isoToLocalInput('2026-10-30')).toBe('2026-10-30');
    expect(isoToLocalInput('2026-10-30T23:30:00Z')).toBe('2026-10-30');
    expect(isoToLocalInput(null)).toBe('');
    expect(isoToLocalInput('not a date')).toBe('');
  });

  it('formats a missing or invalid deadline as "No deadline"', () => {
    expect(formatDeadline(null)).toBe('No deadline');
    expect(formatDeadline('garbage')).toBe('No deadline');
    expect(formatDeadline('2026-10-30')).not.toBe('No deadline');
  });
});
