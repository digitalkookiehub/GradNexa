import type { Guide, GuideProcedure } from '@/types/guide';

export const OVERVIEW_ID = 'overview';
export const WRITTEN_ID = 'written';

export interface GuideSection {
  id: string;
  title: string;
}

/** URL-safe id for a heading, stable between the table of contents and the rendered heading. */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/** Top-level sections ("## ..." lines outside code fences) for the written guide's contents. */
export function extractSections(markdown: string): GuideSection[] {
  const sections: GuideSection[] = [];
  let inFence = false;
  for (const line of markdown.split('\n')) {
    if (line.trimStart().startsWith('```')) {
      inFence = !inFence;
      continue;
    }
    if (!inFence && line.startsWith('## ')) {
      const title = line.slice(3).trim();
      sections.push({ id: slugify(title), title });
    }
  }
  return sections;
}

// Pages an admin can actually open from the guide (the admin menu plus a few shared pages).
const SHARED_PAGES = new Set(['/placement', '/knowledge', '/profile', '/guide']);

/** True when the signed-in admin may open this page, so the guide can link to it. */
export function isOpenableByAdmin(path: string | null): path is string {
  return path !== null && (path.startsWith('/admin/') || SHARED_PAGES.has(path));
}

/** Every procedure in reading order (the order of the sidebar). */
export function allProcedures(guide: Guide): GuideProcedure[] {
  return guide.groups.flatMap((g) => g.procedures);
}

/** The pages the sidebar can show, in order: overview, every procedure, written guide. */
export function pageOrder(guide: Guide): string[] {
  return [OVERVIEW_ID, ...allProcedures(guide).map((p) => p.id), WRITTEN_ID];
}

/** Previous and next page ids in the sidebar order (null at the ends). */
export function neighbours(guide: Guide, id: string): { prev: string | null; next: string | null } {
  const order = pageOrder(guide);
  const i = order.indexOf(id);
  if (i < 0) return { prev: null, next: null };
  return { prev: i > 0 ? order[i - 1] : null, next: i < order.length - 1 ? order[i + 1] : null };
}

/** Resolve a page id to something the guide can show; unknown ids fall back to the overview. */
export function resolvePage(guide: Guide, id: string | null): string {
  return id !== null && pageOrder(guide).includes(id) ? id : OVERVIEW_ID;
}

/** Split text into plain and bold ("**label**") runs so UI names can be emphasised safely. */
export function inlineRuns(text: string): { text: string; bold: boolean }[] {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .filter((part) => part !== '')
    .map((part) => (part.startsWith('**') && part.endsWith('**') ? { text: part.slice(2, -2), bold: true } : { text: part, bold: false }));
}
