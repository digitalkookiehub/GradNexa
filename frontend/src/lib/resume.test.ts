import { describe, expect, it } from 'vitest';
import { MAX_RESUME_BYTES, buildSegments, validateResumeFile } from './resume';

function fileOf(name: string, type: string, size: number): File {
  const f = new File(['x'], name, { type });
  Object.defineProperty(f, 'size', { value: size });
  return f;
}

describe('validateResumeFile', () => {
  it('accepts pdf and docx', () => {
    expect(validateResumeFile(fileOf('cv.pdf', 'application/pdf', 100))).toBeNull();
    expect(
      validateResumeFile(fileOf('cv.DOCX', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 100)),
    ).toBeNull();
  });
  it('rejects other types, empty and oversized files', () => {
    expect(validateResumeFile(fileOf('cv.txt', 'text/plain', 10))).toMatch(/PDF or DOCX/);
    expect(validateResumeFile(fileOf('cv.pdf', 'image/png', 10))).toMatch(/PDF or DOCX/);
    expect(validateResumeFile(fileOf('cv.pdf', 'application/pdf', 0))).toMatch(/empty/);
    expect(validateResumeFile(fileOf('cv.pdf', 'application/pdf', MAX_RESUME_BYTES + 1))).toMatch(/larger/);
  });
});

describe('buildSegments', () => {
  const text = 'I know Python and SQL well';

  it('slices exact text for each range', () => {
    const segs = buildSegments(text, [
      { start: 7, end: 13, group: 'a' },
      { start: 18, end: 21, group: 'b' },
    ]);
    expect(segs.map((s) => s.text).join('')).toBe(text);
    expect(segs.filter((s) => s.groups.length).map((s) => [s.text, s.groups])).toEqual([
      ['Python', ['a']],
      ['SQL', ['b']],
    ]);
  });

  it('handles overlaps by tagging the shared part with both groups', () => {
    const segs = buildSegments(text, [
      { start: 7, end: 17, group: 'a' },
      { start: 14, end: 21, group: 'b' },
    ]);
    expect(segs.map((s) => s.text).join('')).toBe(text);
    const shared = segs.find((s) => s.groups.length === 2);
    expect(shared?.text).toBe('and');
  });

  it('drops out-of-range, negative, empty and non-integer ranges', () => {
    const segs = buildSegments(text, [
      { start: -1, end: 3, group: 'x' },
      { start: 5, end: 999, group: 'x' },
      { start: 5, end: 5, group: 'x' },
      { start: 1.5, end: 3, group: 'x' },
    ]);
    expect(segs).toHaveLength(1);
    expect(segs[0].groups).toEqual([]);
    expect(segs[0].text).toBe(text);
  });

  it('treats span offsets as code points so astral characters do not shift highlights', () => {
    const emojiText = 'I \u{1F600} know Python well';
    const start = Array.from(emojiText).indexOf('P');
    const segs = buildSegments(emojiText, [{ start, end: start + 6, group: 'skill:1' }]);
    const hit = segs.find((sg) => sg.groups.includes('skill:1'));
    expect(hit?.text).toBe('Python');
    expect(segs.map((sg) => sg.text).join('')).toBe(emojiText);
  });
});
